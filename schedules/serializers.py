from rest_framework import serializers
from .models import (
    TRPGSession,
    SessionParticipant,
    SessionInvitation,
    SessionNote,
    SessionLog,
    HandoutInfo,
    HandoutAttachment,
    HandoutNotification,
    UserNotificationPreferences,
    SessionImage,
    SessionYouTubeLink,
)
from accounts.serializers import UserSerializer
from accounts.models import CustomUser, Group
from scenarios.models import Scenario
from django.utils import timezone
from datetime import datetime, time as time_cls


class NullableIntegerField(serializers.IntegerField):
    """空文字をnullとして扱えるIntegerField（フォーム送信対策）"""

    def to_internal_value(self, data):
        if data == '':
            data = None
        return super().to_internal_value(data)


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
    part_number = NullableIntegerField(min_value=1, required=False, allow_null=True)
    
    class Meta:
        model = SessionYouTubeLink
        fields = ['id', 'youtube_url', 'video_id', 'title', 'duration_seconds',
                 'duration_display', 'channel_name', 'thumbnail_url', 'description',
                 'perspective', 'part_number', 'order', 'added_by', 'added_by_detail',
                 'created_at', 'updated_at']
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


class SessionNoteSerializer(serializers.ModelSerializer):
    author_detail = UserSerializer(source='author', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)

    class Meta:
        model = SessionNote
        fields = [
            'id',
            'session',
            'session_title',
            'author',
            'author_detail',
            'note_type',
            'title',
            'content',
            'is_pinned',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'session',
            'session_title',
            'author',
            'author_detail',
            'created_at',
            'updated_at'
        ]


class SessionLogSerializer(serializers.ModelSerializer):
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    related_character_name = serializers.CharField(
        source='related_character.name',
        read_only=True
    )

    class Meta:
        model = SessionLog
        fields = [
            'id',
            'session',
            'session_title',
            'created_by',
            'created_by_detail',
            'timestamp',
            'event_type',
            'description',
            'related_character',
            'related_character_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'session',
            'session_title',
            'created_by',
            'created_by_detail',
            'related_character_name',
            'created_at',
            'updated_at'
        ]


class HandoutInfoSerializer(serializers.ModelSerializer):
    participant = serializers.PrimaryKeyRelatedField(
        queryset=SessionParticipant.objects.all(),
        required=False,
        allow_null=True
    )
    participant_detail = SessionParticipantSerializer(source='participant', read_only=True)
    recipient = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = HandoutInfo
        fields = ['id', 'session', 'participant', 'participant_detail', 
                 'title', 'content', 'recommended_skills', 'is_secret', 'handout_number',
                 'assigned_player_slot', 'created_at', 'updated_at', 'recipient']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        recipient = attrs.pop('recipient', None)
        participant = attrs.get('participant')
        session = attrs.get('session')

        if recipient and not participant:
            if not session:
                raise serializers.ValidationError({'session': 'session is required when using recipient'})
            participant = SessionParticipant.objects.filter(
                session=session,
                user=recipient
            ).first()
            if not participant:
                raise serializers.ValidationError({'recipient': 'Recipient is not a participant in this session'})
            attrs['participant'] = participant

        if not attrs.get('participant') and not getattr(self.instance, 'participant', None):
            raise serializers.ValidationError({'participant': 'participant or recipient is required'})

        return attrs


class HandoutAttachmentSerializer(serializers.ModelSerializer):
    """ハンドアウト添付ファイルシリアライザー"""

    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = HandoutAttachment
        fields = [
            'id',
            'handout',
            'file',
            'file_url',
            'original_filename',
            'file_type',
            'file_size',
            'content_type',
            'description',
            'uploaded_by',
            'uploaded_by_detail',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'handout',
            'file_url',
            'original_filename',
            'file_type',
            'file_size',
            'content_type',
            'uploaded_by',
            'uploaded_by_detail',
            'created_at',
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class TRPGSessionSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(required=False)
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        required=False,
        allow_null=True
    )
    session_date = serializers.DateField(write_only=True, required=False)
    start_time = serializers.TimeField(write_only=True, required=False)
    estimated_hours = serializers.FloatField(write_only=True, required=False)
    min_players = serializers.IntegerField(write_only=True, required=False)
    max_players = serializers.IntegerField(write_only=True, required=False)
    gm_detail = UserSerializer(source='gm', read_only=True)
    scenario = serializers.PrimaryKeyRelatedField(
        queryset=Scenario.objects.all(),
        required=False,
        allow_null=True
    )
    scenario_detail = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
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
                 'group', 'scenario', 'scenario_detail', 'duration_minutes', 'participants', 'participants_detail', 
                 'handouts_detail', 'images_detail', 'youtube_links_detail',
                 'participant_count', 'youtube_total_duration', 
                 'youtube_total_duration_display', 'youtube_video_count',
                 'created_at', 'updated_at', 'session_date', 'start_time',
                 'estimated_hours', 'min_players', 'max_players']
        read_only_fields = ['id', 'gm', 'created_at', 'updated_at']
    
    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_scenario_detail(self, obj):
        if not obj.scenario:
            return None
        return {
            'id': obj.scenario.id,
            'title': obj.scenario.title,
            'game_system': obj.scenario.game_system,
            'recommended_skills': obj.scenario.recommended_skills,
        }

    def get_participants(self, obj):
        participants = SessionParticipantSerializer(
            obj.sessionparticipant_set.all(),
            many=True
        ).data
        for participant in participants:
            detail = participant.get('character_sheet_detail')
            if detail:
                participant['character_sheet'] = detail
        return participants

    def validate(self, attrs):
        session_date = attrs.pop('session_date', None)
        start_time = attrs.pop('start_time', None)
        estimated_hours = attrs.pop('estimated_hours', None)
        attrs.pop('min_players', None)
        attrs.pop('max_players', None)

        if session_date and 'date' not in attrs:
            if not start_time:
                start_time = time_cls(0, 0)
            session_dt = datetime.combine(session_date, start_time)
            if timezone.is_naive(session_dt):
                session_dt = timezone.make_aware(session_dt, timezone.get_current_timezone())
            attrs['date'] = session_dt

        if estimated_hours is not None and 'duration_minutes' not in attrs:
            attrs['duration_minutes'] = int(float(estimated_hours) * 60)

        if self.instance is None and 'date' not in attrs:
            raise serializers.ValidationError({'date': 'date or session_date is required'})

        return attrs


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


class SessionInvitationSerializer(serializers.ModelSerializer):
    """セッション招待シリアライザー（一覧表示＋受諾/辞退導線用）"""

    inviter = UserBasicSerializer(read_only=True)
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    session_date = serializers.DateTimeField(source='session.date', read_only=True)
    session_visibility = serializers.CharField(source='session.visibility', read_only=True)
    session_group = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = SessionInvitation
        fields = [
            'id',
            'session_id',
            'session_title',
            'session_date',
            'session_visibility',
            'session_group',
            'inviter',
            'status',
            'message',
            'created_at',
            'responded_at',
            'expires_at',
            'is_expired',
        ]
        read_only_fields = fields

    def get_session_group(self, obj):
        group = getattr(obj.session, 'group', None)
        if not group:
            return None
        return {'id': group.id, 'name': group.name}

    def get_expires_at(self, obj):
        return obj.expires_at.isoformat() if obj.expires_at else None

    def get_is_expired(self, obj):
        return obj.is_expired
