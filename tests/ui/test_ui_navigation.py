"""
UI Navigation Test Suite
Tests for verifying UI navigation works correctly across all screens
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import Group, GroupMembership
from schedules.models import TRPGSession
from scenarios.models import Scenario
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class UINavigationTestCase(TestCase):
    """UI ナビゲーションのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            nickname='Test User'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        GroupMembership.objects.create(
            user=self.user,
            group=self.group,
            role='admin'
        )
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user,
            group=self.group,
            duration_minutes=180
        )
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )

    def test_home_page_navigation(self):
        """ホームページのナビゲーションテスト"""
        # 未認証アクセス
        response = self.client.get('/')
        self.assertRedirects(response, '/accounts/login/?next=/', fetch_redirect_response=False)
        
        # 認証済みアクセス
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        self.assertContains(response, 'カレンダー')
        self.assertContains(response, 'セッション')
        self.assertContains(response, 'シナリオ')
        self.assertContains(response, 'グループ')

    def test_calendar_page_navigation(self):
        """カレンダーページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/schedules/calendar/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chrono Abyss')
        # セッション詳細へのリンク確認
        self.assertContains(response, 'handleEventClick')

    def test_sessions_page_navigation(self):
        """セッション一覧ページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R'lyeh Log")

    def test_session_detail_navigation(self):
        """セッション詳細ページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Session')
        self.assertContains(response, 'Test User')

    def test_scenarios_archive_navigation(self):
        """シナリオアーカイブページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/scenarios/archive/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mythos Archive')
        self.assertContains(response, 'showScenarioDetail')

    def test_groups_management_navigation(self):
        """グループ管理ページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/groups/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cult Circle')
        self.assertContains(response, 'showGroupDetail')

    def test_statistics_page_navigation(self):
        """統計ページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/statistics/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tindalos Metrics')

    def test_dashboard_navigation(self):
        """ダッシュボードのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        self.assertContains(response, 'ダッシュボード')

    def test_authentication_flow(self):
        """認証フローのテスト"""
        # ログインページ
        response = self.client.get('/login/')
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertContains(response, 'Gate of Yog-Sothoth')
        
        # ログイン処理
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/accounts/dashboard/')
        
        # ログアウト処理
        response = self.client.get(reverse('account_logout'))
        self.assertIn(response.status_code, [200, 302])

    def test_navigation_links_consistency(self):
        """ナビゲーションリンクの一貫性テスト"""
        self.client.login(username='testuser', password='testpass123')
        
        # JavaScriptで定義されているページに実際にアクセス可能か確認
        pages = [
            '/api/schedules/calendar/view/',
            '/api/schedules/sessions/view/',
            '/api/scenarios/archive/view/',
            '/accounts/groups/view/',
            '/accounts/statistics/view/',
        ]
        
        for page in pages:
            response = self.client.get(page, HTTP_ACCEPT='text/html')
            self.assertIn(response.status_code, [200, 302], 
                         f"Page {page} returned unexpected status code: {response.status_code}")

    def test_responsive_navigation(self):
        """レスポンシブナビゲーションのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # モバイルナビゲーション要素の確認
        self.assertContains(response, 'navbar-toggler')
        self.assertContains(response, 'navbarNav')

    def test_breadcrumb_navigation(self):
        """パンくずナビゲーションのテスト"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        # アイコンが含まれているか確認
        self.assertContains(response, 'fas fa-home')

    def test_error_page_navigation(self):
        """エラーページのナビゲーションテスト"""
        self.client.login(username='testuser', password='testpass123')
        # 存在しないページ
        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)

    def test_session_join_navigation(self):
        """セッション参加ナビゲーションのテスト"""
        self.client.login(username='testuser', password='testpass123')
        # セッション詳細ページから参加ボタンの確認
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        # 参加/退出ボタンの存在確認
        self.assertContains(response, 'joinSession')

    def test_modal_navigation(self):
        """モーダルナビゲーションのテスト"""
        self.client.login(username='testuser', password='testpass123')
        
        # シナリオアーカイブのモーダル
        response = self.client.get('/api/scenarios/archive/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'scenarioDetailModal')
        self.assertContains(response, 'addScenarioModal')
        
        # グループ管理のモーダル
        response = self.client.get('/accounts/groups/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'createGroupModal')
        self.assertContains(response, 'groupDetailModal')
