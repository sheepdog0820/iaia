from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from schedules.models import SessionParticipant, TRPGSession


class SessionStatisticsContractTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="stats-owner")
        self.other = get_user_model().objects.create_user(username="stats-other")
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def session(self, gm, minutes, days=1):
        return TRPGSession.objects.create(
            title="統計確認",
            gm=gm,
            created_by=gm,
            date=timezone.now() - timedelta(days=days),
            duration_minutes=minutes,
            status="completed",
        )

    def test_average_uses_unrounded_minutes_and_counts_each_session_once(self):
        gm_session = self.session(self.owner, 30)
        SessionParticipant.objects.create(session=gm_session, user=self.owner)
        SessionParticipant.objects.create(session=gm_session, user=self.other)
        player_session = self.session(self.other, 35)
        SessionParticipant.objects.create(session=player_session, user=self.owner)
        self.session(self.other, 600)
        self.session(self.owner, 600, days=400)
        self.session(self.owner, 600, days=-10)

        response = self.client.get("/api/schedules/sessions/statistics/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_count"], 2)
        self.assertEqual(response.data["total_minutes"], 65)
        self.assertEqual(response.data["total_hours"], 1.1)
        self.assertEqual(response.data["average_session_hours"], 0.5)

    def test_empty_statistics_returns_zero_average(self):
        response = self.client.get("/api/schedules/sessions/statistics/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_count"], 0)
        self.assertEqual(response.data["average_session_hours"], 0)

    def test_average_uses_actual_duration_even_when_zero(self):
        session = self.session(self.owner, 120)
        for minutes, expected in [(0, 0), (45, 0.8)]:
            with self.subTest(actual_minutes=minutes):
                session.actual_duration_minutes = minutes
                session.save(update_fields=["actual_duration_minutes"])
                response = self.client.get("/api/schedules/sessions/statistics/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["total_minutes"], minutes)
                self.assertEqual(response.data["average_session_hours"], expected)
