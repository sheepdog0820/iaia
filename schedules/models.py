from django.db import models
from django.utils import timezone
from datetime import datetime, date as date_cls, time as time_cls, timedelta
from django.core.exceptions import ValidationError
import uuid
from accounts.models import CustomUser, Group, GroupMembership


class TRPGSession(models.Model):
    STATUS_CHOICES = [
        ('planned', '予定'),
        ('ongoing', '進行中'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'プライベート'),
        ('group', 'グループ内'),
        ('public', '公開'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    youtube_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planned')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='group')
    
    gm = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='gm_sessions')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    scenario = models.ForeignKey(
        'scenarios.Scenario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    participants = models.ManyToManyField(CustomUser, through='SessionParticipant', related_name='sessions')

    # 定期セッション/キャンペーン（ISSUE-017）
    series = models.ForeignKey(
        'SessionSeries',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        help_text="所属するセッションシリーズ"
    )

    duration_minutes = models.PositiveIntegerField(default=0, help_text="セッション時間（分）")

    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        session_date = kwargs.pop('session_date', None)
        start_time = kwargs.pop('start_time', None)
        estimated_hours = kwargs.pop('estimated_hours', None)
        kwargs.pop('min_players', None)
        kwargs.pop('max_players', None)

        if session_date and 'date' not in kwargs:
            if isinstance(session_date, datetime):
                session_dt = session_date
            else:
                if isinstance(session_date, str):
                    try:
                        session_date = date_cls.fromisoformat(session_date)
                    except ValueError:
                        session_date = None
                if isinstance(start_time, str):
                    try:
                        start_time = time_cls.fromisoformat(start_time)
                    except ValueError:
                        start_time = None
                if isinstance(session_date, date_cls):
                    if start_time is None:
                        start_time = time_cls(0, 0)
                    session_dt = datetime.combine(session_date, start_time)
                else:
                    session_dt = None

            if session_dt:
                if timezone.is_naive(session_dt):
                    session_dt = timezone.make_aware(session_dt, timezone.get_current_timezone())
                kwargs['date'] = session_dt

        if estimated_hours is not None and 'duration_minutes' not in kwargs:
            try:
                hours = float(estimated_hours)
                kwargs['duration_minutes'] = int(hours * 60)
            except (TypeError, ValueError):
                pass

        super().__init__(*args, **kwargs)
    
    def __str__(self):
        if not self.date:
            return f"{self.title} (日付未定)"
        return f"{self.title} ({self.date.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
        date_will_update = creating or update_fields is None or 'date' in update_fields

        old_date = None
        if not creating and date_will_update:
            old_date = TRPGSession.objects.filter(pk=self.pk).values_list('date', flat=True).first()

        auto_group_created = False
        if not self.group_id and self.gm_id:
            group_name = f"{self.gm.nickname or self.gm.username} Default Group"
            group, _ = Group.objects.get_or_create(
                name=group_name,
                created_by=self.gm,
                defaults={'visibility': 'private'}
            )
            GroupMembership.objects.get_or_create(
                user=self.gm,
                group=group,
                defaults={'role': 'admin'}
            )
            self.group = group
            auto_group_created = True

        if auto_group_created and self.visibility == 'group':
            self.visibility = 'public'

        super().save(*args, **kwargs)

        # Keep backward compatibility with the legacy single `date` field by ensuring
        # a primary occurrence exists and stays in sync when `date` changes.
        if self.date is None or not date_will_update:
            return

        if creating:
            if not self.occurrences.filter(is_primary=True).exists():
                SessionOccurrence.objects.create(
                    session=self,
                    start_at=self.date,
                    is_primary=True,
                )
            return

        if old_date != self.date:
            primary = self.occurrences.filter(is_primary=True).first()
            if primary:
                primary.start_at = self.date
                primary.save(update_fields=['start_at', 'updated_at'])
                return

            matching = self.occurrences.filter(start_at=old_date).order_by('id').first()
            if matching:
                self.occurrences.exclude(id=matching.id).filter(is_primary=True).update(is_primary=False)
                matching.start_at = self.date
                matching.is_primary = True
                matching.save(update_fields=['start_at', 'is_primary', 'updated_at'])
                return

            SessionOccurrence.objects.create(
                session=self,
                start_at=self.date,
                is_primary=True,
            )
    
    @property
    def youtube_total_duration(self):
        """YouTube動画の合計時間（秒）"""
        return SessionYouTubeLink.get_session_total_duration(self)
    
    @property
    def youtube_total_duration_display(self):
        """YouTube動画の合計時間（表示形式）"""
        return SessionYouTubeLink.format_duration(self.youtube_total_duration)
    
    @property
    def youtube_video_count(self):
        """YouTube動画の本数"""
        return self.youtube_links.count()
    
    class Meta:
        ordering = ['-date']


class SessionOccurrence(models.Model):
    """A scheduled occurrence of a session (allows multiple dates per TRPGSession)."""

    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='occurrences',
    )
    start_at = models.DateTimeField(db_index=True)
    content = models.TextField(blank=True, default='')
    is_primary = models.BooleanField(default=False, db_index=True)

    participants = models.ManyToManyField(
        CustomUser,
        through='SessionOccurrenceParticipant',
        related_name='session_occurrences',
        blank=True,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_at', 'id']
        indexes = [
            models.Index(fields=['session', 'start_at']),
            models.Index(fields=['session', 'is_primary']),
        ]

    def __str__(self):
        return f"{self.session.title} @ {self.start_at.strftime('%Y-%m-%d %H:%M')}"


class SessionOccurrenceParticipant(models.Model):
    occurrence = models.ForeignKey(SessionOccurrence, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [
            ['occurrence', 'user'],
        ]
        indexes = [
            models.Index(fields=['occurrence', 'user']),
            models.Index(fields=['user', 'occurrence']),
        ]

    def __str__(self):
        return f"{self.user.nickname or self.user.username} in {self.occurrence}"


class SessionParticipant(models.Model):
    ROLE_CHOICES = [
        ('gm', 'GM'),
        ('player', 'PL'),
    ]
    
    PLAYER_SLOT_CHOICES = [
        (1, 'プレイヤー1'),
        (2, 'プレイヤー2'),
        (3, 'プレイヤー3'),
        (4, 'プレイヤー4'),
    ]
    
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    character_name = models.CharField(max_length=100, blank=True)
    character_sheet_url = models.URLField(blank=True)
    
    # 新規フィールド: プレイヤー枠番号
    player_slot = models.IntegerField(
        choices=PLAYER_SLOT_CHOICES,
        null=True,
        blank=True,
        help_text="プレイヤー枠番号（1-4）"
    )
    
    # 新規フィールド: キャラクターシート直接参照
    character_sheet = models.ForeignKey(
        'accounts.CharacterSheet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_participations'
    )
    
    class Meta:
        unique_together = [
            ['session', 'user'],
            ['session', 'player_slot'],  # 同じセッション内で枠番号は重複不可
        ]
        
    def __str__(self):
        slot_display = f" (Slot {self.player_slot})" if self.player_slot else ""
        return f"{self.user.nickname} in {self.session.title} ({self.role}){slot_display}"


class SessionInvitation(models.Model):
    """セッション招待（受諾/辞退/期限切れを管理）"""

    INVITATION_EXPIRY_DAYS = 7
    STATUS_CHOICES = [
        ('pending', '保留'),
        ('accepted', '受諾'),
        ('declined', '辞退'),
        ('expired', '期限切れ'),
    ]

    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_session_invitations')
    invitee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_session_invitations')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="招待メッセージ")

    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'invitee')
        ordering = ['-created_at']

    def __str__(self):
        inviter_name = self.inviter.nickname or self.inviter.username
        invitee_name = self.invitee.nickname or self.invitee.username
        return f"{inviter_name} invited {invitee_name} to {self.session.title}"

    @property
    def expires_at(self):
        return self.created_at + timedelta(days=self.INVITATION_EXPIRY_DAYS)

    @property
    def is_expired(self):
        return self.status == 'pending' and timezone.now() >= self.expires_at

    def mark_expired(self, save=True):
        self.status = 'expired'
        self.responded_at = timezone.now()
        if save:
            self.save(update_fields=['status', 'responded_at'])

    @classmethod
    def expire_pending(cls):
        cutoff = timezone.now() - timedelta(days=cls.INVITATION_EXPIRY_DAYS)
        return cls.objects.filter(status='pending', created_at__lt=cutoff).update(
            status='expired',
            responded_at=timezone.now()
        )


class SessionNote(models.Model):
    """セッションノート（GM/参加者の記録）"""

    NOTE_TYPE_CHOICES = [
        ('gm_private', 'GMプライベート'),
        ('public_summary', '公開サマリー'),
        ('player_note', 'プレイヤーノート'),
        ('npc_memo', 'NPCメモ'),
        ('handover', '引き継ぎ事項'),
    ]

    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='session_notes'
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default='player_note'
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['session', 'note_type']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        title_display = f" - {self.title}" if self.title else ""
        return f"{self.session.title} ({self.note_type}){title_display}"


class SessionLog(models.Model):
    """セッションログ（時系列の出来事）"""

    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='session_logs'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    event_type = models.CharField(max_length=50, default='general')
    description = models.TextField()
    related_character = models.ForeignKey(
        'accounts.CharacterSheet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_logs'
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['timestamp', 'created_at']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.session.title} - {self.event_type}"


class HandoutInfo(models.Model):
    HANDOUT_NUMBER_CHOICES = [
        (1, 'HO1'),
        (2, 'HO2'),
        (3, 'HO3'),
        (4, 'HO4'),
    ]
    
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE, related_name='handouts')
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name='handouts')
    title = models.CharField(max_length=100)
    content = models.TextField()
    recommended_skills = models.TextField(
        blank=True,
        default='',
        help_text="推奨技能（カンマ/改行区切り）"
    )
    is_secret = models.BooleanField(default=True, help_text="秘匿ハンドアウトかどうか")
    
    # 新規フィールド: ハンドアウト番号
    handout_number = models.IntegerField(
        choices=HANDOUT_NUMBER_CHOICES,
        null=True,
        blank=True,
        help_text="ハンドアウト番号（HO1-HO4）"
    )
    
    # 新規フィールド: 割り当てプレイヤー枠
    assigned_player_slot = models.IntegerField(
        choices=SessionParticipant.PLAYER_SLOT_CHOICES,
        null=True,
        blank=True,
        help_text="割り当てられたプレイヤー枠"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        ho_display = f"HO{self.handout_number}" if self.handout_number else "HO"
        return f"{ho_display}: {self.title} - {self.participant.user.nickname}"
    
    class Meta:
        unique_together = [
            ['session', 'handout_number'],  # 同じセッション内でHO番号は重複不可
        ]
        ordering = ['handout_number', 'title']


class HandoutNotification(models.Model):
    """ハンドアウト配布通知モデル"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('handout_created', 'ハンドアウト作成'),
        ('handout_published', 'ハンドアウト公開'),
        ('handout_updated', 'ハンドアウト更新'),
        # セッション関連通知（ISSUE-013）
        ('session_invitation', 'セッション招待'),
        ('schedule_change', 'スケジュール変更'),
        ('session_cancelled', 'セッションキャンセル'),
        ('session_reminder', 'セッションリマインダー'),
        ('group_invitation', 'グループ招待'),
        # フレンドリクエスト通知（ISSUE-013）
        ('friend_request', 'フレンドリクエスト'),
        ('friend_request_accepted', 'フレンドリクエスト承認'),
    ]
    
    handout_id = models.PositiveIntegerField(help_text="対象ハンドアウトのID（セッション通知の場合は0）")
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='handout_notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_handout_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField(help_text="通知メッセージ")
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, null=True, help_text="追加メタデータ")
    
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_notification_type_display()} → {self.recipient.nickname}"
    
    def mark_as_read(self):
        """通知を既読にマーク"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['handout_id']),
        ]


