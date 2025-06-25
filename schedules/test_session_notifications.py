"""
セッション通知機能単体テスト（ISSUE-013）
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from schedules.models import (
    TRPGSession, SessionParticipant, HandoutNotification, 
    UserNotificationPreferences
)
from schedules.notifications import SessionNotificationService
import json


class SessionNotificationServiceTestCase(TestCase):
    """SessionNotificationServiceの単体テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='pass123',
            nickname='GMユーザー'
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass123',
            nickname='プレイヤー1'
        )
        self.player2 = CustomUser.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='pass123',
            nickname='プレイヤー2'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player1, self.player2)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            description='通知テスト用セッション',
            date=timezone.now() + timedelta(days=7),
            location='オンライン',
            gm=self.gm,
            group=self.group,
            status='planned',
            duration_minutes=180
        )
        
        # 参加者追加
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player'
        )
        
        # 通知サービス
        self.notification_service = SessionNotificationService()
    
    def test_send_session_invitation_notification(self):
        """セッション招待通知の送信テスト"""
        # 通知送信
        result = self.notification_service.send_session_invitation_notification(
            self.session, self.gm, self.player2
        )
        
        self.assertTrue(result)
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.player2,
            notification_type='session_invitation'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.sender, self.gm)
        self.assertIn('テストセッション', notification.message)
        self.assertIn('GMユーザー', notification.message)
        
        # メタデータ確認
        self.assertEqual(notification.metadata['session_id'], self.session.id)
        self.assertEqual(notification.metadata['session_title'], 'テストセッション')
    
    def test_send_session_invitation_notification_disabled(self):
        """通知無効時の招待通知テスト"""
        # 通知設定を無効化
        prefs = UserNotificationPreferences.get_or_create_for_user(self.player2)
        prefs.session_notifications_enabled = False
        prefs.save()
        
        # 通知送信
        result = self.notification_service.send_session_invitation_notification(
            self.session, self.gm, self.player2
        )
        
        self.assertFalse(result)
        
        # 通知が作成されていないことを確認
        count = HandoutNotification.objects.filter(
            recipient=self.player2,
            notification_type='session_invitation'
        ).count()
        self.assertEqual(count, 0)
    
    def test_send_session_schedule_change_notification(self):
        """スケジュール変更通知の送信テスト"""
        old_date = self.session.date
        new_date = self.session.date + timedelta(days=2)
        
        # 通知送信
        count = self.notification_service.send_session_schedule_change_notification(
            self.session, old_date, new_date
        )
        
        self.assertEqual(count, 1)  # player1のみ
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.player1,
            notification_type='schedule_change'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.sender, self.gm)
        self.assertIn('スケジュール変更', notification.message)
        self.assertIn('変更前:', notification.message)
        self.assertIn('変更後:', notification.message)
        
        # GMには通知されない
        gm_notifications = HandoutNotification.objects.filter(
            recipient=self.gm,
            notification_type='schedule_change'
        ).count()
        self.assertEqual(gm_notifications, 0)
    
    def test_send_session_cancelled_notification(self):
        """セッションキャンセル通知の送信テスト"""
        # 通知送信（理由あり）
        count = self.notification_service.send_session_cancelled_notification(
            self.session, reason='体調不良のため'
        )
        
        self.assertEqual(count, 1)
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.player1,
            notification_type='session_cancelled'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertIn('キャンセル', notification.message)
        self.assertIn('体調不良のため', notification.message)
        self.assertEqual(notification.metadata['cancel_reason'], '体調不良のため')
    
    def test_send_session_reminder_notification(self):
        """セッションリマインダー通知の送信テスト"""
        # GMも参加者として追加
        SessionParticipant.objects.create(
            session=self.session,
            user=self.gm,
            role='gm'
        )
        
        # 通知送信（24時間前）
        count = self.notification_service.send_session_reminder_notification(
            self.session, hours_before=24
        )
        
        self.assertEqual(count, 2)  # GMとplayer1
        
        # 通知確認
        notifications = HandoutNotification.objects.filter(
            notification_type='session_reminder'
        )
        
        self.assertEqual(notifications.count(), 2)
        
        for notification in notifications:
            self.assertIn('24時間後', notification.message)
            self.assertIn('リマインダー', notification.message)
            self.assertEqual(notification.metadata['hours_before'], 24)


