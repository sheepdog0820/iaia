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
            
            subject = f"[タブレノ] {notification.get_notification_type_display()}"
            message = notification.message
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tableno.jp')
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


class SessionNotificationService(HandoutNotificationService):
    """セッション関連通知サービスクラス（ISSUE-013実装）"""
    
    def send_session_invitation_notification(self, session, inviter, invitee, invitation_id=None):
        """
        セッション招待通知を送信
        
        Args:
            session (TRPGSession): 招待対象のセッション
            inviter (CustomUser): 招待者
            invitee (CustomUser): 被招待者
            
        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            # 通知設定を確認
            preferences = UserNotificationPreferences.get_or_create_for_user(invitee)
            if not preferences.session_notifications_enabled:
                logger.info(f"通知設定により送信をスキップ: user={invitee.id}")
                return False
            
            # 通知メッセージ作成
            message = self._create_session_invitation_message(session, inviter)
            
            # 通知レコード作成
            notification = HandoutNotification.objects.create(
                handout_id=0,  # セッション通知なのでhandout_idは0
                recipient=invitee,
                sender=inviter,
                notification_type='session_invitation',
                message=message,
                is_read=False
            )
            
            # metadataは後から設定
            if hasattr(notification, 'metadata'):
                notification.metadata = {
                    'session_invitation_id': invitation_id,
                    'session_id': session.id,
                    'session_title': session.title,
                    'session_date': session.date.isoformat() if session.date else None,
                    'inviter_name': inviter.nickname or inviter.username
                }
                notification.save()
            
            # メール通知（設定が有効な場合）
            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)
            
            logger.info(f"セッション招待通知送信完了: session={session.id}, invitee={invitee.id}")
            return True
            
        except Exception as e:
            logger.error(f"セッション招待通知送信エラー: {e}")
            return False
    
    def send_session_schedule_change_notification(self, session, old_date, new_date):
        """
        セッションスケジュール変更通知を送信
        
        Args:
            session (TRPGSession): 変更されたセッション
            old_date (datetime): 変更前の日時
            new_date (datetime): 変更後の日時
            
        Returns:
            int: 送信した通知数
        """
        try:
            # セッション参加者全員に通知（GM除く）
            participants = session.participants.exclude(id=session.gm.id).all()
            notification_count = 0
            
            for participant in participants:
                # 通知設定を確認
                preferences = UserNotificationPreferences.get_or_create_for_user(participant)
                if not preferences.session_notifications_enabled:
                    continue
                
                # 通知メッセージ作成
                message = self._create_schedule_change_message(session, old_date, new_date)
                
                # 通知レコード作成
                notification = HandoutNotification.objects.create(
                    handout_id=0,  # セッション通知なのでhandout_idは0
                    recipient=participant,
                    sender=session.gm,
                    notification_type='schedule_change',
                    message=message,
                    is_read=False
                )
                
                # metadataは後から設定
                if hasattr(notification, 'metadata'):
                    notification.metadata = {
                        'session_id': session.id,
                        'session_title': session.title,
                        'old_date': old_date.isoformat() if old_date else None,
                        'new_date': new_date.isoformat() if new_date else None,
                        'gm_name': session.gm.nickname or session.gm.username
                    }
                    notification.save()
                
                # メール通知（設定が有効な場合）
                if preferences.email_notifications_enabled:
                    self._send_email_notification(notification)
                
                notification_count += 1
            
            logger.info(f"スケジュール変更通知送信完了: session={session.id}, 通知数={notification_count}")
            return notification_count
            
        except Exception as e:
            logger.error(f"スケジュール変更通知送信エラー: {e}")
            return 0
    
    def send_session_cancelled_notification(self, session, reason=None):
        """
        セッションキャンセル通知を送信
        
        Args:
            session (TRPGSession): キャンセルされたセッション
            reason (str): キャンセル理由（オプション）
            
        Returns:
            int: 送信した通知数
        """
        try:
            # セッション参加者全員に通知（GM除く）
            participants = session.participants.exclude(id=session.gm.id).all()
            notification_count = 0
            
            for participant in participants:
                # 通知設定を確認
                preferences = UserNotificationPreferences.get_or_create_for_user(participant)
                if not preferences.session_notifications_enabled:
                    continue
                
                # 通知メッセージ作成
                message = self._create_session_cancelled_message(session, reason)
                
                # 通知レコード作成
                notification = HandoutNotification.objects.create(
                    handout_id=0,  # セッション通知なのでhandout_idは0
                    recipient=participant,
                    sender=session.gm,
                    notification_type='session_cancelled',
                    message=message,
                    is_read=False,
                    metadata={
                        'session_id': session.id,
                        'session_title': session.title,
                        'session_date': session.date.isoformat() if session.date else None,
                        'gm_name': session.gm.nickname or session.gm.username,
                        'cancel_reason': reason or ''
                    }
                )
                
                # メール通知（設定が有効な場合）
                if preferences.email_notifications_enabled:
                    self._send_email_notification(notification)
                
                notification_count += 1
            
            logger.info(f"セッションキャンセル通知送信完了: session={session.id}, 通知数={notification_count}")
            return notification_count
            
        except Exception as e:
            logger.error(f"セッションキャンセル通知送信エラー: {e}")
            return 0
    
    def send_session_reminder_notification(self, session, hours_before=24):
        """
        セッションリマインダー通知を送信
        
        Args:
            session (TRPGSession): 対象セッション
            hours_before (int): 何時間前の通知か
            
        Returns:
            int: 送信した通知数
        """
        try:
            # セッション参加者全員に通知（GM含む）
            participants = list(session.participants.all())
            if session.gm not in participants:
                participants.append(session.gm)
            
            notification_count = 0
            
            for participant in participants:
                # 通知設定を確認
                preferences = UserNotificationPreferences.get_or_create_for_user(participant)
                if not preferences.session_notifications_enabled:
                    continue
                
                # 通知メッセージ作成
                message = self._create_session_reminder_message(session, hours_before)
                
                # 通知レコード作成
                notification = HandoutNotification.objects.create(
                    handout_id=0,  # セッション通知なのでhandout_idは0
                    recipient=participant,
                    sender=session.gm,
                    notification_type='session_reminder',
                    message=message,
                    is_read=False,
                    metadata={
                        'session_id': session.id,
                        'session_title': session.title,
                        'session_date': session.date.isoformat() if session.date else None,
                        'hours_before': hours_before,
                        'gm_name': session.gm.nickname or session.gm.username
                    }
                )
                
                # メール通知（設定が有効な場合）
                if preferences.email_notifications_enabled:
                    self._send_email_notification(notification)
                
                notification_count += 1
            
            logger.info(f"セッションリマインダー通知送信完了: session={session.id}, 通知数={notification_count}")
            return notification_count
            
        except Exception as e:
            logger.error(f"セッションリマインダー通知送信エラー: {e}")
            return 0
    
    def _create_session_invitation_message(self, session, inviter):
        """セッション招待通知メッセージの作成"""
        date_label = session.date.strftime('%Y年%m月%d日 %H:%M') if session.date else '未定'
        return (
            f"【セッション招待】\n"
            f"{inviter.nickname or inviter.username}さんからセッションに招待されました。\n\n"
            f"セッション: {session.title}\n"
            f"日時: {date_label}\n"
            f"GM: {session.gm.nickname or session.gm.username}\n"
            f"場所: {session.location or 'オンライン'}"
        )
    
    def _create_schedule_change_message(self, session, old_date, new_date):
        """スケジュール変更通知メッセージの作成"""
        old_label = old_date.strftime('%Y年%m月%d日 %H:%M') if old_date else '未定'
        new_label = new_date.strftime('%Y年%m月%d日 %H:%M') if new_date else '未定'
        return (
            f"【スケジュール変更】\n"
            f"セッション「{session.title}」の開催日時が変更されました。\n\n"
            f"変更前: {old_label}\n"
            f"変更後: {new_label}\n"
            f"GM: {session.gm.nickname or session.gm.username}"
        )
    
    def _create_session_cancelled_message(self, session, reason=None):
        """セッションキャンセル通知メッセージの作成"""
        date_label = session.date.strftime('%Y年%m月%d日 %H:%M') if session.date else '未定'
        message = (
            f"【セッションキャンセル】\n"
            f"セッション「{session.title}」がキャンセルされました。\n\n"
            f"予定日時: {date_label}\n"
            f"GM: {session.gm.nickname or session.gm.username}"
        )
        if reason:
            message += f"\n理由: {reason}"
        return message
    
    def _create_session_reminder_message(self, session, hours_before):
        """セッションリマインダー通知メッセージの作成"""
        date_label = session.date.strftime('%Y年%m月%d日 %H:%M') if session.date else '未定'
        return (
            f"【セッションリマインダー】\n"
            f"{hours_before}時間後にセッションが開催されます。\n\n"
            f"セッション: {session.title}\n"
            f"日時: {date_label}\n"
            f"GM: {session.gm.nickname or session.gm.username}\n"
            f"場所: {session.location or 'オンライン'}"
        )


class GroupNotificationService(HandoutNotificationService):
    """グループ招待などの通知サービス"""

    def send_group_invitation_notification(self, group, inviter, invitee, invitation_message: str = "") -> bool:
        """
        グループ招待通知を送信する

        Args:
            group (Group): 招待対象のグループ
            inviter (CustomUser): 招待を送ったユーザー
            invitee (CustomUser): 招待を受けるユーザー
            invitation_message (str): 招待メッセージ（任意）

        Returns:
            bool: 通知を送信した場合は True、それ以外は False
        """
        try:
            preferences = UserNotificationPreferences.get_or_create_for_user(invitee)
            if hasattr(preferences, "group_notifications_enabled") and not preferences.group_notifications_enabled:
                logger.info(f"グループ通知が無効のため送信しません: user={invitee.id}")
                return False

            message = self._create_group_invitation_message(group, inviter, invitation_message)

            notification = HandoutNotification.objects.create(
                handout_id=0,
                recipient=invitee,
                sender=inviter,
                notification_type="group_invitation",
                message=message,
                is_read=False,
                metadata={
                    "group_id": group.id,
                    "group_name": group.name,
                    "inviter_name": inviter.nickname or inviter.username,
                    "message": invitation_message or "",
                },
            )

            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)

            logger.info(f"グループ招待通知を送信しました: group={group.id}, invitee={invitee.id}")
            return True

        except Exception as e:
            logger.error(f"グループ招待通知の送信に失敗しました: {e}")
            return False

    def _create_group_invitation_message(self, group, inviter, invitation_message: str = "") -> str:
        """グループ招待通知メッセージを生成"""
        lines = [
            "【グループ招待】",
            f"{inviter.nickname or inviter.username}さんから招待が届いています。",
            f"グループ: {group.name}",
        ]
        if invitation_message:
            lines.append(f"メッセージ: {invitation_message}")
        return "\n".join(lines)


class FriendNotificationService(HandoutNotificationService):
    """フレンドリクエスト通知サービスクラス（ISSUE-013）"""

    def send_friend_request_notification(self, sender, recipient):
        """
        フレンドリクエスト送信通知

        Args:
            sender (CustomUser): リクエストを送った人
            recipient (CustomUser): リクエストを受け取る人

        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            # 通知設定を確認
            preferences = UserNotificationPreferences.get_or_create_for_user(recipient)
            if hasattr(preferences, 'friend_notifications_enabled') and not preferences.friend_notifications_enabled:
                logger.info(f"フレンド通知が無効のためスキップ: user={recipient.id}")
                return False

            # 通知メッセージ作成
            message = self._create_friend_request_message(sender)

            # 通知レコード作成
            notification = HandoutNotification.objects.create(
                handout_id=0,  # フレンド通知なのでhandout_idは0
                recipient=recipient,
                sender=sender,
                notification_type='friend_request',
                message=message,
                is_read=False,
                metadata={
                    'sender_id': sender.id,
                    'sender_name': sender.nickname or sender.username,
                }
            )

            # メール通知（設定が有効な場合）
            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)

            logger.info(f"フレンドリクエスト通知送信完了: sender={sender.id}, recipient={recipient.id}")
            return True

        except Exception as e:
            logger.error(f"フレンドリクエスト通知送信エラー: {e}")
            return False

    def send_friend_request_accepted_notification(self, accepter, original_sender):
        """
        フレンドリクエスト承認通知

        Args:
            accepter (CustomUser): リクエストを承認した人
            original_sender (CustomUser): リクエストを送った人（通知を受け取る人）

        Returns:
            bool: 通知送信成功時True、失敗時False
        """
        try:
            # 通知設定を確認
            preferences = UserNotificationPreferences.get_or_create_for_user(original_sender)
            if hasattr(preferences, 'friend_notifications_enabled') and not preferences.friend_notifications_enabled:
                logger.info(f"フレンド通知が無効のためスキップ: user={original_sender.id}")
                return False

            # 通知メッセージ作成
            message = self._create_friend_request_accepted_message(accepter)

            # 通知レコード作成
            notification = HandoutNotification.objects.create(
                handout_id=0,  # フレンド通知なのでhandout_idは0
                recipient=original_sender,
                sender=accepter,
                notification_type='friend_request_accepted',
                message=message,
                is_read=False,
                metadata={
                    'accepter_id': accepter.id,
                    'accepter_name': accepter.nickname or accepter.username,
                }
            )

            # メール通知（設定が有効な場合）
            if preferences.email_notifications_enabled:
                self._send_email_notification(notification)

            logger.info(f"フレンドリクエスト承認通知送信完了: accepter={accepter.id}, recipient={original_sender.id}")
            return True

        except Exception as e:
            logger.error(f"フレンドリクエスト承認通知送信エラー: {e}")
            return False

    def _create_friend_request_message(self, sender):
        """フレンドリクエスト通知メッセージの作成"""
        return (
            f"【フレンドリクエスト】\n"
            f"{sender.nickname or sender.username}さんからフレンドリクエストが届いています。"
        )

    def _create_friend_request_accepted_message(self, accepter):
        """フレンドリクエスト承認通知メッセージの作成"""
        return (
            f"【フレンドリクエスト承認】\n"
            f"{accepter.nickname or accepter.username}さんがフレンドリクエストを承認しました。\n"
            f"これでフレンドになりました！"
        )
