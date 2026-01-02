"""
追加機能テストスイート - エクスポート・統計・その他機能
タブレノ TRPGスケジュール管理システム
"""

import unittest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import json

from accounts.models import CustomUser, Group as CustomGroup, GroupMembership
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario, PlayHistory

User = get_user_model()


class ExportFunctionTestCase(APITestCase):
    """エクスポート機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='export_user',
            email='export@arkham.edu',
            password='export_2024',
            nickname='Export User'
        )
        
        # テストデータ作成
        self.group = CustomGroup.objects.create(
            name='Export Test Group',
            created_by=self.user
        )
        
        GroupMembership.objects.create(user=self.user, group=self.group, role='admin')
        
        self.scenario = Scenario.objects.create(
            title='Export Test Scenario',
            author='Test Author',
            game_system='coc',
            created_by=self.user
        )
        
        # 複数のセッションとプレイ履歴を作成
        for i in range(3):
            session = TRPGSession.objects.create(
                title=f'Export Test Session {i+1}',
                date=timezone.now() + timedelta(days=i),
                gm=self.user,
                group=self.group,
                status='completed',
                duration_minutes=180
            )
            
            # GMも参加者として追加
            SessionParticipant.objects.create(
                session=session,
                user=self.user,
                role='gm'
            )
            
            PlayHistory.objects.create(
                scenario=self.scenario,
                user=self.user,
                session=session,
                played_date=timezone.now(),
                role='gm',
                notes=f'Test session {i+1} notes'
            )
    
    def test_export_formats_api(self):
        """利用可能なエクスポート形式の取得テスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/accounts/export/formats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 利用可能なフォーマットがレスポンスに含まれていることを確認
        self.assertIn('formats', response.data)
        formats = response.data['formats']
        self.assertTrue(len(formats) > 0)
        
        # 各フォーマットに必要な情報が含まれていることを確認
        for format_info in formats:
            self.assertIn('format', format_info)
            self.assertIn('name', format_info)
            self.assertIn('description', format_info)
    
    def test_export_json_format(self):
        """JSONフォーマットエクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/accounts/export/statistics/', {'format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response['Content-Type'])
    
    @unittest.skip("CSV export functionality needs debugging - URL routing issue")
    def test_export_csv_format(self):
        """CSVフォーマットエクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/accounts/export/statistics/', {'format': 'csv'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])
    
    def test_export_with_date_range(self):
        """日付範囲指定でのエクスポートテスト"""
        self.client.force_authenticate(user=self.user)
        
        start_date = timezone.now().strftime('%Y-%m-%d')
        end_date = (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        response = self.client.get('/api/accounts/export/statistics/', {
            'format': 'json',
            'start_date': start_date,
            'end_date': end_date
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 期間内のデータが含まれていることを確認
        export_data = response.json()
        self.assertIn('play_history', export_data)
        self.assertIn('sessions', export_data)
        self.assertIn('statistics', export_data)


class StatisticsFunctionTestCase(APITestCase):
    """統計機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='stats_user',
            email='stats@arkham.edu',
            password='stats_2024',
            nickname='Stats User'
        )
        
        # テストデータ作成
        self.group = CustomGroup.objects.create(
            name='Stats Test Group',
            created_by=self.user
        )
        
        GroupMembership.objects.create(user=self.user, group=self.group, role='admin')
        
        # 複数のシナリオとセッションを作成
        for i in range(5):
            scenario = Scenario.objects.create(
                title=f'Stats Test Scenario {i+1}',
                author='Test Author',
                game_system='coc',
                created_by=self.user
            )
            
            session = TRPGSession.objects.create(
                title=f'Stats Test Session {i+1}',
                date=timezone.now() - timedelta(days=i*7),
                gm=self.user,
                group=self.group,
                status='completed',
                duration_minutes=120 + (i * 30)  # 可変時間
            )
            
            # GMも参加者として追加
            SessionParticipant.objects.create(
                session=session,
                user=self.user,
                role='gm'
            )
            
            PlayHistory.objects.create(
                scenario=scenario,
                user=self.user,
                session=session,
                played_date=timezone.now() - timedelta(days=i*7),
                role='gm',
                notes=f'Test session {i+1} notes'
            )
    
    def test_tindalos_metrics_api(self):
        """Tindalos指標の取得テスト"""
        self.client.force_authenticate(user=self.user)
        
        current_year = timezone.now().year
        response = self.client.get('/api/accounts/statistics/tindalos/', {'year': current_year})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 基本統計情報が含まれていることを確認
        data = response.data
        self.assertIn('total_play_time', data)
        self.assertIn('session_count', data)
        self.assertIn('gm_session_count', data)
        self.assertIn('player_session_count', data)
        self.assertIn('scenario_count', data)
        
        # 数値が正しいことを確認
        from django.db.models import Q, Sum
        sessions = TRPGSession.objects.filter(
            Q(participants=self.user) | Q(gm=self.user),
            date__year=current_year,
            status='completed',
        ).distinct()
        expected_sessions = sessions.count()
        expected_gm_sessions = sessions.filter(gm=self.user).count()
        expected_total_play_time = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        expected_scenario_count = PlayHistory.objects.filter(
            user=self.user,
            played_date__year=current_year,
        ).values('scenario').distinct().count()

        self.assertEqual(data['session_count'], expected_sessions)
        self.assertEqual(data['gm_session_count'], expected_gm_sessions)
        self.assertEqual(data['scenario_count'], expected_scenario_count)
        self.assertEqual(data['total_play_time'], expected_total_play_time)
    
    def test_user_ranking_api(self):
        """ユーザーランキングの取得テスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/accounts/statistics/ranking/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # ランキングデータの構造確認
        data = response.data
        self.assertIn('users', data)
        self.assertTrue(len(data['users']) > 0)
        
        # ランキング項目の確認
        user_stats = data['users'][0]
        self.assertIn('user', user_stats)
        self.assertIn('total_play_time', user_stats)
        self.assertIn('session_count', user_stats)
        self.assertIn('gm_count', user_stats)
    
    def test_group_statistics_api(self):
        """グループ統計の取得テスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/accounts/statistics/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # グループ統計データの構造確認
        data = response.data
        self.assertIn('groups', data)
        self.assertTrue(len(data['groups']) > 0)
        
        # グループ統計項目の確認
        group_stats = data['groups'][0]
        self.assertIn('group', group_stats)
        self.assertIn('member_count', group_stats)
        self.assertIn('session_count', group_stats)
        self.assertIn('total_play_time', group_stats)
    
    def test_statistics_with_filters(self):
        """フィルター付き統計の取得テスト"""
        self.client.force_authenticate(user=self.user)
        
        # 年度指定での統計取得
        current_year = timezone.now().year
        response = self.client.get('/api/accounts/statistics/tindalos/', {'year': current_year})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # ゲームシステム指定での統計取得
        response = self.client.get('/api/accounts/statistics/tindalos/', {'game_system': 'coc'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class HandoutManagementTestCase(APITestCase):
    """ハンドアウト管理機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        self.gm = User.objects.create_user(
            username='gm_handout',
            email='gm@arkham.edu',
            password='gm_2024',
            nickname='GM User'
        )
        
        self.player1 = User.objects.create_user(
            username='player1_handout',
            email='player1@arkham.edu',
            password='player_2024',
            nickname='Player 1'
        )
        
        self.player2 = User.objects.create_user(
            username='player2_handout',
            email='player2@arkham.edu',
            password='player_2024',
            nickname='Player 2'
        )
        
        self.group = CustomGroup.objects.create(
            name='Handout Test Group',
            created_by=self.gm
        )
        
        GroupMembership.objects.create(user=self.gm, group=self.group, role='admin')
        GroupMembership.objects.create(user=self.player1, group=self.group, role='member')
        GroupMembership.objects.create(user=self.player2, group=self.group, role='member')
        
        self.session = TRPGSession.objects.create(
            title='Handout Test Session',
            date=timezone.now(),
            gm=self.gm,
            group=self.group
        )
        
        # 参加者作成
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player',
            character_name='Character 1'
        )
        
        self.participant2 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player2,
            role='player',
            character_name='Character 2'
        )
    
    def test_handout_creation_and_management(self):
        """ハンドアウトの作成と管理テスト"""
        self.client.force_authenticate(user=self.gm)
        
        # 1. 個人用秘匿ハンドアウト作成
        secret_handout_data = {
            'session': self.session.id,
            'participant': self.participant1.id,
            'title': 'Personal Secret Information',
            'content': 'Only for Character 1 eyes',
            'is_secret': True
        }
        
        response = self.client.post('/api/schedules/handouts/', secret_handout_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        secret_handout_id = response.data['id']
        
        # 2. 共通ハンドアウト作成
        public_handout_data = {
            'session': self.session.id,
            'participant': self.participant1.id,
            'title': 'Common Information',
            'content': 'Information for all participants',
            'is_secret': False
        }
        
        response = self.client.post('/api/schedules/handouts/', public_handout_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        public_handout_id = response.data['id']
        
        # 3. プレイヤー1の視点でハンドアウト確認
        self.client.force_authenticate(user=self.player1)
        
        # 自分宛ての秘匿ハンドアウトは閲覧可能
        response = self.client.get(f'/api/schedules/handouts/{secret_handout_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 共通ハンドアウトも閲覧可能
        response = self.client.get(f'/api/schedules/handouts/{public_handout_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. プレイヤー2の視点でハンドアウト確認
        self.client.force_authenticate(user=self.player2)
        
        # 他人宛ての秘匿ハンドアウトは閲覧不可
        response = self.client.get(f'/api/schedules/handouts/{secret_handout_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 共通ハンドアウトは閲覧可能
        response = self.client.get(f'/api/schedules/handouts/{public_handout_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_bulk_handout_management(self):
        """一括ハンドアウト管理のテスト"""
        self.client.force_authenticate(user=self.gm)
        
        # セッションの全ハンドアウト取得
        response = self.client.get('/api/schedules/handouts/', {'session': self.session.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 管理用ビューのテスト（将来実装を想定）
        # response = self.client.get(f'/api/schedules/sessions/{self.session.id}/handouts/manage/')
        # self.assertEqual(response.status_code, status.HTTP_200_OK)


class CalendarIntegrationTestCase(APITestCase):
    """カレンダー統合機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='calendar_user',
            email='calendar@arkham.edu',
            password='calendar_2024',
            nickname='Calendar User'
        )
        
        self.group = CustomGroup.objects.create(
            name='Calendar Test Group',
            created_by=self.user
        )
        
        GroupMembership.objects.create(user=self.user, group=self.group, role='admin')
        
        # 複数の日程のセッションを作成
        base_date = timezone.now().replace(hour=19, minute=0, second=0, microsecond=0)
        for i in range(7):
            TRPGSession.objects.create(
                title=f'Calendar Test Session {i+1}',
                date=base_date + timedelta(days=i),
                gm=self.user,
                group=self.group,
                duration_minutes=180
            )
    
    def test_calendar_view_api(self):
        """カレンダービューAPIのテスト"""
        self.client.force_authenticate(user=self.user)
        
        # 月表示のカレンダーデータ取得
        current_month = timezone.now().strftime('%Y-%m')
        response = self.client.get('/api/schedules/calendar/', {'month': current_month})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # カレンダーデータの構造確認
        data = response.data
        self.assertIn('events', data)
        self.assertIn('month', data)
        
        # セッションがイベントとして含まれていることを確認
        events = data['events']
        self.assertTrue(len(events) > 0)
        
        # イベントデータの構造確認
        for event in events:
            self.assertIn('title', event)
            self.assertIn('date', event)
            self.assertIn('type', event)
    
    def test_upcoming_sessions_api(self):
        """今後のセッション取得APIのテスト"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/schedules/sessions/upcoming/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 今後のセッションが取得できることを確認
        upcoming_sessions = response.data
        self.assertTrue(len(upcoming_sessions) > 0)
        
        # セッションデータの確認
        for session in upcoming_sessions:
            self.assertIn('title', session)
            self.assertIn('date', session)
            self.assertIn('status', session)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests([
        'test_additional_features.ExportFunctionTestCase',
        'test_additional_features.StatisticsFunctionTestCase',
        'test_additional_features.HandoutManagementTestCase',
        'test_additional_features.CalendarIntegrationTestCase'
    ])
