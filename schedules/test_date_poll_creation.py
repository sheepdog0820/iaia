from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import Group, GroupMembership
from schedules.models import DatePoll, DatePollOption, TRPGSession
from schedules.serializers import DatePollCreateSerializer


def creation_fixture():
    owner = get_user_model().objects.create_user(username="creation-owner")
    editor = get_user_model().objects.create_user(username="creation-admin")
    group = Group.objects.create(name="同時作成検証", created_by=owner)
    membership = GroupMembership.objects.create(group=group, user=editor, role="admin")
    session = TRPGSession.objects.create(title="日程未定", gm=owner, group=group, date=None)
    payload = {
        "title": "日程調整",
        "group": group.pk,
        "session": session.pk,
        "options": [{"datetime": (timezone.now() + timedelta(days=i)).isoformat()} for i in (1, 2)],
    }
    return editor, membership, session, payload


class DatePollCreationTests(TestCase):
    def setUp(self):
        self.user, self.membership, self.session, self.payload = creation_fixture()

    def validated_serializer(self):
        serializer = DatePollCreateSerializer(data=self.payload, context={"request": SimpleNamespace(user=self.user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer

    def test_stale_validation_cannot_create_duplicate_open_poll(self):
        first = self.validated_serializer()
        stale = self.validated_serializer()
        first.save()
        with self.assertRaises(ValidationError):
            stale.save()
        self.assertEqual(DatePoll.objects.count(), 1)
        self.assertEqual(DatePollOption.objects.count(), 2)

    def test_session_dated_after_validation_is_rejected(self):
        stale = self.validated_serializer()
        self.session.date = timezone.now() + timedelta(days=5)
        self.session.save(update_fields=["date"])
        with self.assertRaises(ValidationError):
            stale.save()
        self.assertFalse(DatePoll.objects.exists())

    def test_management_rights_are_rechecked_before_creation(self):
        stale = self.validated_serializer()
        self.membership.role = "member"
        self.membership.save(update_fields=["role"])
        with self.assertRaises(ValidationError):
            stale.save()
        self.assertFalse(DatePoll.objects.exists())

    def test_session_deleted_after_validation_is_rejected(self):
        stale = self.validated_serializer()
        self.session.delete()
        with self.assertRaisesMessage(ValidationError, "対象のセッションが見つかりません"):
            stale.save()
        self.assertFalse(DatePoll.objects.exists())

    def test_option_failure_rolls_back_poll_and_previous_options(self):
        serializer = self.validated_serializer()
        original_create = DatePollOption.objects.create
        calls = 0

        def fail_second_option(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("isolated option failure")
            return original_create(**kwargs)

        with patch("schedules.serializers.DatePollOption.objects.create", side_effect=fail_second_option):
            with self.assertRaises(RuntimeError):
                serializer.save()
        self.assertFalse(DatePoll.objects.exists())
        self.assertFalse(DatePollOption.objects.exists())


class DatePollCreationConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_api_creation_allows_one_open_poll(self):
        user, _, session, payload = creation_fixture()
        barrier = Barrier(2)
        original_create = DatePollCreateSerializer.create

        def create_after_both_validated(serializer, data):
            barrier.wait(timeout=10)
            return original_create(serializer, data)

        def create():
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                client = APIClient()
                client.force_authenticate(user)
                return client.post("/api/schedules/date-polls/", payload, format="json").status_code
            finally:
                connections.close_all()

        with patch.object(DatePollCreateSerializer, "create", create_after_both_validated):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(create) for _ in range(2)]
                statuses = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(statuses, [201, 400])
        self.assertEqual(DatePoll.objects.filter(session=session, is_closed=False).count(), 1)
        self.assertEqual(DatePollOption.objects.count(), 2)
