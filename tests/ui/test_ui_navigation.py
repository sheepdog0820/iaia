"""
UI Navigation Test Suite
Tests for verifying UI navigation works correctly across all screens
"""

from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Group, GroupMembership
from scenarios.models import Scenario
from schedules.models import TRPGSession

User = get_user_model()


class UINavigationTestCase(TestCase):
    """UI ナビゲーションのテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123", nickname="Test User"
        )
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])

        # グループ作成
        self.group = Group.objects.create(name="Test Group", created_by=self.user)
        GroupMembership.objects.create(user=self.user, group=self.group, role="admin")

        # セッション作成
        self.session = TRPGSession.objects.create(
            title="Test Session",
            date=timezone.now() + timedelta(days=1),
            gm=self.user,
            group=self.group,
            duration_minutes=180,
        )

        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title="Test Scenario", author="Test Author", created_by=self.user, game_system="coc"
        )

    def test_home_page_navigation(self):
        """ホームページのナビゲーションテスト"""
        # 未認証アクセス
        response = self.client.get("/")
        self.assertRedirects(response, "/accounts/login/?next=/", fetch_redirect_response=False)

        # 認証済みアクセス
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")
        self.assertContains(response, "create-7th-btn")
        self.assertContains(response, "/accounts/character/create/7th/")
        self.assertContains(response, "カレンダー")
        self.assertContains(response, "セッション")
        self.assertContains(response, "シナリオ")
        self.assertContains(response, "グループ")

    def test_calendar_page_navigation(self):
        """カレンダーページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/api/schedules/calendar/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chrono Abyss")
        # セッション詳細へのリンク確認
        self.assertContains(response, "handleEventClick")
        self.assertContains(response, "occurrence_id=")
        # イベントツールチップの導入確認
        self.assertContains(response, "calendar-event-tooltip")
        self.assertContains(response, "calendar-day-saturday")
        self.assertContains(response, "calendar-day-sunday")
        self.assertContains(response, "calendar-day-holiday")
        self.assertContains(response, "/api/schedules/calendar/holidays/")
        self.assertContains(response, "calendar-holiday-label")

    def test_sessions_page_navigation(self):
        """セッション一覧ページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/api/schedules/sessions/view/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R'lyeh Log")
        detail_url = reverse("session_detail", kwargs={"pk": self.session.id})
        self.assertContains(response, detail_url)

    def test_session_detail_navigation(self):
        """セッション詳細ページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/detail/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Session")
        self.assertContains(response, "Test User")

    def test_scenarios_archive_navigation(self):
        """シナリオアーカイブページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/api/scenarios/archive/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mythos Archive")
        self.assertContains(response, "showScenarioDetail")

    def test_groups_management_navigation(self):
        """グループ管理ページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/accounts/groups/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cult Circle")
        self.assertContains(response, "showGroupDetail")

    def test_statistics_page_navigation(self):
        """統計ページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/accounts/statistics/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tindalos Metrics")

    def test_dashboard_navigation(self):
        """ダッシュボードのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")
        self.assertContains(response, "ダッシュボード")

    def test_authentication_flow(self):
        """認証フローのテスト"""
        # ログインページ
        response = self.client.get("/login/")
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertContains(response, "Gate of Yog-Sothoth")

        # ログイン処理
        response = self.client.post("/login/", {"username": "testuser", "password": "testpass123"})
        self.assertRedirects(response, "/accounts/dashboard/")

        # ログアウト処理
        response = self.client.get(reverse("account_logout"))
        self.assertIn(response.status_code, [200, 302])

    def test_navigation_links_consistency(self):
        """ナビゲーションリンクの一貫性テスト"""
        self.client.login(username="testuser", password="testpass123")

        # JavaScriptで定義されているページに実際にアクセス可能か確認
        pages = [
            "/api/schedules/calendar/view/",
            "/api/schedules/sessions/view/",
            "/api/scenarios/archive/view/",
            "/accounts/groups/view/",
            "/accounts/statistics/view/",
        ]

        for page in pages:
            response = self.client.get(page, HTTP_ACCEPT="text/html")
            self.assertIn(
                response.status_code, [200, 302], f"Page {page} returned unexpected status code: {response.status_code}"
            )

    def test_responsive_navigation(self):
        """レスポンシブナビゲーションのテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # モバイルナビゲーション要素の確認
        self.assertContains(response, "navbar-toggler")
        self.assertContains(response, "navbarNav")

    def test_navbar_has_visible_contrast_styles_for_light_and_dark_modes(self):
        """ナビゲーションがライト/ダーク両方で見えるスタイルを持つ"""
        stylesheet = Path("static/css/arkham_modern.css").read_text(encoding="utf-8")

        self.assertIn("--nav-accent-text: var(--accent-primary-dark);", stylesheet)
        self.assertIn("--nav-accent-text: #93c5fd;", stylesheet)
        self.assertIn("--navbar-toggler-bg:", stylesheet)
        self.assertIn("--navbar-toggler-border:", stylesheet)
        self.assertIn(".navbar-toggler {", stylesheet)
        self.assertIn("min-width: 44px;", stylesheet)
        self.assertIn("min-height: 40px;", stylesheet)
        self.assertIn("border: 1px solid var(--navbar-toggler-border);", stylesheet)
        self.assertIn(".navbar-toggler-icon {", stylesheet)
        self.assertIn("linear-gradient(currentColor, currentColor)", stylesheet)
        self.assertIn("background-size: 100% 2px;", stylesheet)
        self.assertIn(".navbar-nav .nav-link:hover {", stylesheet)
        self.assertIn("color: var(--nav-accent-text) !important;", stylesheet)
        self.assertIn(".dropdown-item:hover {", stylesheet)
        self.assertIn(".dropdown-header {", stylesheet)
        self.assertIn("color: var(--text-secondary);", stylesheet)
        self.assertIn(".dropdown-divider {", stylesheet)

    def test_card_header_tabs_and_muted_text_have_visible_contrast(self):
        stylesheet = Path("static/css/arkham_modern.css").read_text(encoding="utf-8")

        self.assertIn("--card-header-gradient:", stylesheet)
        self.assertIn("background: var(--card-header-gradient) !important;", stylesheet)
        self.assertIn(".card-header .text-muted,", stylesheet)
        self.assertIn(".card-header small,", stylesheet)
        self.assertIn("color: #ffffff !important;", stylesheet)
        self.assertIn(".card-header .card-header-tabs .nav-link", stylesheet)
        self.assertIn(".card-header .card-header-tabs .nav-link.active", stylesheet)
        self.assertIn("background: rgba(15, 23, 42, 0.24);", stylesheet)
        self.assertIn("border-bottom-color: rgba(255, 255, 255, 0.35);", stylesheet)
        self.assertIn(".card-header.bg-primary", stylesheet)
        self.assertIn(".card-header.bg-info", stylesheet)
        self.assertIn(".card-header.bg-success", stylesheet)
        self.assertIn(".card-header.bg-warning", stylesheet)
        self.assertIn(".card-header.bg-danger", stylesheet)
        self.assertIn(".card-header.bg-secondary", stylesheet)
        self.assertIn("background: linear-gradient(135deg, #0e7490 0%, #155e75 100%) !important;", stylesheet)
        self.assertIn("background: linear-gradient(135deg, #047857 0%, #065f46 100%) !important;", stylesheet)
        self.assertIn("background: linear-gradient(135deg, #b45309 0%, #92400e 100%) !important;", stylesheet)
        self.assertIn("background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%) !important;", stylesheet)
        self.assertIn("background: linear-gradient(135deg, #475569 0%, #334155 100%) !important;", stylesheet)

    def test_outline_buttons_have_visible_contrast_in_light_and_dark_modes(self):
        stylesheet = Path("static/css/arkham_modern.css").read_text(encoding="utf-8")

        self.assertIn("--button-outline-primary-text: var(--accent-primary-dark);", stylesheet)
        self.assertIn("--button-outline-primary-text: #93c5fd;", stylesheet)
        self.assertIn("--button-outline-secondary-text: var(--text-secondary);", stylesheet)
        self.assertIn("--button-outline-secondary-text: #cbd5e1;", stylesheet)
        self.assertIn(".btn-outline-primary {", stylesheet)
        self.assertIn("border: 2px solid var(--button-outline-primary-text);", stylesheet)
        self.assertIn("color: var(--button-outline-primary-text);", stylesheet)
        self.assertIn(".btn-outline-secondary {", stylesheet)
        self.assertIn("border: 2px solid var(--button-outline-secondary-text);", stylesheet)
        self.assertIn("color: var(--button-outline-secondary-text);", stylesheet)

    def test_breadcrumb_navigation(self):
        """パンくずナビゲーションのテスト"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/detail/")
        self.assertEqual(response.status_code, 200)
        # アイコンが含まれているか確認
        self.assertContains(response, "fas fa-home")

    def test_error_page_navigation(self):
        """エラーページのナビゲーションテスト"""
        self.client.login(username="testuser", password="testpass123")
        # 存在しないページ
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get("/nonexistent-page/")
        self.assertEqual(response.status_code, 404)

    def test_session_join_navigation(self):
        """セッション参加ナビゲーションのテスト"""
        self.client.login(username="testuser", password="testpass123")
        # セッション詳細ページから参加ボタンの確認
        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/detail/")
        self.assertEqual(response.status_code, 200)
        # 参加/退出ボタンの存在確認
        self.assertContains(response, "joinSession")

    def test_modal_navigation(self):
        """モーダルナビゲーションのテスト"""
        self.client.login(username="testuser", password="testpass123")

        # シナリオアーカイブのモーダル
        response = self.client.get("/api/scenarios/archive/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "scenarioDetailModal")
        self.assertContains(response, "addScenarioModal")

        # グループ管理のモーダル
        response = self.client.get("/accounts/groups/view/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "createGroupModal")
        self.assertContains(response, "groupDetailModal")
