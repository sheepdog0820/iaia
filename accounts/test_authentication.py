from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser
from accounts.models import Group as CustomGroup

User = get_user_model()


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'nickname': 'testuser'
        }
        self.user = User.objects.create_user(
            username='testuser',  # CustomUserでも username が必要
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )

    def test_user_creation(self):
        """ユーザー作成のテスト"""
        self.assertTrue(isinstance(self.user, CustomUser))
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.nickname, 'testuser')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_login_page_accessible(self):
        """ログインページのアクセステスト"""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ログイン')

    def test_demo_login_page_accessible(self):
        """デモログインページのアクセステスト"""
        response = self.client.get('/accounts/demo/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'デモログイン')

    def test_mock_social_login_google(self):
        """Googleモックソーシャルログインのテスト"""
        response = self.client.get('/accounts/mock-social/google/')
        # リダイレクト（ログイン成功）またはダッシュボードを確認
        self.assertIn(response.status_code, [200, 302])

    def test_mock_social_login_twitter(self):
        """Twitterモックソーシャルログインのテスト"""
        response = self.client.get('/accounts/mock-social/twitter/')
        # リダイレクト（ログイン成功）またはダッシュボードを確認
        self.assertIn(response.status_code, [200, 302])

    def test_dashboard_requires_login(self):
        """ダッシュボードが認証を要求することのテスト"""
        response = self.client.get('/accounts/dashboard/')
        # 未認証ではリダイレクト
        self.assertEqual(response.status_code, 302)

    def test_authenticated_dashboard_access(self):
        """認証済みダッシュボードアクセステスト"""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ダッシュボード')

    def test_logout_functionality(self):
        """ログアウト機能のテスト"""
        self.client.force_login(self.user)
        response = self.client.post('/auth/logout/')
        self.assertEqual(response.status_code, 302)  # リダイレクト


class GroupTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123',
            nickname='user1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123',
            nickname='user2'
        )

    def test_group_creation(self):
        """グループ作成のテスト"""
        group = CustomGroup.objects.create(
            name='Test Group',
            description='Test Description',
            created_by=self.user1
        )
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.created_by, self.user1)

    def test_group_membership(self):
        """グループメンバーシップのテスト"""
        group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        group.members.add(self.user1, self.user2)
        
        self.assertIn(self.user1, group.members.all())
        self.assertIn(self.user2, group.members.all())
        self.assertEqual(group.members.count(), 2)


class APIAuthenticationTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123',
            nickname='apiuser'
        )

    def test_unauthenticated_api_access(self):
        """未認証APIアクセスのテスト"""
        response = self.client.get('/api/schedules/sessions/view/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_api_access(self):
        """認証済みAPIアクセスのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # レスポンス構造の確認
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertIn('limit', data)
        self.assertIn('offset', data)

    def test_scenarios_api_access(self):
        """シナリオAPIアクセスのテスト"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/scenarios/history/?limit=5')
        # 200または404（データがない場合）を期待
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])