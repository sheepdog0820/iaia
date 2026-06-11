"""
Group-related models for accounts app
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .base_models import TimestampedModel
from .user_models import CustomUser


class Group(TimestampedModel):
    """User group model with visibility settings"""
    VISIBILITY_CHOICES = [
        ('private', 'プライベート'),
        ('public', '公開'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    members = models.ManyToManyField(CustomUser, through='GroupMembership')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_groups')
    
    def __str__(self):
        return self.name


class GroupDiscordSettings(TimestampedModel):
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name='discord_settings'
    )
    encrypted_webhook_url = models.TextField(blank=True, default='')
    enabled = models.BooleanField(default=False)
    event_types = models.JSONField(default=list, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    disabled_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def _fernet():
        digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def set_webhook_url(self, webhook_url):
        self.encrypted_webhook_url = (
            self._fernet().encrypt(webhook_url.encode('utf-8')).decode('ascii')
            if webhook_url else ''
        )

    def get_webhook_url(self):
        if not self.encrypted_webhook_url:
            return ''
        return self._fernet().decrypt(
            self.encrypted_webhook_url.encode('ascii')
        ).decode('utf-8')

    @property
    def is_configured(self):
        return bool(self.encrypted_webhook_url)


class DiscordDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    settings = models.ForeignKey(
        GroupDiscordSettings, on_delete=models.CASCADE, related_name='deliveries'
    )
    event_type = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class GroupMembership(models.Model):
    """Group membership model with role management"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'group')
        
    def __str__(self):
        return f"{self.user.nickname} in {self.group.name} ({self.role})"


class GroupInvitation(models.Model):
    """Group invitation model with status tracking"""
    INVITATION_EXPIRY_DAYS = 7
    STATUS_CHOICES = [
        ('pending', '保留中'),
        ('accepted', '承認済み'),
        ('declined', '拒否'),
        ('expired', '期限切れ'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="招待メッセージ")
    
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('group', 'invitee')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.inviter.nickname} invited {self.invitee.nickname} to {self.group.name}"

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
        """期限切れの招待を一括更新"""
        cutoff = timezone.now() - timedelta(days=cls.INVITATION_EXPIRY_DAYS)
        return cls.objects.filter(status='pending', created_at__lt=cutoff).update(
            status='expired',
            responded_at=timezone.now()
        )
