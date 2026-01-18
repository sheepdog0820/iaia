from rest_framework import serializers
from .models import (
    TRPGSession,
    SessionOccurrence,
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
    # 高度なスケジューリング機能（ISSUE-017）
    SessionSeries,
    SessionAvailability,
    DatePoll,
    DatePollOption,
    DatePollVote,
    DatePollComment,
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
    date = serializers.DateTimeField(required=False, allow_null=True)
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

        return attrs


class SessionOccurrenceSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source='session.title', read_only=True)
    participants = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        many=True,
        required=False,
    )
    participants_detail = UserSerializer(source='participants', many=True, read_only=True)

    class Meta:
        model = SessionOccurrence
        fields = [
            'id',
            'session',
            'session_title',
            'start_at',
            'content',
            'is_primary',
            'participants',
            'participants_detail',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_primary',
            'created_at',
            'updated_at',
            'session_title',
        ]

    def validate(self, attrs):
        session = attrs.get('session') or getattr(self.instance, 'session', None)
        participants = attrs.get('participants')

        if session and participants is not None and getattr(session, 'group_id', None):
            allowed_ids = set(session.group.members.values_list('id', flat=True))
            if getattr(session, 'gm_id', None):
                allowed_ids.add(session.gm_id)

            invalid_ids = [user.id for user in participants if user.id not in allowed_ids]
            if invalid_ids:
                raise serializers.ValidationError(
                    {'participants': 'All participants must belong to the session group.'}
                )

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


# =====================================================
# 高度なスケジューリング機能（ISSUE-017）
# =====================================================


