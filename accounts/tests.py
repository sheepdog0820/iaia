from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from .models import CustomUser, Group, GroupMembership

User = get_user_model()


class BasicAccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='basicuser',
            email='basic@example.com',
            password='basicpass123',
            nickname='Basic User'
        )

    def test_custom_user_model(self):
        """カスタムユーザーモデルのテスト"""
        self.assertIsInstance(self.user, CustomUser)
        self.assertEqual(self.user.email, 'basic@example.com')
        self.assertEqual(self.user.nickname, 'Basic User')

    def test_user_str_representation(self):
        """ユーザー文字列表現のテスト"""
        self.assertEqual(str(self.user), 'Basic User')

    def test_login_view(self):
        """ログインビューのテスト"""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_signup_view(self):
        """サインアップビューのテスト"""
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_unauthenticated(self):
        """未認証ダッシュボードビューのテスト"""
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_authenticated(self):
        """認証済みダッシュボードビューのテスト"""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)


class GroupBasicTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='groupowner',
            email='owner@example.com',
            password='pass123',
            nickname='Group Owner'
        )

    def test_group_creation(self):
        """グループ作成のテスト"""
        group = Group.objects.create(
            name='Test Group',
            description='Test Description',
            created_by=self.user
        )
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.created_by, self.user)

    def test_group_str_representation(self):
        """グループ文字列表現のテスト"""
        group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        self.assertEqual(str(group), 'Test Group')

    def test_group_membership_creation(self):
        """グループメンバーシップ作成のテスト"""
        group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        membership = GroupMembership.objects.create(
            user=self.user,
            group=group,
            role='admin'
        )
        self.assertEqual(membership.role, 'admin')
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.group, group)
