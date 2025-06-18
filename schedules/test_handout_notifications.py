"""
TRPGセッション管理システム - ハンドアウト配布通知機能のテスト

TDD原則に従って、ハンドアウト配布通知機能のテストを作成します。
この機能により、GMがハンドアウトを作成・公開した際に、
対象プレイヤーに自動で通知が送信されます。
"""

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from schedules.notifications import HandoutNotificationService
import unittest


class HandoutNotificationModelTest(TestCase):
    """ハンドアウト通知モデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        self.player2 = CustomUser.objects.create_user(
            username='player2',
            email='player2@example.com',
            nickname='プレイヤー2'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            description='テスト用のグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        self.group.members.add(self.gm_user, self.player1, self.player2)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            description='テスト用のセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        # 参加者作成
        self.gm_participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.gm_user,
            role='gm'
        )
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player',
            character_name='探索者1'
        )
        self.participant2 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player2,
            role='player',
            character_name='探索者2'
        )
    
    def test_handout_notification_model_creation(self):
        """HandoutNotificationモデルの作成テスト"""
        # このテストは失敗するはず（モデルがまだ存在しない）
        from schedules.models import HandoutNotification
        
        notification = HandoutNotification.objects.create(
            handout_id=1,
            recipient=self.player1,
            sender=self.gm_user,
            notification_type='handout_created',
            message='新しいハンドアウトが作成されました',
            is_read=False
        )
        
        self.assertEqual(notification.recipient, self.player1)
        self.assertEqual(notification.sender, self.gm_user)
        self.assertEqual(notification.notification_type, 'handout_created')
        self.assertFalse(notification.is_read)
    
    def test_handout_notification_validation(self):
        """HandoutNotificationのバリデーションテスト"""
        from schedules.models import HandoutNotification
        
        # 必須フィールドのテスト
        with self.assertRaises(ValidationError):
            notification = HandoutNotification(
                # handout_id なし（必須）
                recipient=self.player1,
                sender=self.gm_user,
                notification_type='handout_created'
            )
            notification.full_clean()
    
    def test_user_notification_preferences_model(self):
        """ユーザー通知設定モデルのテスト"""
        from schedules.models import UserNotificationPreferences
        
        preferences = UserNotificationPreferences.objects.create(
            user=self.player1,
            handout_notifications_enabled=True,
            email_notifications_enabled=False,
            browser_notifications_enabled=True
        )
        
        self.assertEqual(preferences.user, self.player1)
        self.assertTrue(preferences.handout_notifications_enabled)
        self.assertFalse(preferences.email_notifications_enabled)
        self.assertTrue(preferences.browser_notifications_enabled)


class HandoutNotificationServiceTest(TestCase):
    """ハンドアウト通知サービスのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        # 上記と同じセットアップ
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        
        self.group = Group.objects.create(
            name='テストグループ',
            description='テスト用のグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        self.group.members.add(self.gm_user, self.player1)
        
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            description='テスト用のセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
        
        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player'
        )
    
    def test_notification_service_exists(self):
        """通知サービスクラスの存在テスト"""
        # このテストは失敗するはず（サービスクラスがまだ存在しない）
        service = HandoutNotificationService()
        self.assertIsNotNone(service)
    
    def test_send_handout_created_notification(self):
        """ハンドアウト作成通知の送信テスト"""
        # ハンドアウト作成
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='テストハンドアウト',
            content='これはテスト用のハンドアウトです。',
            is_secret=True
        )
        
        # 通知サービスでの通知送信
        service = HandoutNotificationService()
        result = service.send_handout_created_notification(handout)
        
        # 通知が正常に送信されたことを確認
        self.assertTrue(result)
        
        # 通知レコードが作成されたことを確認
        from schedules.models import HandoutNotification
        notifications = HandoutNotification.objects.filter(
            handout_id=handout.id,
            recipient=self.player1
        )
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.first()
        self.assertEqual(notification.sender, self.gm_user)
        self.assertEqual(notification.notification_type, 'handout_created')
        self.assertFalse(notification.is_read)
    
    def test_send_handout_published_notification(self):
        """ハンドアウト公開通知の送信テスト"""
        # 秘匿ハンドアウト作成
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='秘匿ハンドアウト',
            content='これは秘匿ハンドアウトです。',
            is_secret=True
        )
        
        # 公開に変更
        handout.is_secret = False
        handout.save()
        
        # 公開通知の送信
        service = HandoutNotificationService()
        result = service.send_handout_published_notification(handout)
        
        self.assertTrue(result)
        
        # 公開通知レコードの確認
        from schedules.models import HandoutNotification
        notifications = HandoutNotification.objects.filter(
            handout_id=handout.id,
            notification_type='handout_published'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_notification_with_disabled_preferences(self):
        """通知設定無効時のテスト"""
        # ユーザーの通知設定を無効にする
        from schedules.models import UserNotificationPreferences
        UserNotificationPreferences.objects.create(
            user=self.player1,
            handout_notifications_enabled=False
        )
        
        # ハンドアウト作成
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant1,
            title='通知無効テスト',
            content='通知設定が無効なユーザーへのテスト',
            is_secret=False
        )
        
        # 通知送信試行
        service = HandoutNotificationService()
        result = service.send_handout_created_notification(handout)
        
        # 通知設定が無効なので、通知は送信されない
        self.assertFalse(result)
        
        # 通知レコードも作成されない
        from schedules.models import HandoutNotification
        notifications = HandoutNotification.objects.filter(
            handout_id=handout.id,
            recipient=self.player1
        )
        self.assertEqual(notifications.count(), 0)


class HandoutNotificationAPITest(TestCase):
    """ハンドアウト通知APIのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.gm_user = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            nickname='テストGM'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            nickname='プレイヤー1'
        )
        
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timezone.timedelta(days=1),
            gm=self.gm_user,
            group=self.group
        )
    
    def test_notification_list_api(self):
        """通知一覧APIのテスト"""
        # このテストは失敗するはず（APIエンドポイントがまだ存在しない）
        from django.test import Client
        
        client = Client()
        client.force_login(self.player1)
        
        response = client.get('/api/schedules/notifications/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)
    
    def test_mark_notification_as_read_api(self):
        """通知既読マークAPIのテスト"""
        from django.test import Client
        
        client = Client()
        client.force_login(self.player1)
        
        # 存在しない通知IDでのテスト（まだAPIが存在しないので404になるはず）
        response = client.patch('/api/schedules/notifications/1/mark_read/')
        self.assertEqual(response.status_code, 404)
    
    def test_notification_preferences_api(self):
        """通知設定APIのテスト"""
        from django.test import Client
        
        client = Client()
        client.force_login(self.player1)
        
        # 通知設定の取得
        response = client.get('/api/schedules/notification-preferences/')
        self.assertEqual(response.status_code, 200)
        
        # 通知設定の更新
        response = client.patch('/api/schedules/notification-preferences/', {
            'handout_notifications_enabled': False,
            'email_notifications_enabled': True
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)


@unittest.skip("Integration test - will be implemented after basic functionality")
class HandoutNotificationIntegrationTest(TestCase):
    """ハンドアウト通知機能の統合テスト"""
    
    def test_end_to_end_handout_notification_flow(self):
        """エンドツーエンドのハンドアウト通知フロー"""
        # この統合テストは基本機能実装後に実装する
        pass