class SessionSeriesSerializer(serializers.ModelSerializer):
    """セッションシリーズ/キャンペーン シリアライザ"""

    gm_detail = UserSerializer(source='gm', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    recurrence_display = serializers.CharField(source='get_recurrence_display', read_only=True)
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)
    session_count = serializers.SerializerMethodField()
    next_session_dates = serializers.SerializerMethodField()

    class Meta:
        model = SessionSeries
        fields = [
            'id', 'title', 'description',
            'group', 'group_name', 'gm', 'gm_detail', 'scenario',
            'recurrence', 'recurrence_display',
            'weekday', 'weekday_display', 'day_of_month',
            'start_time', 'duration_minutes',
            'custom_interval_days',
            'start_date', 'end_date',
            'auto_create_sessions', 'auto_create_weeks_ahead',
            'is_active', 'session_count', 'next_session_dates',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_session_count(self, obj):
        return obj.sessions.count()

    def get_next_session_dates(self, obj):
        dates = obj.get_next_session_dates(count=3)
        return [d.isoformat() for d in dates]


class SessionSeriesCreateSerializer(serializers.ModelSerializer):
    """セッションシリーズ作成用シリアライザ"""

    class Meta:
        model = SessionSeries
        fields = [
            'title', 'description', 'group', 'scenario',
            'recurrence', 'weekday', 'day_of_month',
            'start_time', 'duration_minutes',
            'custom_interval_days',
            'start_date', 'end_date',
            'auto_create_sessions', 'auto_create_weeks_ahead',
        ]

    def validate(self, attrs):
        recurrence = attrs.get('recurrence', 'none')

        if recurrence in ['weekly', 'biweekly'] and attrs.get('weekday') is None:
            raise serializers.ValidationError({
                'weekday': '毎週/隔週の場合は曜日を指定してください'
            })

        if recurrence == 'monthly' and attrs.get('day_of_month') is None:
            raise serializers.ValidationError({
                'day_of_month': '毎月の場合は日を指定してください'
            })

        if recurrence == 'custom' and not attrs.get('custom_interval_days'):
            raise serializers.ValidationError({
                'custom_interval_days': 'カスタムの場合は間隔を指定してください'
            })

        group = attrs.get('group')
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if group and user and user.is_authenticated:
            if not (group.created_by_id == user.id or group.members.filter(id=user.id).exists()):
                raise serializers.ValidationError({
                    'group': 'このグループでシリーズを作成する権限がありません'
                })

        return attrs

    def create(self, validated_data):
        validated_data['gm'] = self.context['request'].user
        return super().create(validated_data)


class SessionAvailabilitySerializer(serializers.ModelSerializer):
    """参加可能日投票シリアライザ"""

    user_detail = UserSerializer(source='user', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SessionAvailability
        fields = [
            'id', 'session', 'occurrence', 'proposed_date',
            'user', 'user_detail', 'status', 'status_display', 'comment',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DatePollVoteSerializer(serializers.ModelSerializer):
    """日程調整投票シリアライザ"""

    user_detail = UserSerializer(source='user', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DatePollVote
        fields = [
            'id', 'option', 'user', 'user_detail',
            'status', 'status_display', 'comment',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DatePollCommentSerializer(serializers.ModelSerializer):
    """日程調整コメント（チャット）シリアライザ"""

    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = DatePollComment
        fields = [
            'id',
            'poll',
            'user',
            'user_detail',
            'content',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'poll', 'user', 'created_at', 'updated_at']


class DatePollOptionSerializer(serializers.ModelSerializer):
    """日程調整候補日シリアライザ"""

    votes = DatePollVoteSerializer(many=True, read_only=True)
    available_count = serializers.SerializerMethodField()
    maybe_count = serializers.SerializerMethodField()
    unavailable_count = serializers.SerializerMethodField()

    class Meta:
        model = DatePollOption
        fields = [
            'id', 'poll', 'datetime', 'note',
            'votes', 'available_count', 'maybe_count', 'unavailable_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_available_count(self, obj):
        return obj.votes.filter(status='available').count()

    def get_maybe_count(self, obj):
        return obj.votes.filter(status='maybe').count()

    def get_unavailable_count(self, obj):
        return obj.votes.filter(status='unavailable').count()


class DatePollSerializer(serializers.ModelSerializer):
    """日程調整シリアライザ"""

    created_by_detail = UserSerializer(source='created_by', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    options = DatePollOptionSerializer(many=True, read_only=True)
    session_detail = serializers.SerializerMethodField()

    class Meta:
        model = DatePoll
        fields = [
            'id', 'title', 'description',
            'group', 'group_name', 'created_by', 'created_by_detail',
            'deadline', 'is_closed', 'selected_date',
            'create_session_on_confirm', 'session', 'session_detail',
            'options',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'session', 'created_at', 'updated_at']

    def get_session_detail(self, obj):
        if obj.session:
            return {
                'id': obj.session.id,
                'title': obj.session.title,
                'date': obj.session.date.isoformat() if obj.session.date else None,
            }
        return None


class DatePollOptionCreateSerializer(serializers.Serializer):
    """日程調整候補日（作成用）"""

    datetime = serializers.DateTimeField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=100)


class DatePollCreateSerializer(serializers.ModelSerializer):
    """日程調整作成用シリアライザ"""

    session = serializers.PrimaryKeyRelatedField(
        queryset=TRPGSession.objects.all(),
        required=False,
        allow_null=True,
        help_text='既存セッションに紐付ける場合のセッションID',
    )
    options = DatePollOptionCreateSerializer(
        many=True,
        write_only=True,
        allow_empty=False,
        help_text="候補日リスト [{'datetime': '2024-01-01T19:00:00', 'note': '備考'}]"
    )

    class Meta:
        model = DatePoll
        fields = [
            'title', 'description', 'group',
            'deadline', 'create_session_on_confirm',
            'session',
            'options',
        ]

    def validate(self, attrs):
        group = attrs.get('group')
        session = attrs.get('session')
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if group and user and user.is_authenticated:
            if not (group.created_by_id == user.id or group.members.filter(id=user.id).exists()):
                raise serializers.ValidationError({
                    'group': 'このグループで日程調整を作成する権限がありません'
                })

        if session:
            if group and session.group_id != group.id:
                raise serializers.ValidationError({
                    'session': 'セッションと日程調整のグループが一致しません'
                })
            if user and user.is_authenticated and session.gm_id != user.id:
                raise serializers.ValidationError({
                    'session': 'セッションのGMのみが日程調整を作成できます'
                })
            if session.date is not None:
                raise serializers.ValidationError({
                    'session': '日程が確定済みのセッションには日程調整を作成できません'
                })
            if DatePoll.objects.filter(session=session, is_closed=False).exists():
                raise serializers.ValidationError({
                    'session': 'このセッションには未締め切りの日程調整が既にあります'
                })
        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop('options')
        validated_data['created_by'] = self.context['request'].user

        poll = DatePoll.objects.create(**validated_data)

        for option_data in options_data:
            DatePollOption.objects.create(
                poll=poll,
                datetime=option_data['datetime'],
                note=option_data.get('note', ''),
            )

        return poll
