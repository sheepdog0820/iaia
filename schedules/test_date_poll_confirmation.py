from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import DatePoll, DatePollOption, TRPGSession


def create_poll():
    user = get_user_model().objects.create_user(username="confirmation-owner")
    group = Group.objects.create(name="日程確定検証", created_by=user)
    poll = DatePoll.objects.create(title="候補の確定", group=group, created_by=user)
    options = [DatePollOption.objects.create(poll=poll, datetime=timezone.now() + timedelta(days=i)) for i in (1, 2)]
    return user, poll, options


class DatePollConfirmationTests(APITestCase):
    def setUp(self):
        self.user, self.poll, self.options = create_poll()
        self.client.force_authenticate(self.user)

    def test_stale_request_cannot_create_a_second_session(self):
        stale = DatePoll.objects.get(pk=self.poll.pk)
        url = f"/api/schedules/date-polls/{self.poll.pk}/confirm/"
        first = self.client.post(url, {"option_id": self.options[0].pk}, format="json")
        self.assertEqual(first.status_code, 200)
        with patch("schedules.views.DatePollViewSet.get_object", return_value=stale):
            second = self.client.post(url, {"option_id": self.options[1].pk}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertIn("投票は締め切られています", str(second.data))
        self.poll.refresh_from_db()
        self.assertEqual(TRPGSession.objects.count(), 1)
        self.assertEqual(self.poll.selected_date, self.options[0].datetime)
        self.assertEqual(self.poll.session.date, self.options[0].datetime)

    def test_session_failure_leaves_poll_open_for_retry(self):
        with patch("schedules.models.TRPGSession.objects.create", side_effect=RuntimeError("isolated failure")):
            with self.assertRaises(RuntimeError):
                self.poll.confirm_date(self.options[0])
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_closed)
        self.assertIsNone(self.poll.selected_date)
        self.assertIsNone(self.poll.session_id)
        session = self.poll.confirm_date(self.options[0])
        self.assertEqual(session.pk, self.poll.session_id)
        self.assertEqual(TRPGSession.objects.count(), 1)


class DatePollConfirmationConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_confirmations_create_only_one_session(self):
        _, poll, options = create_poll()
        barrier = Barrier(2)

        def confirm(option_id):
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                stale = DatePoll.objects.get(pk=poll.pk)
                option = DatePollOption.objects.get(pk=option_id)
                barrier.wait(timeout=10)
                try:
                    stale.confirm_date(option)
                    return "confirmed", option.datetime
                except ValidationError:
                    return "closed", None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(confirm, option.pk) for option in options]
            results = [future.result(timeout=20) for future in futures]
        self.assertCountEqual([result[0] for result in results], ["confirmed", "closed"])
        selected = next(result[1] for result in results if result[0] == "confirmed")
        poll.refresh_from_db()
        self.assertEqual(TRPGSession.objects.count(), 1)
        self.assertEqual(poll.selected_date, selected)
        self.assertEqual(poll.session.date, selected)
