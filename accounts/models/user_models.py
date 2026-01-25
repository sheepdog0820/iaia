"""
User-related models for accounts app
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from .base_models import TimestampedModel, timezone


class CustomUser(AbstractUser):
    """Custom user model with TRPG-specific fields"""
    nickname = models.CharField(max_length=50, blank=True)
    trpg_history = models.TextField(blank=True, help_text="過去のTRPG参加履歴")
    trpg_introduction_sheet = models.JSONField(default=dict, blank=True, help_text="TRPG自己紹介シート")
    profile_image = models.ImageField(upload_to='profiles/', blank=True)
    is_premium = models.BooleanField(default=False, help_text="課金ユーザ（高権限ユーザ）")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nickname or self.username

    @property
    def has_premium_access(self):
        return self.is_premium or self.is_staff or self.is_superuser


class Friend(TimestampedModel):
    """Friend relationship model"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friends')
    friend = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friend_of')
    
    class Meta:
        unique_together = ('user', 'friend')
        
    def __str__(self):
        return f"{self.user.nickname} -> {self.friend.nickname}"
