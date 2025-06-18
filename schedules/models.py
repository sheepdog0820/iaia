from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Group


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
    date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    youtube_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planned')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='group')
    
    gm = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='gm_sessions')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    participants = models.ManyToManyField(CustomUser, through='SessionParticipant', related_name='sessions')
    
    duration_minutes = models.PositiveIntegerField(default=0, help_text="セッション時間（分）")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.date.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-date']


class SessionParticipant(models.Model):
    ROLE_CHOICES = [
        ('gm', 'GM'),
        ('player', 'PL'),
    ]
    
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    character_name = models.CharField(max_length=100, blank=True)
    character_sheet_url = models.URLField(blank=True)
    
    class Meta:
        unique_together = ('session', 'user')
        
    def __str__(self):
        return f"{self.user.nickname} in {self.session.title} ({self.role})"


class HandoutInfo(models.Model):
    session = models.ForeignKey(TRPGSession, on_delete=models.CASCADE, related_name='handouts')
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name='handouts')
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_secret = models.BooleanField(default=True, help_text="秘匿ハンドアウトかどうか")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.participant.user.nickname}"
    
    class Meta:
        ordering = ['title']


class HandoutNotification(models.Model):
    """ハンドアウト配布通知モデル"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('handout_created', 'ハンドアウト作成'),
        ('handout_published', 'ハンドアウト公開'),
        ('handout_updated', 'ハンドアウト更新'),
    ]
    
    handout_id = models.PositiveIntegerField(help_text="対象ハンドアウトのID")
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='handout_notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_handout_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField(help_text="通知メッセージ")
    is_read = models.BooleanField(default=False)
    
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
                'email_notifications_enabled': False,
                'browser_notifications_enabled': True,
            }
        )
        return preferences


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
