from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from .models import TRPGSession, SessionParticipant, HandoutInfo
from accounts.models import Group as CustomGroup

User = get_user_model()


class ScheduleModelsTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User'
        )
        self.user2 = User.objects.create_user(
            username='playeruser',
            email='player@example.com',
            password='pass123',
            nickname='Player User'
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        self.group.members.add(self.user1, self.user2)

    def test_trpg_session_creation(self):
        """TRPGセッション作成テスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            description='Test Description',
            date=timezone.now() + timedelta(days=1),
            location='Online',
            gm=self.user1,
            group=self.group,
            duration_minutes=180
        )
        
        self.assertEqual(session.title, 'Test Session')
        self.assertEqual(session.gm, self.user1)
        self.assertEqual(session.group, self.group)
        self.assertEqual(session.duration_minutes, 180)
        self.assertEqual(session.status, 'planned')  # デフォルト値

    def test_session_participant_creation(self):
        """セッション参加者作成テスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player',
            character_name='Test Character'
        )
        
        self.assertEqual(participant.session, session)
        self.assertEqual(participant.user, self.user2)
        self.assertEqual(participant.role, 'player')
        self.assertEqual(participant.character_name, 'Test Character')

    def test_handout_creation(self):
        """ハンドアウト作成テスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player'
        )
        
        handout = HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title='Test Handout',
            content='Secret information...',
            is_secret=True
        )
        
        self.assertEqual(handout.title, 'Test Handout')
        self.assertEqual(handout.participant, participant)
        self.assertTrue(handout.is_secret)


class ScheduleAPITestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User'
        )
        self.user2 = User.objects.create_user(
            username='playeruser',
            email='player@example.com',
            password='pass123',
            nickname='Player User'
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        self.group.members.add(self.user1, self.user2)
        
        # テスト用セッション作成
        self.session = TRPGSession.objects.create(
            title='Test Session',
            description='Test Description',
            date=timezone.now() + timedelta(days=1),
            location='Online',
            gm=self.user1,
            group=self.group,
            duration_minutes=180
        )

    def test_sessions_list_unauthenticated(self):
        """未認証セッション一覧アクセステスト"""
        response = self.client.get('/api/schedules/sessions/view/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sessions_list_authenticated(self):
        """認証済みセッション一覧アクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        
        session_data = data['results'][0]
        self.assertEqual(session_data['title'], 'Test Session')
        self.assertEqual(session_data['gm_name'], 'GM User')

    def test_sessions_list_pagination(self):
        """セッション一覧ページネーションテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # パラメータ付きリクエスト
        response = self.client.get('/api/schedules/sessions/view/?limit=5&offset=0', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['limit'], 5)
        self.assertEqual(data['offset'], 0)
        self.assertIn('has_next', data)
        self.assertIn('has_previous', data)

    def test_session_viewset_list(self):
        """セッションViewSetリストテスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_viewset_detail(self):
        """セッションViewSet詳細テスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['title'], 'Test Session')
        self.assertEqual(data['gm'], self.user1.id)

    def test_session_creation_via_api(self):
        """API経由セッション作成テスト"""
        self.client.force_authenticate(user=self.user1)
        
        session_data = {
            'title': 'New Session',
            'description': 'New Description',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 240
        }
        
        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        created_session = TRPGSession.objects.get(title='New Session')
        self.assertEqual(created_session.gm, self.user1)
        self.assertEqual(created_session.duration_minutes, 240)

    def test_session_join_functionality(self):
        """セッション参加機能テスト"""
        self.client.force_authenticate(user=self.user2)
        
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 参加者が作成されたことを確認
        participant = SessionParticipant.objects.get(
            session=self.session,
            user=self.user2
        )
        self.assertEqual(participant.role, 'player')

    def test_session_join_duplicate(self):
        """重複セッション参加テスト"""
        self.client.force_authenticate(user=self.user2)
        
        # 最初の参加
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 重複参加試行
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_join_group_non_member_forbidden(self):
        """グループ外メンバーの参加拒否テスト"""
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass123',
            nickname='Outsider'
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_join_private_forbidden(self):
        """プライベートセッション参加拒否テスト"""
        self.session.visibility = 'private'
        self.session.save(update_fields=['visibility'])
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_calendar_api(self):
        """カレンダーAPIテスト"""
        self.client.force_authenticate(user=self.user1)
        
        start_date = timezone.now().date()
        end_date = (timezone.now() + timedelta(days=30)).date()
        
        response = self.client.get(
            f'/api/schedules/calendar/?start={start_date}&end={end_date}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calendar_api_missing_params(self):
        """カレンダーAPI必須パラメータ不足テスト"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/schedules/calendar/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)

    def test_participants_viewset(self):
        """参加者ViewSetテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 参加者作成
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )
        
        response = self.client.get('/api/schedules/participants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_handouts_viewset(self):
        """ハンドアウトViewSetテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 参加者とハンドアウト作成
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )
        
        HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='Test Handout',
            content='Secret info'
        )
        
        response = self.client.get('/api/schedules/handouts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
