from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group as CustomGroup
from .models import TRPGSession, SessionSeries, SessionAvailability, DatePoll, DatePollOption


User = get_user_model()


class AdvancedSchedulingModelsTestCase(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User',
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.gm,
        )
        self.group.members.add(self.gm)

    @patch('schedules.models.timezone.localdate')
    def test_get_next_session_dates_weekly_includes_future_start_date(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 1)
        series = SessionSeries.objects.create(
            title='Weekly Series',
            group=self.group,
            gm=self.gm,
            recurrence='weekly',
            weekday=0,  # Monday
            start_date=date(2026, 1, 5),
        )

        dates = series.get_next_session_dates(count=3)
        self.assertEqual(dates, [date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19)])

    @patch('schedules.models.timezone.localdate')
    def test_get_next_session_dates_biweekly_respects_start_date_parity(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 10)
        series = SessionSeries.objects.create(
            title='Biweekly Series',
            group=self.group,
            gm=self.gm,
            recurrence='biweekly',
            weekday=0,  # Monday
            start_date=date(2026, 1, 5),
        )

        dates = series.get_next_session_dates(count=2)
        self.assertEqual(dates, [date(2026, 1, 19), date(2026, 2, 2)])

    @patch('schedules.models.timezone.localdate')
    def test_get_next_session_dates_monthly_supports_end_of_month(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 15)
        series = SessionSeries.objects.create(
            title='Monthly Series',
            group=self.group,
            gm=self.gm,
            recurrence='monthly',
            day_of_month=31,
            start_date=date(2026, 1, 30),
        )

        dates = series.get_next_session_dates(count=3)
        self.assertEqual(dates, [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

    @patch('schedules.models.timezone.localdate')
    def test_get_next_session_dates_custom_interval_does_not_drift(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 15)
        series = SessionSeries.objects.create(
            title='Custom Series',
            group=self.group,
            gm=self.gm,
            recurrence='custom',
            custom_interval_days=10,
            start_date=date(2026, 1, 1),
        )

        dates = series.get_next_session_dates(count=3)
        self.assertEqual(dates, [date(2026, 1, 21), date(2026, 1, 31), date(2026, 2, 10)])


class AdvancedSchedulingAPITestCase(APITestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User',
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='pass123',
            nickname='Member',
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass123',
            nickname='Outsider',
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.gm,
        )
        self.group.members.add(self.gm, self.member)

        self.session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            group=self.group,
            visibility='group',
            status='planned',
        )

    @patch('schedules.models.timezone.localdate')
    def test_session_series_generate_sessions_creates_and_deduplicates(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 1)
        series = SessionSeries.objects.create(
            title='Weekly Series',
            group=self.group,
            gm=self.gm,
            recurrence='weekly',
            weekday=0,
            start_date=date(2026, 1, 5),
            duration_minutes=180,
        )

        self.client.force_authenticate(user=self.gm)
        response = self.client.post(f'/api/schedules/session-series/{series.id}/generate_sessions/', {'count': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created_count'], 2)
        self.assertEqual(TRPGSession.objects.filter(series=series).count(), 2)

        response2 = self.client.post(f'/api/schedules/session-series/{series.id}/generate_sessions/', {'count': 2})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['created_count'], 0)

    @patch('schedules.models.timezone.localdate')
    def test_session_series_generate_sessions_forbidden_for_non_gm(self, mocked_localdate):
        mocked_localdate.return_value = date(2026, 1, 1)
        series = SessionSeries.objects.create(
            title='Weekly Series',
            group=self.group,
            gm=self.gm,
            recurrence='weekly',
            weekday=0,
            start_date=date(2026, 1, 5),
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.post(f'/api/schedules/session-series/{series.id}/generate_sessions/', {'count': 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_availability_vote_requires_session_visibility(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post(
            '/api/schedules/availability/vote/',
            {'session_id': self.session.id, 'status': 'available'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_availability_vote_creates_and_updates(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            '/api/schedules/availability/vote/',
            {'session_id': self.session.id, 'status': 'available', 'comment': ''},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SessionAvailability.objects.filter(session=self.session, user=self.member).count(), 1)

        response2 = self.client.post(
            '/api/schedules/availability/vote/',
            {'session_id': self.session.id, 'status': 'maybe', 'comment': 'late'},
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            SessionAvailability.objects.get(session=self.session, user=self.member).status,
            'maybe',
        )

    def test_session_availability_for_session_requires_visibility(self):
        self.client.force_authenticate(user=self.member)
        SessionAvailability.objects.create(
            session=self.session,
            user=self.member,
            status='available',
        )
        SessionAvailability.objects.create(
            session=self.session,
            user=self.gm,
            status='unavailable',
        )

        response = self.client.get(f'/api/schedules/availability/for_session/?session_id={self.session.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        self.client.force_authenticate(user=self.outsider)
        response2 = self.client.get(f'/api/schedules/availability/for_session/?session_id={self.session.id}')
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_date_poll_create_vote_and_confirm(self):
        self.client.force_authenticate(user=self.gm)

        option_dt1 = (timezone.now() + timedelta(days=3)).isoformat()
        option_dt2 = (timezone.now() + timedelta(days=4)).isoformat()

        response = self.client.post(
            '/api/schedules/date-polls/',
            {
                'title': 'Date Poll',
                'description': 'Pick a date',
                'group': self.group.id,
                'create_session_on_confirm': True,
                'options': [
                    {'datetime': option_dt1, 'note': 'A'},
                    {'datetime': option_dt2, 'note': 'B'},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        poll = DatePoll.objects.get(title='Date Poll')
        self.assertEqual(poll.created_by, self.gm)
        self.assertEqual(poll.options.count(), 2)

        option = DatePollOption.objects.filter(poll=poll).order_by('datetime').first()
        self.client.force_authenticate(user=self.member)
        vote_response = self.client.post(
            f'/api/schedules/date-polls/{poll.id}/vote/',
            {'votes': [{'option_id': option.id, 'status': 'available', 'comment': ''}]},
            format='json',
        )
        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.gm)
        confirm_response = self.client.post(
            f'/api/schedules/date-polls/{poll.id}/confirm/',
            {'option_id': option.id},
            format='json',
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        poll.refresh_from_db()
        self.assertTrue(poll.is_closed)
        self.assertIsNotNone(poll.session)

        confirm_again = self.client.post(
            f'/api/schedules/date-polls/{poll.id}/confirm/',
            {'option_id': option.id},
            format='json',
        )
        self.assertEqual(confirm_again.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.member)
        confirm_not_creator = self.client.post(
            f'/api/schedules/date-polls/{poll.id}/confirm/',
            {'option_id': option.id},
            format='json',
        )
        self.assertEqual(confirm_not_creator.status_code, status.HTTP_403_FORBIDDEN)