class UserNotificationPreferences(models.Model):
    """ユーザー通知設定モデル"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    handout_notifications_enabled = models.BooleanField(default=True, help_text="ハンドアウト通知を有効にする")
    session_notifications_enabled = models.BooleanField(default=True, help_text="セッション通知を有効にする")
    group_notifications_enabled = models.BooleanField(default=True, help_text="グループ通知を有効にする")
    friend_notifications_enabled = models.BooleanField(default=True, help_text="フレンド通知を有効にする")
    email_notifications_enabled = models.BooleanField(default=False, help_text="メール通知を有効にする")
    browser_notifications_enabled = models.BooleanField(default=True, help_text="ブラウザ通知を有効にする")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.nickname}の通知設定"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """ユーザーの通知設定を取得または作成"""
        preferences, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'handout_notifications_enabled': True,
                'session_notifications_enabled': True,
                'group_notifications_enabled': True,
                'email_notifications_enabled': False,
                'browser_notifications_enabled': True,
            }
        )
        return preferences


class SessionImage(models.Model):
    """セッション添付画像モデル"""
    
    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='session_images/%Y/%m/%d/',
        help_text='セッションに関連する画像'
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text='画像のタイトル'
    )
    description = models.TextField(
        blank=True,
        help_text='画像の説明'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='表示順序'
    )
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_session_images'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['session', 'order']),
        ]
    
    def __str__(self):
        return f"{self.session.title} - {self.title or f'画像{self.order + 1}'}"
    
    def save(self, *args, **kwargs):
        # 新規作成時、orderを自動設定
        if not self.pk and self.order == 0 and hasattr(self, 'session_id') and self.session_id:
            max_order = SessionImage.objects.filter(
                session_id=self.session_id
            ).aggregate(
                max_order=models.Max('order')
            )['max_order']
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)
    
    def get_thumbnail_url(self):
        """サムネイルURL取得（将来的な実装用）"""
        return self.image.url if self.image else None
    
    def delete(self, *args, **kwargs):
        """削除時に画像ファイルも削除"""
        if self.image:
            try:
                if self.image.storage.exists(self.image.name):
                    self.image.delete(save=False)
            except Exception:
                pass
        super().delete(*args, **kwargs)


def handout_attachment_upload_path(instance, filename):
    """
    ハンドアウト添付ファイルのアップロードパスを生成
    パス形式: handouts/{session_id}/{handout_id}/{timestamp}_{filename}
    """
    import uuid
    from django.utils import timezone
    
    # ファイル名の安全化
    import os
    name, ext = os.path.splitext(filename)
    safe_filename = f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    
    return f"handouts/{instance.handout.session.id}/{instance.handout.id}/{safe_filename}"


class HandoutAttachment(models.Model):
    """ハンドアウト添付ファイルモデル"""
    
    FILE_TYPE_CHOICES = [
        ('image', '画像'),
        ('pdf', 'PDF'),
        ('audio', '音声'),
        ('video', '動画'),
        ('document', '文書'),
    ]
    
    handout = models.ForeignKey(HandoutInfo, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=handout_attachment_upload_path)
    original_filename = models.CharField(max_length=255, help_text="元のファイル名")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_size = models.PositiveIntegerField(help_text="ファイルサイズ（バイト）")
    content_type = models.CharField(max_length=100, help_text="MIMEタイプ")
    description = models.TextField(blank=True, help_text="添付ファイルの説明")
    
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_attachments')
    created_at = models.DateTimeField(default=timezone.now)
    
    # ファイルサイズ制限（バイト）
    MAX_FILE_SIZE = {
        'image': 10 * 1024 * 1024,      # 10MB
        'pdf': 20 * 1024 * 1024,        # 20MB
        'audio': 50 * 1024 * 1024,      # 50MB
        'video': 100 * 1024 * 1024,     # 100MB
        'document': 10 * 1024 * 1024,   # 10MB
    }
    
    # サポートされるMIMEタイプ
    SUPPORTED_CONTENT_TYPES = {
        'image': [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
        ],
        'pdf': [
            'application/pdf'
        ],
        'audio': [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'
        ],
        'video': [
            'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'
        ],
        'document': [
            'text/plain', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    }
    
    def __str__(self):
        return f"{self.original_filename} ({self.handout.title})"
    
    def clean(self):
        """モデルバリデーション"""
        super().clean()
        
        # ファイルタイプの妥当性チェック
        if self.file_type not in dict(self.FILE_TYPE_CHOICES):
            raise ValidationError(f"サポートされていないファイルタイプです: {self.file_type}")
        
        # ファイルサイズのチェック
        if self.file_size and self.file_type in self.MAX_FILE_SIZE:
            max_size = self.MAX_FILE_SIZE[self.file_type]
            if self.file_size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                raise ValidationError(
                    f"{self.get_file_type_display()}ファイルのサイズは{max_size_mb}MB以下である必要があります"
                )
        
        # MIMEタイプのチェック
        if self.content_type and self.file_type in self.SUPPORTED_CONTENT_TYPES:
            supported_types = self.SUPPORTED_CONTENT_TYPES[self.file_type]
            if self.content_type not in supported_types:
                raise ValidationError(
                    f"サポートされていないファイル形式です: {self.content_type}"
                )
    
    def save(self, *args, **kwargs):
        """保存時の処理"""
        # ファイルサイズの自動設定
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        # ファイルタイプの自動判定
        if self.file and not self.file_type:
            self.file_type = self.detect_file_type()
        
        # コンテンツタイプの自動設定
        if self.file and hasattr(self.file, 'content_type'):
            self.content_type = self.file.content_type
        
        # バリデーション実行
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    def detect_file_type(self):
        """ファイルタイプの自動判定"""
        if not self.content_type:
            return 'document'  # デフォルト
        
        for file_type, content_types in self.SUPPORTED_CONTENT_TYPES.items():
            if self.content_type in content_types:
                return file_type
        
        return 'document'  # 不明な場合はdocument扱い
    
    def get_download_url(self):
        """ダウンロードURL取得"""
        if self.file:
            return self.file.url
        return None
    
    def get_file_size_display(self):
        """ファイルサイズの人間が読みやすい表示"""
        if not self.file_size:
            return "不明"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def is_image(self):
        """画像ファイルかどうか"""
        return self.file_type == 'image'
    
    def is_pdf(self):
        """PDFファイルかどうか"""
        return self.file_type == 'pdf'
    
    def is_audio(self):
        """音声ファイルかどうか"""
        return self.file_type == 'audio'
    
    def is_video(self):
        """動画ファイルかどうか"""
        return self.file_type == 'video'
    
    def delete(self, *args, **kwargs):
        """削除時にファイルも削除"""
        if self.file:
            # ファイルが存在する場合のみ削除
            try:
                if self.file.storage.exists(self.file.name):
                    self.file.delete(save=False)
            except Exception:
                pass  # ファイル削除エラーは無視
        
        super().delete(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['handout', '-created_at']),
            models.Index(fields=['file_type']),
            models.Index(fields=['uploaded_by']),
        ]


class SessionYouTubeLink(models.Model):
    """セッションに関連するYouTube動画リンク"""
    
    # リレーション
    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='youtube_links'
    )
    added_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_youtube_links'
    )
    
    # YouTube情報
    youtube_url = models.URLField(max_length=500)
    video_id = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=200)
    duration_seconds = models.PositiveIntegerField(default=0)
    channel_name = models.CharField(max_length=100, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    
    # メタ情報
    perspective = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="視点",
        help_text="例: GM視点 / PL1視点 / 全体"
    )
    part_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="パート番号",
        help_text="分割されている場合のパート番号（例: 1,2,3）"
    )
    description = models.TextField(
        blank=True,
        verbose_name="備考",
        help_text="この動画についての説明やメモ"
    )
    order = models.PositiveIntegerField(default=0)
    
    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['session', 'video_id']
        indexes = [
            models.Index(fields=['session', 'order']),
        ]
    
    def __str__(self):
        return f"{self.session.title} - {self.title}"
    
    @property
    def duration_display(self):
        """再生時間を HH:MM:SS 形式で表示"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def save(self, *args, **kwargs):
        # video_idを抽出
        if self.youtube_url and not self.video_id:
            self.video_id = self.extract_video_id(self.youtube_url)
        
        # 新規作成時、orderを自動設定
        if not self.pk and self.order == 0:
            max_order = SessionYouTubeLink.objects.filter(
                session_id=self.session_id
            ).aggregate(
                max_order=models.Max('order')
            )['max_order']
            self.order = (max_order or 0) + 1
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def extract_video_id(url):
        """YouTube URLから動画IDを抽出"""
        import re
        
        if not url:
            return None
            
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]+)',
            r'(?:youtube\.com\/embed\/)([^&\n?]+)',
            r'(?:youtube\.com\/live\/)([^&\n?/]+)',
            r'(?:youtube\.com\/shorts\/)([^&\n?/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def get_session_total_duration(cls, session):
        """セッションの動画合計時間を取得"""
        from django.db.models import Sum
        result = cls.objects.filter(session=session).aggregate(
            total=Sum('duration_seconds')
        )
        return result['total'] or 0
    
    @classmethod
    def get_session_statistics(cls, session):
        """セッションの動画統計情報を取得"""
        from django.db.models import Sum, Avg, Count
        videos = cls.objects.filter(session=session)
        
        stats = videos.aggregate(
            count=Count('id'),
            total_duration=Sum('duration_seconds'),
            avg_duration=Avg('duration_seconds')
        )
        
        # チャンネル別集計
        channel_stats = videos.values('channel_name').annotate(
            video_count=Count('id'),
            total_duration=Sum('duration_seconds')
        ).order_by('-video_count')
        
        return {
            'video_count': stats['count'] or 0,
            'total_duration_seconds': stats['total_duration'] or 0,
            'total_duration_display': cls.format_duration(stats['total_duration'] or 0),
            'average_duration_seconds': int(stats['avg_duration'] or 0),
            'average_duration_display': cls.format_duration(int(stats['avg_duration'] or 0)),
            'channel_breakdown': list(channel_stats)
        }
    
    @staticmethod
    def format_duration(seconds):
        """秒数を HH:MM:SS 形式にフォーマット"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"


# =====================================================
# 高度なスケジューリング機能（ISSUE-017）
# =====================================================


class SessionSeries(models.Model):
    """定期セッション・キャンペーン管理モデル（ISSUE-017）"""

    RECURRENCE_CHOICES = [
        ('none', '単発'),
        ('weekly', '毎週'),
        ('biweekly', '隔週'),
        ('monthly', '毎月'),
        ('custom', 'カスタム'),
    ]

    WEEKDAY_CHOICES = [
        (0, '月曜日'),
        (1, '火曜日'),
        (2, '水曜日'),
        (3, '木曜日'),
        (4, '金曜日'),
        (5, '土曜日'),
        (6, '日曜日'),
    ]

    title = models.CharField(max_length=200, help_text="シリーズ/キャンペーン名")
    description = models.TextField(blank=True, help_text="シリーズの説明")

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='session_series'
    )
    gm = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='gm_session_series'
    )
    scenario = models.ForeignKey(
        'scenarios.Scenario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_series'
    )

    # 定期開催設定
    recurrence = models.CharField(
        max_length=10,
        choices=RECURRENCE_CHOICES,
        default='none',
        help_text="繰り返しパターン"
    )
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text="曜日（毎週/隔週の場合）"
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="日（毎月の場合、1-31）"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="開始時刻"
    )
    duration_minutes = models.PositiveIntegerField(
        default=180,
        help_text="予定時間（分）"
    )

    # カスタム間隔
    custom_interval_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="カスタム間隔（日数）"
    )

    # 期間
    start_date = models.DateField(help_text="シリーズ開始日")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="シリーズ終了日（空の場合は無期限）"
    )

    # 自動生成設定
    auto_create_sessions = models.BooleanField(
        default=True,
        help_text="セッションを自動生成する"
    )
    auto_create_weeks_ahead = models.PositiveIntegerField(
        default=4,
        help_text="何週間先まで自動生成するか"
    )

    is_active = models.BooleanField(default=True, help_text="シリーズがアクティブか")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "セッションシリーズ"
        verbose_name_plural = "セッションシリーズ"

    def __str__(self):
        return f"{self.title} ({self.get_recurrence_display()})"

    def get_next_session_dates(self, count=5):
        """次回以降のセッション日程を計算"""
        import calendar
        from datetime import date as date_cls, timedelta

        if not count or count <= 0:
            return []

        if self.recurrence == 'none':
            return []

        today = timezone.localdate()
        start_date = self.start_date

        def _in_range(target_date):
            if target_date < start_date:
                return False
            if self.end_date and target_date > self.end_date:
                return False
            return True

        dates = []

        if self.recurrence in ('weekly', 'biweekly'):
            if self.weekday is None:
                return []

            interval_days = 7 if self.recurrence == 'weekly' else 14
            days_until = (self.weekday - start_date.weekday()) % 7
            first = start_date + timedelta(days=days_until)

            if first <= today:
                days_since = (today - first).days
                steps = (days_since // interval_days) + 1
                first = first + timedelta(days=steps * interval_days)

            current = first
            while len(dates) < count and _in_range(current):
                dates.append(current)
                current = current + timedelta(days=interval_days)

            return dates

        if self.recurrence == 'monthly':
            if not self.day_of_month:
                return []

            def _next_month(year, month):
                if month == 12:
                    return year + 1, 1
                return year, month + 1

            def _month_candidate(year, month):
                last_day = calendar.monthrange(year, month)[1]
                return date_cls(year, month, min(self.day_of_month, last_day))

            year = start_date.year
            month = start_date.month
            candidate = _month_candidate(year, month)
            if candidate < start_date:
                year, month = _next_month(year, month)
                candidate = _month_candidate(year, month)

            while candidate <= today:
                year, month = _next_month(year, month)
                candidate = _month_candidate(year, month)

            current = candidate
            while len(dates) < count and _in_range(current):
                dates.append(current)
                year, month = _next_month(year, month)
                current = _month_candidate(year, month)

            return dates

        if self.recurrence == 'custom':
            interval_days = self.custom_interval_days
            if not interval_days:
                return []

            first = start_date
            if first <= today:
                days_since = (today - first).days
                steps = (days_since // interval_days) + 1
                first = first + timedelta(days=steps * interval_days)

            current = first
            while len(dates) < count and _in_range(current):
                dates.append(current)
                current = current + timedelta(days=interval_days)

            return dates

        return []

    def create_session_for_date(self, session_date):
        """指定日のセッションを作成"""
        from datetime import datetime

        if self.start_time:
            session_datetime = datetime.combine(session_date, self.start_time)
            if timezone.is_naive(session_datetime):
                session_datetime = timezone.make_aware(
                    session_datetime, timezone.get_current_timezone()
                )
        else:
            session_datetime = timezone.make_aware(
                datetime.combine(session_date, time_cls(19, 0)),
                timezone.get_current_timezone()
            )

        session = TRPGSession.objects.create(
            title=f"{self.title} #{self.sessions.count() + 1}",
            description=self.description,
            date=session_datetime,
            gm=self.gm,
            group=self.group,
            scenario=self.scenario,
            duration_minutes=self.duration_minutes,
            status='planned',
            visibility='group',
        )
        session.series = self
        session.save()
        return session


class SessionAvailability(models.Model):
    """参加可能日投票モデル（ISSUE-017）"""

    AVAILABILITY_CHOICES = [
        ('available', '参加可能'),
        ('maybe', '未定'),
        ('unavailable', '参加不可'),
    ]

    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.CASCADE,
        related_name='availability_votes',
        null=True,
        blank=True,
    )
    occurrence = models.ForeignKey(
        SessionOccurrence,
        on_delete=models.CASCADE,
        related_name='availability_votes',
        null=True,
        blank=True,
    )
    proposed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="候補日時（セッション/オカレンスが未確定の場合）"
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='availability_votes'
    )
    status = models.CharField(
        max_length=15,
        choices=AVAILABILITY_CHOICES,
        default='available'
    )
    comment = models.CharField(
        max_length=200,
        blank=True,
        help_text="コメント（遅刻/早退など）"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['proposed_date', 'created_at']
        unique_together = [
            ('session', 'user'),
            ('occurrence', 'user'),
        ]
        indexes = [
            models.Index(fields=['session', 'user']),
            models.Index(fields=['occurrence', 'user']),
            models.Index(fields=['proposed_date']),
        ]

    def __str__(self):
        target = self.session or self.occurrence or self.proposed_date
        return f"{self.user.nickname or self.user.username}: {self.get_status_display()} ({target})"


class DatePoll(models.Model):
    """日程調整投票モデル（ISSUE-017）"""

    title = models.CharField(max_length=200, help_text="投票タイトル")
    description = models.TextField(blank=True, help_text="説明")

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='date_polls'
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_date_polls'
    )

    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="投票締め切り"
    )
    is_closed = models.BooleanField(default=False, help_text="投票が締め切られたか")
    selected_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="確定日時"
    )

    # 投票から自動でセッションを作成するか
    create_session_on_confirm = models.BooleanField(
        default=True,
        help_text="確定時にセッションを作成"
    )
    session = models.ForeignKey(
        TRPGSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='date_polls',
        help_text="作成されたセッション"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "日程調整"
        verbose_name_plural = "日程調整"

    def __str__(self):
        return self.title

    def get_vote_summary(self):
        """投票サマリーを取得"""
        from django.db.models import Count, Case, When, IntegerField

        options = self.options.annotate(
            available_count=Count(
                Case(When(votes__status='available', then=1), output_field=IntegerField())
            ),
            maybe_count=Count(
                Case(When(votes__status='maybe', then=1), output_field=IntegerField())
            ),
            unavailable_count=Count(
                Case(When(votes__status='unavailable', then=1), output_field=IntegerField())
            ),
        ).order_by('-available_count', '-maybe_count', 'datetime')

        return options

    def confirm_date(self, selected_option):
        """日程を確定する"""
        selected_dt = selected_option.datetime
        if selected_dt and timezone.is_naive(selected_dt):
            selected_dt = timezone.make_aware(selected_dt, timezone.get_current_timezone())

        self.selected_date = selected_dt
        self.is_closed = True
        self.save()

        if self.session:
            session = self.session
            session.date = self.selected_date
            session.save(update_fields=['date', 'updated_at'])
            return session

        if self.create_session_on_confirm and not self.session:
            session = TRPGSession.objects.create(
                title=self.title,
                description=self.description,
                date=self.selected_date,
                gm=self.created_by,
                group=self.group,
                status='planned',
                visibility='group',
            )
            self.session = session
            self.save()
            return session
        return None


class DatePollOption(models.Model):
    """日程調整の候補日モデル（ISSUE-017）"""

    poll = models.ForeignKey(
        DatePoll,
        on_delete=models.CASCADE,
        related_name='options'
    )
    datetime = models.DateTimeField(help_text="候補日時")
    note = models.CharField(
        max_length=100,
        blank=True,
        help_text="備考"
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['datetime']

    def __str__(self):
        return f"{self.poll.title}: {self.datetime.strftime('%Y-%m-%d %H:%M')}"


class DatePollVote(models.Model):
    """日程調整への投票モデル（ISSUE-017）"""

    VOTE_CHOICES = [
        ('available', '◯ 参加可能'),
        ('maybe', '△ 未定'),
        ('unavailable', '✕ 参加不可'),
    ]

    option = models.ForeignKey(
        DatePollOption,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='date_poll_votes'
    )
    status = models.CharField(
        max_length=15,
        choices=VOTE_CHOICES,
        default='available'
    )
    comment = models.CharField(
        max_length=100,
        blank=True,
        help_text="コメント"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['option', 'user']
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.nickname or self.user.username}: {self.get_status_display()}"


class DatePollComment(models.Model):
    """日程調整のコメント（チャット）モデル（ISSUE-017）"""

    poll = models.ForeignKey(
        DatePoll,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='date_poll_comments',
    )
    content = models.TextField(help_text="コメント本文")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['poll', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        user_display = self.user.nickname or self.user.username
        return f"{self.poll.title}: {user_display}"
