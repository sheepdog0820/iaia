from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import DatePoll, DatePollOption, DatePollVote


class DatePollVoteValidationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="vote-validation")
        group = Group.objects.create(name="投票入力検証", created_by=self.user)
        self.poll = DatePoll.objects.create(title="投票", group=group, created_by=self.user)
        self.option = DatePollOption.objects.create(poll=self.poll, datetime=timezone.now())
        self.url = f"/api/schedules/date-polls/{self.poll.pk}/vote/"
        self.client.force_authenticate(self.user)
        self.client.raise_request_exception = False

    def test_malformed_bodies_return_400_without_writes(self):
        for payload in ([1], {"votes": "bad"}, {"votes": [None]}, {"votes": [1]}, {"votes": [{"option_id": "bad"}]}):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(DatePollVote.objects.exists())

    def test_invalid_fields_return_400_without_writes(self):
        for fields in ({"status": "invalid"}, {"status": None}, {"comment": "あ" * 101}, {"comment": None}):
            with self.subTest(fields=fields):
                DatePollVote.objects.all().delete()
                response = self.client.post(
                    self.url, {"votes": [{"option_id": self.option.pk, **fields}]}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(DatePollVote.objects.exists())

    def test_foreign_option_rejects_entire_batch_and_preserves_previous_vote(self):
        other = DatePoll.objects.create(title="別の投票", group=self.poll.group, created_by=self.user)
        foreign_option = DatePollOption.objects.create(poll=other, datetime=timezone.now())
        vote = DatePollVote.objects.create(option=self.option, user=self.user, status="maybe", comment="元の回答")
        response = self.client.post(
            self.url,
            {
                "votes": [
                    {"option_id": self.option.pk, "status": "available"},
                    {"option_id": foreign_option.pk, "status": "unavailable"},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        vote.refresh_from_db()
        self.assertEqual((vote.status, vote.comment), ("maybe", "元の回答"))
        self.assertEqual(DatePollVote.objects.count(), 1)

    def test_valid_choices_defaults_and_comment_boundary(self):
        for value in ("available", "maybe", "unavailable"):
            with self.subTest(status=value):
                response = self.client.post(
                    self.url,
                    {"votes": [{"option_id": self.option.pk, "status": value, "comment": "あ" * 100}]},
                    format="json",
                )
                self.assertEqual(response.status_code, 200)
                vote = DatePollVote.objects.get(option=self.option, user=self.user)
                self.assertEqual((vote.status, vote.comment), (value, "あ" * 100))
        response = self.client.post(self.url, {"votes": [{"option_id": self.option.pk}]}, format="json")
        self.assertEqual(response.status_code, 200)
        vote.refresh_from_db()
        self.assertEqual((vote.status, vote.comment), ("available", ""))
