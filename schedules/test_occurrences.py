"""
セッション複数日程 (SessionOccurrence) のAPI/同期テスト
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionOccurrence


class SessionOccurrenceAPITestCase(APITestCase):
    def setUp(self):
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='pass1234',
            nickname='GM',
        )
        self.member_user = CustomUser.objects.create_user(
            username='member_user',
            email='member@example.com',
            password='pass1234',
            nickname='Member',
        )
        self.group = Group.objects.create(
            name='Test Group',
            description='Group for occurrence tests',
            created_by=self.gm_user,
        )
        self.group.members.add(self.gm_user, self.member_user)

        self.session = TRPGSession.objects.create(
            title='Test Session',
            description='',
            date=timezone.now().replace(microsecond=0),
            duration_minutes=180,
            location='',
            gm=self.gm_user,
            group=self.group,
            status='planned',
            visibility='group',
        )
        self.primary_occurrence = self.session.occurrences.get(is_primary=True)

    def test_primary_occurrence_is_created_and_synced(self):
        self.assertEqual(
            SessionOccurrence.objects.filter(session=self.session, is_primary=True).count(),
            1,
        )
        self.assertEqual(self.primary_occurrence.start_at, self.session.date)

    def test_primary_occurrence_patch_updates_session_date(self):
        self.client.force_authenticate(user=self.gm_user)
        new_start_at = (self.session.date + timedelta(days=7)).replace(microsecond=0)

        response = self.client.patch(
            f'/api/schedules/occurrences/{self.primary_occurrence.id}/',
            {'start_at': new_start_at.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.session.refresh_from_db()
        self.primary_occurrence.refresh_from_db()
        self.assertEqual(self.primary_occurrence.start_at, new_start_at)
        self.assertEqual(self.session.date, new_start_at)

    def test_create_occurrence_allows_blank_content(self):
        self.client.force_authenticate(user=self.gm_user)
        start_at = (self.session.date + timedelta(days=1)).replace(microsecond=0)

        response = self.client.post(
            '/api/schedules/occurrences/',
            {
                'session': self.session.id,
                'start_at': start_at.isoformat(),
                'content': '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        occurrence = SessionOccurrence.objects.get(id=response.data['id'])
        self.assertFalse(occurrence.is_primary)
        self.assertEqual(occurrence.start_at, start_at)
        self.assertEqual(occurrence.content, '')

    def test_non_gm_cannot_create_occurrence(self):
        self.client.force_authenticate(user=self.member_user)
        start_at = (self.session.date + timedelta(days=2)).replace(microsecond=0)

        response = self.client.post(
            '/api/schedules/occurrences/',
            {'session': self.session.id, 'start_at': start_at.isoformat(), 'content': ''},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_occurrence_participants_must_belong_to_group(self):
        self.client.force_authenticate(user=self.gm_user)
        outsider = CustomUser.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass1234',
        )
        start_at = (self.session.date + timedelta(days=3)).replace(microsecond=0)

        response = self.client.post(
            '/api/schedules/occurrences/',
            {
                'session': self.session.id,
                'start_at': start_at.isoformat(),
                'participants': [outsider.id],
                'content': '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participants', response.data)

    def test_delete_primary_occurrence_is_rejected(self):
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.delete(f'/api/schedules/occurrences/{self.primary_occurrence.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SessionOccurrence.objects.filter(id=self.primary_occurrence.id).exists())

    def test_delete_non_primary_occurrence_is_allowed(self):
        self.client.force_authenticate(user=self.gm_user)
        start_at = (self.session.date + timedelta(days=4)).replace(microsecond=0)
        occurrence = SessionOccurrence.objects.create(session=self.session, start_at=start_at)

        response = self.client.delete(f'/api/schedules/occurrences/{occurrence.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SessionOccurrence.objects.filter(id=occurrence.id).exists())

    def test_calendar_events_use_occurrence_id(self):
        self.client.force_authenticate(user=self.member_user)
        start = (self.session.date - timedelta(days=1)).replace(microsecond=0)
        end = (self.session.date + timedelta(days=1)).replace(microsecond=0)

        response = self.client.get(
            '/api/schedules/calendar/',
            {'start': start.isoformat(), 'end': end.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        events = response.data
        target = next((e for e in events if e.get('session_id') == self.session.id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target.get('id'), self.primary_occurrence.id)
        self.assertEqual(target.get('occurrence_id'), self.primary_occurrence.id)