class SessionInviteAPITestCase(APITestCase):
    """セッション招待APIのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='pass123'
        )
        self.player = CustomUser.objects.create_user(
            username='player',
            email='player@example.com',
            password='pass123'
        )
        self.non_member = CustomUser.objects.create_user(
            username='nonmember',
            email='non@example.com',
            password='pass123'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='Invite Test Session',
            date=timezone.now() + timedelta(days=3),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # GM認証
        self.client.force_authenticate(user=self.gm)
    
    def test_invite_success(self):
        """正常な招待送信"""
        url = reverse('session-invite', kwargs={'pk': self.session.pk})
        data = {'user_id': self.non_member.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.non_member,
            notification_type='session_invitation'
        ).first()
        self.assertIsNotNone(notification)
    
    def test_invite_non_gm_forbidden(self):
        """GM以外による招待の拒否"""
        self.client.force_authenticate(user=self.player)
        
        url = reverse('session-invite', kwargs={'pk': self.session.pk})
        data = {'user_id': self.non_member.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only GM can invite', response.data['error'])
    
    def test_invite_already_participant(self):
        """既に参加者の場合のエラー"""
        # playerを参加者として追加
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player'
        )
        
        url = reverse('session-invite', kwargs={'pk': self.session.pk})
        data = {'user_id': self.player.id}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already a participant', response.data['error'])
    
    def test_invite_invalid_user(self):
        """存在しないユーザーへの招待"""
        url = reverse('session-invite', kwargs={'pk': self.session.pk})
        data = {'user_id': 99999}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('User not found', response.data['error'])
    
    def test_invite_missing_user_id(self):
        """user_id未指定のエラー"""
        url = reverse('session-invite', kwargs={'pk': self.session.pk})
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id is required', response.data['error'])


class SessionUpdateNotificationTestCase(APITestCase):
    """セッション更新時の自動通知テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.gm = CustomUser.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='pass123'
        )
        self.player = CustomUser.objects.create_user(
            username='player',
            email='player@example.com',
            password='pass123'
        )
        
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm
        )
        self.group.members.add(self.gm, self.player)
        
        self.session = TRPGSession.objects.create(
            title='Update Test Session',
            date=timezone.now() + timedelta(days=5),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player'
        )
        
        self.client.force_authenticate(user=self.gm)
    
    def test_schedule_change_notification_on_update(self):
        """更新時のスケジュール変更通知"""
        url = reverse('session-detail', kwargs={'pk': self.session.pk})
        new_date = (timezone.now() + timedelta(days=7)).isoformat()
        
        data = {
            'title': self.session.title,
            'date': new_date,
            'group': self.group.id,
            'status': 'planned'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.player,
            notification_type='schedule_change'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertIn('スケジュール変更', notification.message)
    
    def test_cancellation_notification_on_status_change(self):
        """ステータス変更時のキャンセル通知"""
        url = reverse('session-detail', kwargs={'pk': self.session.pk})
        
        data = {
            'status': 'cancelled',
            'cancel_reason': '会場が確保できなかったため'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 通知確認
        notification = HandoutNotification.objects.filter(
            recipient=self.player,
            notification_type='session_cancelled'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertIn('キャンセル', notification.message)
        self.assertEqual(notification.metadata['cancel_reason'], '会場が確保できなかったため')
    
    def test_no_notification_on_minor_update(self):
        """日時以外の更新時は通知なし"""
        url = reverse('session-detail', kwargs={'pk': self.session.pk})
        
        data = {
            'description': '更新された説明文'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 通知が作成されていないことを確認
        notifications = HandoutNotification.objects.filter(
            recipient=self.player,
            notification_type__in=['schedule_change', 'session_cancelled']
        )
        
        self.assertEqual(notifications.count(), 0)