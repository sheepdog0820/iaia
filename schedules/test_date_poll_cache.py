from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import DatePoll


class DatePollCacheTests(APITestCase):
    def test_poll_reads_and_updates_are_not_cached(self):
        user = get_user_model().objects.create_user(username="poll-cache")
        group = Group.objects.create(name="投票検証", created_by=user)
        group.members.add(user)
        poll = DatePoll.objects.create(title="候補", group=group, created_by=user)
        self.client.force_authenticate(user)
        responses = [
            self.client.get("/api/schedules/date-polls/"),
            self.client.get(f"/api/schedules/date-polls/{poll.pk}/"),
            self.client.patch(f"/api/schedules/date-polls/{poll.pk}/", {"title": "更新"}, format="json"),
        ]
        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response.get("Cache-Control", ""))
                self.assertIn("no-cache", response["Cache-Control"])
                self.assertIn("private", response["Cache-Control"])

    def test_unauthenticated_poll_response_is_not_cached(self):
        response = self.client.get("/api/schedules/date-polls/")
        self.assertIn(response.status_code, (401, 403))
        self.assertIn("no-store", response.get("Cache-Control", ""))
