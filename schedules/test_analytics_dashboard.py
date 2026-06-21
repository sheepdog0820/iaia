from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from .models import TRPGSession, SessionParticipant

User = get_user_model()


class SessionAnalyticsDashboardApiTestCase(APITestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='pass123',
            nickname='GM',
        )
        self.player1 = User.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass123',
            nickname='Player 1',
        )
        self.player2 = User.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='pass123',
            nickname='Player 2',
        )

        self.group = Group.objects.create(
            name='Group',
            created_by=self.gm,
        )
        GroupMembership.objects.create(user=self.gm, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.player1, group=self.group, role='member')
        GroupMembership.objects.create(user=self.player2, group=self.group, role='member')

        now = timezone.now()
        self.session1 = TRPGSession.objects.create(
            title='Session 1',
            date=(now - timedelta(days=10)).replace(hour=20, minute=0, second=0, microsecond=0),
            gm=self.gm,
            group=self.group,
            duration_minutes=180,
            actual_duration_minutes=210,
        )
        self.session2 = TRPGSession.objects.create(
            title='Session 2',
            date=(now - timedelta(days=40)).replace(hour=21, minute=0, second=0, microsecond=0),
            gm=self.gm,
            group=self.group,
            duration_minutes=240,
        )

        SessionParticipant.objects.create(session=self.session1, user=self.player1, role='player')
        SessionParticipant.objects.create(session=self.session2, user=self.player1, role='player')
        SessionParticipant.objects.create(session=self.session2, user=self.player2, role='player')

    def test_dashboard_returns_expected_shape(self):
        self.client.force_authenticate(user=self.gm)

        now = timezone.now().date()
        start = (now - timedelta(days=60)).isoformat()
        end = now.isoformat()

        response = self.client.get(
            f'/api/schedules/analytics/dashboard/?group_id={self.group.id}&start_date={start}&end_date={end}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('summary', data)
        self.assertIn('popular_hours', data)
        self.assertIn('monthly_trend', data)
        self.assertIn('gm_load', data)
        self.assertIn('top_pairs', data)
        self.assertIn('member_participation', data)

        summary = data['summary']
        self.assertEqual(summary['occurrences_count'], 2)
        self.assertEqual(summary['sessions_count'], 2)
        self.assertEqual(summary['total_minutes'], 450)
        self.assertEqual(summary['group_member_count'], 3)
        self.assertEqual(summary['avg_participants'], 2.5)
        self.assertEqual(summary['avg_participation_rate'], 83.3)

        gm_load = data['gm_load']
        self.assertEqual(gm_load[0]['gm_id'], self.gm.id)
        self.assertEqual(gm_load[0]['occurrences'], 2)

        top_pairs = data['top_pairs']
        self.assertGreaterEqual(len(top_pairs), 1)
        self.assertEqual(top_pairs[0]['occurrences_together'], 2)

        member_counts = {row['user_id']: row['occurrences'] for row in data['member_participation']}
        self.assertEqual(member_counts[self.gm.id], 2)
        self.assertEqual(member_counts[self.player1.id], 2)
        self.assertEqual(member_counts[self.player2.id], 1)

    def test_group_filter_requires_membership(self):
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass123',
            nickname='Outsider',
        )
        self.client.force_authenticate(user=outsider)

        response = self.client.get(f'/api/schedules/analytics/dashboard/?group_id={self.group.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
