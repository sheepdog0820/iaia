from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from unittest.mock import patch

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

    def test_requested_year_uses_japanese_calendar_boundaries(self):
        dates = [
            (datetime(2024, 12, 31, 14, 59, 59, tzinfo=datetime_timezone.utc), 600),
            (datetime(2024, 12, 31, 15, tzinfo=datetime_timezone.utc), 60),
            (datetime(2025, 12, 31, 14, 59, 59, tzinfo=datetime_timezone.utc), 120),
            (datetime(2025, 12, 31, 15, tzinfo=datetime_timezone.utc), 600),
        ]
        for date, minutes in dates:
            session = self.session(self.owner, minutes)
            session.date = date
            session.save(update_fields=["date"])
        now = datetime(2026, 6, 1, tzinfo=datetime_timezone.utc)
        with timezone.override("Asia/Tokyo"), patch("schedules.views.timezone.now", return_value=now):
            response = self.client.get("/api/schedules/sessions/statistics/?year=2025")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_count"], 2)
        self.assertEqual(response.data["total_minutes"], 180)
        self.assertEqual(response.data["average_session_hours"], 1.5)

    def test_requested_year_does_not_include_future_sessions(self):
        now = datetime(2026, 6, 1, tzinfo=datetime_timezone.utc)
        for date in [now - timedelta(days=1), now + timedelta(days=1)]:
            session = self.session(self.owner, 60)
            session.date = date
            session.save(update_fields=["date"])
        with patch("schedules.views.timezone.now", return_value=now):
            response = self.client.get("/api/schedules/sessions/statistics/?year=2026")
        self.assertEqual(response.data["session_count"], 1)
        self.assertEqual(response.data["total_minutes"], 60)

    def test_invalid_year_returns_japanese_validation_error(self):
        for year in ["", "invalid", "2025.5", "0", "-1", "10000"]:
            with self.subTest(year=year):
                response = self.client.get("/api/schedules/sessions/statistics/", {"year": year})
                self.assertEqual(response.status_code, 400)
                self.assertIn("年は1から9999までの整数で指定してください", str(response.data))

    def test_supported_year_limits_return_empty_statistics(self):
        for year in [1, 9999]:
            with self.subTest(year=year), timezone.override("Asia/Tokyo"):
                response = self.client.get("/api/schedules/sessions/statistics/", {"year": year})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["session_count"], 0)
