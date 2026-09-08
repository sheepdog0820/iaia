from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import Group
from schedules.models import DatePoll, DatePollOption, DatePollVote, TRPGSession
from schedules.views import DatePollViewSet


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

    def test_stale_vote_after_confirmation_is_rejected(self):
        stale = DatePoll.objects.get(pk=self.poll.pk)
        self.poll.confirm_date(self.options[0])
        with patch("schedules.views.DatePollViewSet.get_object", return_value=stale):
            response = self.client.post(
                f"/api/schedules/date-polls/{self.poll.pk}/vote/",
                {"votes": [{"option_id": self.options[0].pk, "status": "available"}]},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(DatePollVote.objects.exists())

    def test_stale_option_addition_after_confirmation_is_rejected(self):
        stale = DatePoll.objects.get(pk=self.poll.pk)
        self.poll.confirm_date(self.options[0])
        with patch("schedules.views.DatePollViewSet.get_object", return_value=stale):
            response = self.client.post(
                f"/api/schedules/date-polls/{self.poll.pk}/add_option/",
                {"datetime": (timezone.now() + timedelta(days=3)).isoformat()},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.poll.options.count(), 2)

    def test_stale_title_edit_preserves_confirmation(self):
        stale = DatePoll.objects.get(pk=self.poll.pk)
        session = self.poll.confirm_date(self.options[0])
        with patch("schedules.views.DatePollViewSet.get_object", return_value=stale):
            response = self.client.patch(
                f"/api/schedules/date-polls/{self.poll.pk}/", {"title": "確定後のタイトル"}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.title, "確定後のタイトル")
        self.assertTrue(self.poll.is_closed)
        self.assertEqual(self.poll.session_id, session.pk)
        self.assertEqual(self.poll.selected_date, self.options[0].datetime)

    def test_departed_member_cannot_write_using_previous_visibility(self):
        member = get_user_model().objects.create_user(username="departed-voter")
        self.poll.group.members.add(member)
        self.client.force_authenticate(member)
        url = f"/api/schedules/date-polls/{self.poll.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        stale = DatePoll.objects.get(pk=self.poll.pk)
        self.poll.group.members.remove(member)
        with patch("schedules.views.DatePollViewSet.get_object", return_value=stale):
            response = self.client.post(
                url + "vote/", {"votes": [{"option_id": self.options[0].pk, "status": "available"}]}, format="json"
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(DatePollVote.objects.exists())

    def test_member_cannot_edit_poll_title(self):
        member = get_user_model().objects.create_user(username="non-owner-editor")
        self.poll.group.members.add(member)
        self.client.force_authenticate(member)
        response = self.client.patch(
            f"/api/schedules/date-polls/{self.poll.pk}/", {"title": "他の参加者の変更"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "作成者のみが投票を編集できます")
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.title, "候補の確定")


class DatePollConfirmationConcurrencyTests(TransactionTestCase):
    def run_write_behind_confirmation(self, action):
        user, poll, options = create_poll()
        read = Event()
        original_get_object = DatePollViewSet.get_object

        def observe_read(view):
            result = original_get_object(view)
            read.set()
            return result

        def write():
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET lock_timeout = '5s'")
                client = APIClient()
                client.force_authenticate(user)
                url = f"/api/schedules/date-polls/{poll.pk}/"
                if action == "edit":
                    return client.patch(url, {"title": "並行編集"}, format="json").status_code
                data = (
                    {"votes": [{"option_id": options[0].pk, "status": "available"}]}
                    if action == "vote"
                    else {"datetime": (timezone.now() + timedelta(days=3)).isoformat()}
                )
                return client.post(url + action + "/", data, format="json").status_code
            finally:
                connections.close_all()

        with patch.object(DatePollViewSet, "get_object", observe_read), ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                DatePoll.objects.select_for_update().get(pk=poll.pk)
                future = pool.submit(write)
                self.assertTrue(read.wait(timeout=10), "並行要求が投票を読み取れませんでした")
                session = poll.confirm_date(options[0])
            result = future.result(timeout=20)
        poll.refresh_from_db()
        self.assertTrue(poll.is_closed)
        self.assertEqual(poll.session_id, session.pk)
        self.assertEqual(poll.selected_date, options[0].datetime)
        self.assertEqual(poll.session.date, options[0].datetime)
        self.assertEqual(TRPGSession.objects.count(), 1)
        if action == "edit":
            self.assertEqual(result, 200)
            self.assertEqual(poll.title, "並行編集")
        else:
            self.assertEqual(result, 400)
            self.assertFalse(DatePollVote.objects.exists())
            self.assertEqual(poll.options.count(), 2)

    @skipUnlessDBFeature("has_select_for_update")
    def test_vote_waits_for_confirmation(self):
        self.run_write_behind_confirmation("vote")

    @skipUnlessDBFeature("has_select_for_update")
    def test_option_addition_waits_for_confirmation(self):
        self.run_write_behind_confirmation("add_option")

    @skipUnlessDBFeature("has_select_for_update")
    def test_title_edit_waits_for_confirmation(self):
        self.run_write_behind_confirmation("edit")

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
