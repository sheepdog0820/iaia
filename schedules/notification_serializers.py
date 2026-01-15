"""
TRPGセッション管理システム - ハンドアウト通知シリアライザー

通知とユーザー設定のAPIシリアライゼーションを提供します。
"""

from rest_framework import serializers
from .models import HandoutNotification, UserNotificationPreferences, HandoutInfo
from accounts.models import CustomUser


class UserBasicSerializer(serializers.ModelSerializer):
    """ユーザー基本情報シリアライザー"""
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'nickname']


class HandoutBasicSerializer(serializers.ModelSerializer):
    """ハンドアウト基本情報シリアライザー"""
    session_title = serializers.CharField(source='session.title', read_only=True)
    
    class Meta:
        model = HandoutInfo
        fields = ['id', 'title', 'session_title', 'is_secret']


class HandoutNotificationSerializer(serializers.ModelSerializer):
    """ハンドアウト通知シリアライザー"""
    
    recipient = UserBasicSerializer(read_only=True)
    sender = UserBasicSerializer(read_only=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    handout_info = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()
    
    class Meta:
        model = HandoutNotification
        fields = [
            'id', 'handout_id', 'recipient', 'sender', 
            'notification_type', 'notification_type_display',
            'message', 'metadata', 'is_read', 'created_at', 'read_at',
            'handout_info', 'time_since_created'
        ]
        read_only_fields = [
            'id', 'handout_id', 'recipient', 'sender',
            'notification_type', 'message', 'metadata', 'created_at'
        ]
    
    def get_handout_info(self, obj):
        """ハンドアウト情報を取得"""
        try:
            handout = HandoutInfo.objects.get(id=obj.handout_id)
            return HandoutBasicSerializer(handout).data
        except HandoutInfo.DoesNotExist:
            return None
    
    def get_time_since_created(self, obj):
        """作成からの経過時間を人間が読みやすい形式で返す"""
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days}日前"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}時間前"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}分前"
        else:
            return "たった今"


class UserNotificationPreferencesSerializer(serializers.ModelSerializer):
    """ユーザー通知設定シリアライザー"""
    
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = UserNotificationPreferences
        fields = [
            'id', 'user', 'handout_notifications_enabled',
            'session_notifications_enabled', 'group_notifications_enabled',
            'friend_notifications_enabled',
            'email_notifications_enabled', 'browser_notifications_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate(self, data):
        """通知設定のバリデーション"""
        # 少なくとも一つの通知方法または通知種別を有効にする必要がある
        current = {
            'handout': data.get(
                'handout_notifications_enabled',
                getattr(self.instance, 'handout_notifications_enabled', False)
            ),
            'session': data.get(
                'session_notifications_enabled',
                getattr(self.instance, 'session_notifications_enabled', False)
            ),
            'group': data.get(
                'group_notifications_enabled',
                getattr(self.instance, 'group_notifications_enabled', False)
            ),
            'friend': data.get(
                'friend_notifications_enabled',
                getattr(self.instance, 'friend_notifications_enabled', False)
            ),
            'email': data.get(
                'email_notifications_enabled',
                getattr(self.instance, 'email_notifications_enabled', False)
            ),
            'browser': data.get(
                'browser_notifications_enabled',
                getattr(self.instance, 'browser_notifications_enabled', False)
            ),
        }

        if not any(current.values()):
            raise serializers.ValidationError(
                "少なくとも一つの通知方法を有効にしてください"
            )
        
        return data


class NotificationSummarySerializer(serializers.Serializer):
    """通知サマリーシリアライザー"""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    handout_created_count = serializers.IntegerField()
    handout_published_count = serializers.IntegerField()
    handout_updated_count = serializers.IntegerField()
    last_notification_date = serializers.DateTimeField(allow_null=True)
    
    def to_representation(self, instance):
        """通知サマリーデータの作成"""
        user = instance
        notifications = HandoutNotification.objects.filter(recipient=user)
        
        data = {
            'total_notifications': notifications.count(),
            'unread_notifications': notifications.filter(is_read=False).count(),
            'handout_created_count': notifications.filter(
                notification_type='handout_created'
            ).count(),
            'handout_published_count': notifications.filter(
                notification_type='handout_published'
            ).count(),
            'handout_updated_count': notifications.filter(
                notification_type='handout_updated'
            ).count(),
            'last_notification_date': notifications.first().created_at if notifications.exists() else None
        }
        
        return data


class BulkNotificationActionSerializer(serializers.Serializer):
    """一括通知操作シリアライザー"""
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="操作対象の通知IDリスト"
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete'],
        help_text="実行するアクション"
    )
    
    def validate_notification_ids(self, value):
        """通知IDの存在確認"""
        if len(value) > 100:
            raise serializers.ValidationError(
                "一度に操作できる通知は100件までです"
            )
        
        return value
