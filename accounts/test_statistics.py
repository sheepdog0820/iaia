from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from .models import CustomUser, Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario, PlayHistory

User = get_user_model()


class StatisticsViewsTestCase(APITestCase):
    """統計ビューのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='pass123',
            nickname='Test User 1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='pass123',
            nickname='Test User 2'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            description='Test Description',
            created_by=self.user1
        )
        GroupMembership.objects.create(
            user=self.user1,
            group=self.group,
            role='admin'
        )
        GroupMembership.objects.create(
            user=self.user2,
            group=self.group,
            role='member'
        )
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            game_system='coc',
            created_by=self.user1,
            difficulty='intermediate',
            estimated_duration='medium'
        )
        
        # セッション作成（今年のデータ）
        current_year = timezone.now().year
        for i in range(5):
            session = TRPGSession.objects.create(
                title=f'Session {i+1}',
                date=timezone.now() - timedelta(days=i*30),
                gm=self.user1,
                group=self.group,
                duration_minutes=180,
                status='completed'
            )
            # 参加者追加
            SessionParticipant.objects.create(
                session=session,
                user=self.user1,
                role='gm'
            )
            SessionParticipant.objects.create(
                session=session,
                user=self.user2,
                role='player'
            )
            # プレイ履歴追加
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user1,
                session=session,
                played_date=session.date,
                role='gm'
            )
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user2,
                session=session,
                played_date=session.date,
                role='player'
            )
        
        # 昨年のデータも作成
        for i in range(3):
            session = TRPGSession.objects.create(
                title=f'Old Session {i+1}',
                date=timezone.now() - timedelta(days=365+i*30),
                gm=self.user1,
                group=self.group,
                duration_minutes=240,
                status='completed'
            )
            SessionParticipant.objects.create(
                session=session,
                user=self.user1,
                role='gm'
            )

    def test_tindalos_metrics_unauthenticated(self):
        """未認証でのTindalos Metricsアクセステスト"""
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tindalos_metrics_authenticated(self):
        """認証済みTindalos Metricsアクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # 基本構造の確認
        self.assertIn('user', data)
        self.assertIn('year', data)
        self.assertIn('yearly_stats', data)
        self.assertIn('monthly_stats', data)
        self.assertIn('system_stats', data)
        self.assertIn('role_stats', data)
        self.assertIn('group_stats', data)
        self.assertIn('recent_sessions', data)
        
        # ユーザー情報の確認
        self.assertEqual(data['user']['id'], self.user1.id)
        self.assertEqual(data['user']['nickname'], 'Test User 1')
        
        # 年間統計の確認
        yearly_stats = data['yearly_stats']
        self.assertIn('total_sessions', yearly_stats)
        self.assertIn('total_hours', yearly_stats)
        self.assertIn('avg_session_hours', yearly_stats)
        self.assertEqual(yearly_stats['total_sessions'], 5)  # 今年の5セッション
        
        # システム統計の確認
        system_stats = data['system_stats']
        self.assertIsInstance(system_stats, list)
        if system_stats:
            self.assertIn('system', system_stats[0])
            self.assertIn('session_count', system_stats[0])
            self.assertIn('total_hours', system_stats[0])

    def test_tindalos_metrics_with_year_parameter(self):
        """年パラメータ付きTindalos Metricsテスト"""
        self.client.force_authenticate(user=self.user1)
        last_year = timezone.now().year - 1
        response = self.client.get(f'/api/accounts/statistics/tindalos/?year={last_year}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['year'], last_year)
        # 昨年のデータ確認
        self.assertEqual(data['yearly_stats']['total_sessions'], 3)

    def test_user_ranking_unauthenticated(self):
        """未認証でのユーザーランキングアクセステスト"""
        response = self.client.get('/api/accounts/statistics/ranking/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_ranking_authenticated(self):
        """認証済みユーザーランキングアクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/ranking/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # 基本構造の確認
        self.assertIn('year', data)
        self.assertIn('type', data)
        self.assertIn('ranking', data)
        
        # ランキングの確認
        ranking = data['ranking']
        self.assertIsInstance(ranking, list)
        if ranking:
            self.assertIn('rank', ranking[0])
            self.assertIn('user_id', ranking[0])
            self.assertIn('nickname', ranking[0])
            self.assertIn('total_hours', ranking[0])

    def test_group_statistics_unauthenticated(self):
        """未認証でのグループ統計アクセステスト"""
        response = self.client.get('/api/accounts/statistics/groups/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_statistics_authenticated(self):
        """認証済みグループ統計アクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # 基本構造の確認
        self.assertIn('year', data)
        self.assertIn('groups', data)
        
        # グループ詳細の確認
        groups = data['groups']
        self.assertIsInstance(groups, list)
        self.assertEqual(len(groups), 1)
        
        group_data = groups[0]
        self.assertIn('group', group_data)
        self.assertIn('id', group_data['group'])
        self.assertIn('name', group_data['group'])
        self.assertIn('member_count', group_data)
        self.assertIn('session_count', group_data)
        self.assertIn('total_play_time', group_data)
        
        # データの正確性確認
        self.assertEqual(group_data['group']['name'], 'Test Group')
        self.assertEqual(group_data['member_count'], 2)
        self.assertEqual(group_data['session_count'], 5)  # 今年の5セッション

    def test_role_statistics(self):
        """役割別統計のテスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        role_stats = data['role_stats']
        
        # GMとプレイヤーの統計が含まれているか確認
        self.assertIn('gm', role_stats)
        self.assertIn('pl', role_stats)
        
        # GM統計の確認（user1は全セッションでGM）
        self.assertEqual(role_stats['gm']['session_count'], 5)  # 今年の5セッション
        self.assertGreater(role_stats['gm']['total_hours'], 0)

    def test_monthly_statistics(self):
        """月別統計のテスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        monthly_stats = data['monthly_stats']
        
        # 月別統計が12ヶ月分あることを確認
        self.assertIsInstance(monthly_stats, list)
        self.assertEqual(len(monthly_stats), 12)
        
        # 各月のデータ構造確認
        for month_data in monthly_stats:
            self.assertIn('month', month_data)
            self.assertIn('session_count', month_data)
            self.assertIn('total_hours', month_data)
            self.assertGreaterEqual(month_data['month'], 1)
            self.assertLessEqual(month_data['month'], 12)

    def test_recent_sessions(self):
        """最近のセッション履歴テスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        recent_sessions = data['recent_sessions']
        
        # 最近のセッションが含まれているか確認
        self.assertIsInstance(recent_sessions, list)
        self.assertGreater(len(recent_sessions), 0)
        self.assertLessEqual(len(recent_sessions), 10)  # 最大10件
        
        # セッションデータの構造確認
        if recent_sessions:
            session = recent_sessions[0]
            self.assertIn('title', session)
            self.assertIn('date', session)
            self.assertIn('role', session)
            self.assertIn('duration_hours', session)
            self.assertIn('group_name', session)

    def test_empty_statistics(self):
        """データがない場合の統計テスト"""
        # 新規ユーザーを作成（データなし）
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass123',
            nickname='New User'
        )
        
        self.client.force_authenticate(user=new_user)
        response = self.client.get('/api/accounts/statistics/tindalos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # 空のデータでもエラーにならないことを確認
        self.assertEqual(data['yearly_stats']['total_sessions'], 0)
        self.assertEqual(data['yearly_stats']['total_hours'], 0)
        self.assertEqual(len(data['recent_sessions']), 0)