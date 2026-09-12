from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import DatePoll, DatePollOption, DatePollVote, TRPGSession
from schedules.serializers import DatePollOptionSerializer


class DatePollResponseQueryTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="poll-query-owner")
        self.group = Group.objects.create(name="日程応答検証", created_by=self.user)
        self.client.force_authenticate(self.user)

    def test_confirmation_queries_do_not_grow_with_options_and_voters(self):
        totals = []
        for count in (3, 15):
            session = TRPGSession.objects.create(title="日程未定", gm=self.user, group=self.group, date=None)
            poll = DatePoll.objects.create(title="日程調整", group=self.group, session=session, created_by=self.user)
            options = [
                DatePollOption.objects.create(poll=poll, datetime=timezone.now() + timedelta(days=i + 1))
                for i in range(count)
            ]
            for option in options:
                DatePollVote.objects.create(option=option, user=self.user, status="available")
            with CaptureQueriesContext(connection) as queries:
                response = self.client.post(
                    f"/api/schedules/date-polls/{poll.pk}/confirm/", {"option_id": options[0].pk}, format="json"
                )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["is_closed"])
            self.assertEqual(response.data["session_detail"]["date"], options[0].datetime.isoformat())
            self.assertEqual(len(response.data["options"]), count)
            for option in response.data["options"]:
                self.assertEqual(
                    (option["available_count"], option["maybe_count"], option["unavailable_count"]), (1, 0, 0)
                )
                self.assertEqual(len(option["votes"]), 1)
            totals.append(len(queries))
            vote_reads = [query for query in queries if 'FROM "schedules_datepollvote"' in query["sql"]]
            self.assertEqual(len(vote_reads), 1)
        self.assertEqual(totals[0], totals[1], totals)

    def test_counts_match_with_and_without_prefetched_votes(self):
        poll = DatePoll.objects.create(title="集計", group=self.group, created_by=self.user)
        option = DatePollOption.objects.create(poll=poll, datetime=timezone.now() + timedelta(days=1))
        for index, status in enumerate(("available", "available", "maybe", "unavailable")):
            user = get_user_model().objects.create_user(username=f"poll-voter-{index}")
            DatePollVote.objects.create(option=option, user=user, status=status)
        direct = DatePollOptionSerializer(option).data
        prefetched = DatePollOption.objects.prefetch_related("votes__user").get(pk=option.pk)
        with self.assertNumQueries(0):
            cached = DatePollOptionSerializer(prefetched).data
        self.assertEqual(direct, cached)
        self.assertEqual((cached["available_count"], cached["maybe_count"], cached["unavailable_count"]), (2, 1, 1))
