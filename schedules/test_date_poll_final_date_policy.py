from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Group
from schedules.models import DatePoll, DatePollOption, TRPGSession


class FinalDatePolicyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="final-date-owner")
        self.group = Group.objects.create(name="確定日の検証", created_by=self.owner)
        self.session = TRPGSession.objects.create(title="確定日の検証", gm=self.owner, group=self.group, date=None)
        self.polls = []
        self.options = []
        for days in (1, 2):
            poll = DatePoll.objects.create(
                title="日程投票", group=self.group, created_by=self.owner, session=self.session
            )
            self.polls.append(poll)
            self.options.append(
                DatePollOption.objects.create(poll=poll, datetime=timezone.now() + timedelta(days=days))
            )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def confirm(self, index):
        return self.client.post(
            f"/api/schedules/date-polls/{self.polls[index].pk}/confirm/",
            {"option_id": self.options[index].pk},
            format="json",
        )

    def test_second_poll_cannot_overwrite_confirmed_session(self):
        self.assertEqual(self.confirm(0).status_code, 200)
        response = self.confirm(1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("セッション編集", str(response.data))
        self.session.refresh_from_db()
        self.polls[1].refresh_from_db()
        self.assertEqual(self.session.date, self.options[0].datetime)
        self.assertFalse(self.polls[1].is_closed)
        self.assertIsNone(self.polls[1].selected_date)

    def test_confirmed_poll_cannot_reopen_or_rewrite_history(self):
        self.assertEqual(self.confirm(0).status_code, 200)
        url = f"/api/schedules/date-polls/{self.polls[0].pk}/"
        for payload in ({"is_closed": False}, {"selected_date": None}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch(url, payload, format="json").status_code, 400)
        self.polls[0].refresh_from_db()
        self.assertTrue(self.polls[0].is_closed)
        self.assertEqual(self.polls[0].selected_date, self.options[0].datetime)

    def test_session_edit_changes_current_date_but_preserves_poll_history(self):
        self.assertEqual(self.confirm(0).status_code, 200)
        updated_date = timezone.now() + timedelta(days=7)
        response = self.client.patch(
            f"/api/schedules/sessions/{self.session.pk}/", {"date": updated_date.isoformat()}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.polls[0].refresh_from_db()
        self.assertEqual(self.session.date, updated_date)
        self.assertEqual(self.polls[0].selected_date, self.options[0].datetime)

    def test_clearing_session_date_does_not_allow_another_poll_to_confirm(self):
        self.assertEqual(self.confirm(0).status_code, 200)
        TRPGSession.objects.filter(pk=self.session.pk).update(date=None)
        self.assertEqual(self.confirm(1).status_code, 400)

    def test_date_already_set_by_session_editor_cannot_be_overwritten(self):
        TRPGSession.objects.filter(pk=self.session.pk).update(date=self.options[1].datetime)
        self.assertEqual(self.confirm(0).status_code, 400)
        self.session.refresh_from_db()
        self.assertEqual(self.session.date, self.options[1].datetime)


@skipUnlessDBFeature("has_select_for_update")
class FinalDateConcurrencyTests(TransactionTestCase):
    def test_different_polls_cannot_both_confirm_the_same_session(self):
        owner = get_user_model().objects.create_user(username="parallel-final-date")
        group = Group.objects.create(name="並行日程確定", created_by=owner)
        session = TRPGSession.objects.create(title="並行日程確定", gm=owner, group=group, date=None)
        options = []
        for days in (1, 2):
            poll = DatePoll.objects.create(title="並行投票", group=group, created_by=owner, session=session)
            options.append(DatePollOption.objects.create(poll=poll, datetime=timezone.now() + timedelta(days=days)))
        barrier = Barrier(2)

        def confirm(option):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                client = APIClient()
                client.force_authenticate(owner)
                barrier.wait(timeout=10)
                return client.post(
                    f"/api/schedules/date-polls/{option.poll_id}/confirm/", {"option_id": option.pk}, format="json"
                ).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(confirm, option) for option in options]
            self.assertCountEqual([future.result(timeout=20) for future in futures], [200, 400])
        winner = DatePoll.objects.get(session=session, is_closed=True)
        session.refresh_from_db()
        self.assertEqual(session.date, winner.selected_date)
        self.assertEqual(DatePoll.objects.filter(session=session, selected_date__isnull=True).count(), 1)
