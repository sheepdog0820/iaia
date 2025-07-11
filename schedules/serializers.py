from rest_framework import serializers
from .models import TRPGSession, SessionParticipant, HandoutInfo, HandoutNotification, UserNotificationPreferences, SessionImage, SessionYouTubeLink
from accounts.serializers import UserSerializer
from accounts.models import CustomUser


class SessionImageSerializer(serializers.ModelSerializer):
    """セッション画像シリアライザー"""
    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionImage
        fields = ['id', 'image', 'image_url', 'title', 'description', 
                 'order', 'uploaded_by', 'uploaded_by_detail', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class SessionYouTubeLinkSerializer(serializers.ModelSerializer):
    """セッションYouTube動画リンクシリアライザー"""
    added_by_detail = UserSerializer(source='added_by', read_only=True)
    
    class Meta:
        model = SessionYouTubeLink
        fields = ['id', 'youtube_url', 'video_id', 'title', 'duration_seconds',
                 'duration_display', 'channel_name', 'thumbnail_url', 'description',
                 'order', 'added_by', 'added_by_detail', 'created_at', 'updated_at']
        read_only_fields = ['id', 'video_id', 'title', 'duration_seconds', 
                           'channel_name', 'thumbnail_url', 'added_by', 
                           'created_at', 'updated_at']


class SessionParticipantSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    character_sheet_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionParticipant
        fields = ['id', 'session', 'user', 'user_detail', 'role', 
                 'character_name', 'character_sheet_url', 'player_slot',
                 'character_sheet', 'character_sheet_detail']
        read_only_fields = ['id']
    
    def get_character_sheet_detail(self, obj):
        if obj.character_sheet:
            return {
                'id': obj.character_sheet.id,
                'name': obj.character_sheet.name,
                'occupation': obj.character_sheet.occupation,
                'age': obj.character_sheet.age,
                'hp_current': obj.character_sheet.hp_current,
                'mp_current': obj.character_sheet.mp_current,
                'san_current': obj.character_sheet.san_current,
                'hit_points_current': obj.character_sheet.hit_points_current,
                'magic_points_current': obj.character_sheet.magic_points_current,
                'sanity_current': obj.character_sheet.sanity_current
            }
        return None


class HandoutInfoSerializer(serializers.ModelSerializer):
    participant_detail = SessionParticipantSerializer(source='participant', read_only=True)
    
    class Meta:
        model = HandoutInfo
        fields = ['id', 'session', 'participant', 'participant_detail', 
                 'title', 'content', 'is_secret', 'handout_number',
                 'assigned_player_slot', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TRPGSessionSerializer(serializers.ModelSerializer):
    gm_detail = UserSerializer(source='gm', read_only=True)
    participants_detail = SessionParticipantSerializer(
        source='sessionparticipant_set', 
        many=True, 
        read_only=True
    )
    handouts_detail = HandoutInfoSerializer(
        source='handouts', 
        many=True, 
        read_only=True
    )
    images_detail = SessionImageSerializer(
        source='images',
        many=True,
        read_only=True
    )
    youtube_links_detail = SessionYouTubeLinkSerializer(
        source='youtube_links',
        many=True,
        read_only=True
    )
    participant_count = serializers.SerializerMethodField()
    youtube_total_duration = serializers.IntegerField(read_only=True)
    youtube_total_duration_display = serializers.CharField(read_only=True)
    youtube_video_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TRPGSession
        fields = ['id', 'title', 'description', 'date', 'location', 
                 'youtube_url', 'status', 'visibility', 'gm', 'gm_detail',
                 'group', 'duration_minutes', 'participants_detail', 
                 'handouts_detail', 'images_detail', 'youtube_links_detail',
                 'participant_count', 'youtube_total_duration', 
                 'youtube_total_duration_display', 'youtube_video_count',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'gm', 'created_at', 'updated_at']
    
    def get_participant_count(self, obj):
        return obj.participants.count()


class CalendarEventSerializer(serializers.ModelSerializer):
    """カレンダー表示用の軽量シリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    
    class Meta:
        model = TRPGSession
        fields = ['id', 'title', 'date', 'status', 'gm_name', 'location']


class SessionListSerializer(serializers.ModelSerializer):
    """セッション一覧表示用の見やすいシリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    date_formatted = serializers.SerializerMethodField()
    youtube_total_duration_display = serializers.CharField(read_only=True)
    youtube_video_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TRPGSession
        fields = [
            'id', 'title', 'description', 'date', 'date_formatted',
            'location', 'status', 'status_display', 'visibility', 'visibility_display',
            'gm_name', 'group_name', 'participant_count', 'duration_minutes',
            'youtube_url', 'youtube_total_duration_display', 'youtube_video_count'
        ]
    
    def get_participant_count(self, obj):
        return obj.participants.count()
    
    def get_date_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%Y年%m月%d日 %H:%M')
        return None


class UpcomingSessionSerializer(serializers.ModelSerializer):
    """ホーム画面の次回セッション表示用シリアライザー"""
    gm_name = serializers.CharField(source='gm.nickname', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    date_formatted = serializers.SerializerMethodField()
    time_formatted = serializers.SerializerMethodField()
    date_display = serializers.SerializerMethodField()
    participants_summary = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TRPGSession
        fields = [
            'id', 'title', 'description', 'date', 'date_formatted', 'time_formatted', 'date_display',
            'location', 'status', 'gm_name', 'group_name', 'participant_count',
            'participants_summary', 'duration_minutes', 'duration_display'
        ]
    
    def get_participant_count(self, obj):
        return obj.participants.count()
    
    def get_date_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%Y年%m月%d日')
        return None
    
    def get_time_formatted(self, obj):
        if obj.date:
            return obj.date.strftime('%H:%M')
        return None
    
    def get_date_display(self, obj):
        if obj.date:
            from datetime import datetime, timedelta
            now = datetime.now()
            session_date = obj.date.replace(tzinfo=None) if obj.date.tzinfo else obj.date
            
            # 今日の場合
            if session_date.date() == now.date():
                return f"今日 {obj.date.strftime('%H:%M')}"
            
            # 明日の場合
            elif session_date.date() == (now + timedelta(days=1)).date():
                return f"明日 {obj.date.strftime('%H:%M')}"
            
            # 今週内の場合
            elif session_date.date() <= (now + timedelta(days=7)).date():
                weekdays = ['月', '火', '水', '木', '金', '土', '日']
                weekday = weekdays[session_date.weekday()]
                return f"{session_date.strftime('%m/%d')}({weekday}) {obj.date.strftime('%H:%M')}"
            
            # それ以外
            else:
                return obj.date.strftime('%Y年%m月%d日 %H:%M')
        return None
    
    def get_participants_summary(self, obj):
        """参加者の簡易表示"""
        participants = obj.sessionparticipant_set.select_related('user').all()
        
        if not participants:
            return "参加者なし"
        
        # GMを除く参加者
        players = [p for p in participants if p.user != obj.gm]
        
        if len(players) == 0:
            return "GM のみ"
        elif len(players) <= 3:
            # 3人以下なら全員表示
            names = [p.user.nickname or p.user.username for p in players]
            return ", ".join(names)
        else:
            # 4人以上なら最初の2人 + 他○人
            names = [p.user.nickname or p.user.username for p in players[:2]]
            remaining = len(players) - 2
            return f"{', '.join(names)} 他{remaining}人"
    
    def get_duration_display(self, obj):
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            if hours > 0 and minutes > 0:
                return f"{hours}時間{minutes}分"
            elif hours > 0:
                return f"{hours}時間"
            else:
                return f"{minutes}分"
        return None


# ===== ハンドアウト通知関連シリアライザー =====

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
            'message', 'is_read', 'created_at', 'read_at',
            'handout_info', 'time_since_created'
        ]
        read_only_fields = [
            'id', 'handout_id', 'recipient', 'sender',
            'notification_type', 'message', 'created_at'
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
            'email_notifications_enabled', 'browser_notifications_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate(self, data):
        """通知設定のバリデーション"""
        # 少なくとも一つの通知方法は有効にする必要がある
        if not any([
            data.get('handout_notifications_enabled', False),
            data.get('email_notifications_enabled', False),
            data.get('browser_notifications_enabled', False)
        ]):
            raise serializers.ValidationError(
                "少なくとも一つの通知方法を有効にしてください"
            )
        
        return data