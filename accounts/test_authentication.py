from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.conf import settings
from allauth.account.models import EmailAddress
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser
from accounts.models import Group as CustomGroup, PremiumSubscription

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

    def test_password_reset_page_accessible(self):
        url = reverse('account_reset_password')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')

    def test_email_password_login(self):
        """メールアドレス＋パスワードでログインできることのテスト"""
        response = self.client.post('/accounts/login/', data={
            'username': self.user.email,
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/dashboard/', response['Location'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.test',
    )
    def test_password_reset_sends_reset_email(self):
        url = reverse('account_reset_password')

        response = self.client.post(url, data={'email': self.user.email})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        reset_email = mail.outbox[0]
        self.assertEqual(reset_email.to, [self.user.email])
        self.assertEqual(reset_email.from_email, 'noreply@example.test')
        self.assertIn('/accounts/password/reset/key/', reset_email.body)

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION='mandatory',
        ACCOUNT_PREVENT_ENUMERATION=True,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_password_reset_does_not_email_unverified_user_when_verification_is_mandatory(self):
        EmailAddress.objects.update_or_create(
            user=self.user,
            email=self.user.email,
            defaults={'primary': True, 'verified': False},
        )

        response = self.client.post(reverse('account_reset_password'), data={'email': self.user.email})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox, [])

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION='mandatory',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.test',
    )
    def test_password_reset_emails_verified_user_when_verification_is_mandatory(self):
        EmailAddress.objects.update_or_create(
            user=self.user,
            email=self.user.email,
            defaults={'primary': True, 'verified': True},
        )

        response = self.client.post(reverse('account_reset_password'), data={'email': self.user.email})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
    def test_unverified_email_cannot_login_when_verification_is_mandatory(self):
        EmailAddress.objects.update_or_create(
            user=self.user,
            email=self.user.email,
            defaults={'primary': True, 'verified': False},
        )

        response = self.client.post('/accounts/login/', data={
            'username': self.user.email,
            'password': 'testpass123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Email verification is required before login.')

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
    def test_user_without_verified_email_record_cannot_login_when_verification_is_mandatory(self):
        EmailAddress.objects.filter(user=self.user).delete()

        response = self.client.post('/accounts/login/', data={
            'username': self.user.email,
            'password': 'testpass123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Email verification is required before login.')

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
    def test_verified_email_can_login_when_verification_is_mandatory(self):
        EmailAddress.objects.update_or_create(
            user=self.user,
            email=self.user.email,
            defaults={'primary': True, 'verified': True},
        )

        response = self.client.post('/accounts/login/', data={
            'username': self.user.email,
            'password': 'testpass123',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/dashboard/', response['Location'])

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION='mandatory',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_signup_sends_verification_email_and_does_not_login(self):
        response = self.client.post('/accounts/signup/', data={
            'username': 'needsverify',
            'email': 'needsverify@example.com',
            'nickname': 'Needs Verify',
            'password1': 'verification-pass-123',
            'password2': 'verification-pass-123',
            'trpg_history': '',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('account_email_verification_sent'))
        created_user = User.objects.get(username='needsverify')
        email_address = EmailAddress.objects.get(user=created_user, email='needsverify@example.com')
        self.assertFalse(email_address.verified)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(DEBUG=True)
    def test_demo_login_page_accessible(self):
        """デモログインページのアクセステスト"""
        response = self.client.get('/accounts/demo/')
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=True)
    def test_mock_social_login_google(self):
        """Googleモックソーシャルログインのテスト"""
        response = self.client.get('/accounts/mock-social/google/')
        # リダイレクト（ログイン成功）またはダッシュボードを確認
        self.assertIn(response.status_code, [200, 302])

    @override_settings(DEBUG=True)
    def test_mock_social_login_twitter(self):
        """Twitterモックソーシャルログインのテスト"""
        response = self.client.get('/accounts/mock-social/twitter_oauth2/')
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
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 302)  # リダイレクト

    def test_account_delete_requires_login(self):
        """アカウント削除ページが認証を要求することのテスト"""
        response = self.client.get('/accounts/profile/delete/')
        self.assertEqual(response.status_code, 302)

    def test_account_delete_page_warns_when_active_stripe_subscription_exists(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id='cus_delete_guard',
            stripe_subscription_id='sub_delete_guard',
            subscription_status='active',
            access_source='stripe',
        )
        self.client.force_login(self.user)

        response = self.client.get('/accounts/profile/delete/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '課金中のアカウントです。')
        self.assertContains(response, '課金管理へ')

    def test_account_delete_blocks_active_stripe_subscription(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id='cus_delete_guard',
            stripe_subscription_id='sub_delete_guard',
            subscription_status='active',
            access_source='stripe',
        )
        self.client.force_login(self.user)

        response = self.client.post('/accounts/profile/delete/', data={
            'confirm': 'DELETE',
            'password': 'testpass123',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('billing'))
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_account_delete_allows_canceled_stripe_subscription(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id='cus_delete_guard',
            stripe_subscription_id='sub_delete_guard',
            subscription_status='canceled',
            access_source='stripe',
        )
        self.client.force_login(self.user)

        response = self.client.post('/accounts/profile/delete/', data={
            'confirm': 'DELETE',
            'password': 'testpass123',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

    def test_account_delete_with_password(self):
        """パスワード確認ありでアカウント削除できることのテスト"""
        self.client.force_login(self.user)
        response = self.client.post('/accounts/profile/delete/', data={
            'confirm': 'DELETE',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())


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
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

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
