"""
TRPGセッション管理システム - ハンドアウト通知サービス

ハンドアウトの作成、公開、更新時の通知機能を提供します。
"""

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import HandoutNotification, UserNotificationPreferences
import logging

logger = logging.getLogger(__name__)


class HandoutNotificationService:
    """ハンドアウト通知サービスクラス"""
    
    def send_handout_created_notification(self, handout):
        """
        ハンドアウト作成通知を送信
        
        Args:
            handout (HandoutInfo): 作成されたハンドアウト
            
        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            recipient = handout.participant.user
            sender = handout.session.gm
            
            # 通知設定を確認
            preferences = UserNotificationPreferences.get_or_create_for_user(recipient)
            if not preferences.handout_notifications_enabled:
                logger.info(f"通知設定により送信をスキップ: user={recipient.id}")
                return False
            
            # 通知メッセージ作成
            message = self._create_handout_created_message(handout)
            
            # 通知レコード作成
            notification = HandoutNotification.objects.create(
                handout_id=handout.id,
                recipient=recipient,
                sender=sender,
                notification_type='handout_created',
                message=message,
                is_read=False
            )
            
            # メール通知（設定が有効な場合）
            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)
            
            logger.info(f"ハンドアウト作成通知送信完了: handout={handout.id}, recipient={recipient.id}")
            return True
            
        except Exception as e:
            logger.error(f"ハンドアウト作成通知送信エラー: {e}")
            return False
    
    def send_handout_published_notification(self, handout):
        """
        ハンドアウト公開通知を送信
        
        Args:
            handout (HandoutInfo): 公開されたハンドアウト
            
        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            # 公開ハンドアウトの場合、全参加者に通知
            if not handout.is_secret:
                recipients = handout.session.participants.exclude(id=handout.session.gm.id)
            else:
                # 秘匿ハンドアウトの場合、対象者のみに通知
                recipients = [handout.participant.user]
            
            sender = handout.session.gm
            notification_count = 0
            
            for recipient in recipients:
                # 通知設定を確認
                preferences = UserNotificationPreferences.get_or_create_for_user(recipient)
                if not preferences.handout_notifications_enabled:
                    continue
                
                # 通知メッセージ作成
                message = self._create_handout_published_message(handout)
                
                # 通知レコード作成
                notification = HandoutNotification.objects.create(
                    handout_id=handout.id,
                    recipient=recipient,
                    sender=sender,
                    notification_type='handout_published',
                    message=message,
                    is_read=False
                )
                
                # メール通知（設定が有効な場合）
                if preferences.email_notifications_enabled:
                    self._send_email_notification(notification)
                
                notification_count += 1
            
            logger.info(f"ハンドアウト公開通知送信完了: handout={handout.id}, 通知数={notification_count}")
            return notification_count > 0
            
        except Exception as e:
            logger.error(f"ハンドアウト公開通知送信エラー: {e}")
            return False
    
    def send_handout_updated_notification(self, handout):
        """
        ハンドアウト更新通知を送信
        
        Args:
            handout (HandoutInfo): 更新されたハンドアウト
            
        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            recipient = handout.participant.user
            sender = handout.session.gm
            
            # 通知設定を確認
            preferences = UserNotificationPreferences.get_or_create_for_user(recipient)
            if not preferences.handout_notifications_enabled:
                return False
            
            # 通知メッセージ作成
            message = self._create_handout_updated_message(handout)
            
            # 通知レコード作成
            notification = HandoutNotification.objects.create(
                handout_id=handout.id,
                recipient=recipient,
                sender=sender,
                notification_type='handout_updated',
                message=message,
                is_read=False
            )
            
            # メール通知（設定が有効な場合）
            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)
            
            logger.info(f"ハンドアウト更新通知送信完了: handout={handout.id}, recipient={recipient.id}")
            return True
            
        except Exception as e:
            logger.error(f"ハンドアウト更新通知送信エラー: {e}")
            return False
    
    def get_user_notifications(self, user, unread_only=False):
        """
        ユーザーの通知一覧を取得
        
        Args:
            user (CustomUser): 対象ユーザー
            unread_only (bool): 未読のみ取得するか
            
        Returns:
            QuerySet: 通知のQuerySet
        """
        notifications = HandoutNotification.objects.filter(recipient=user)
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        return notifications.order_by('-created_at')
    
    def mark_notification_as_read(self, notification_id, user):
        """
        通知を既読にマーク
        
        Args:
            notification_id (int): 通知ID
            user (CustomUser): ユーザー
            
        Returns:
            bool: 成功時True、失敗時False
        """
        try:
            notification = HandoutNotification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()
            return True
        except HandoutNotification.DoesNotExist:
            return False
    
    def _create_handout_created_message(self, handout):
        """ハンドアウト作成通知メッセージの作成"""
        return (
            f"【{handout.session.title}】\n"
            f"新しいハンドアウト「{handout.title}」が作成されました。\n"
            f"GM: {handout.session.gm.nickname}"
        )
    
    def _create_handout_published_message(self, handout):
        """ハンドアウト公開通知メッセージの作成"""
        return (
            f"【{handout.session.title}】\n"
            f"ハンドアウト「{handout.title}」が公開されました。\n"
            f"GM: {handout.session.gm.nickname}"
        )
    
    def _create_handout_updated_message(self, handout):
        """ハンドアウト更新通知メッセージの作成"""
        return (
            f"【{handout.session.title}】\n"
            f"ハンドアウト「{handout.title}」が更新されました。\n"
            f"GM: {handout.session.gm.nickname}"
        )
    
    def _send_email_notification(self, notification):
        """メール通知の送信"""
        try:
            if not hasattr(settings, 'EMAIL_BACKEND'):
                logger.warning("メール設定が見つかりません")
                return False
            
            subject = f"[Arkham Nexus] {notification.get_notification_type_display()}"
            message = notification.message
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@arkham-nexus.com')
            recipient_list = [notification.recipient.email]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False
            )
            
            logger.info(f"メール通知送信完了: recipient={notification.recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"メール通知送信エラー: {e}")
            return False