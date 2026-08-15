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
    profile_image = models.ImageField(upload_to="profiles/", blank=True)
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

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="friends")
    friend = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="friend_of")

    class Meta:
        unique_together = ("user", "friend")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user=models.F("friend")),
                name="friend_users_must_differ",
            )
        ]

    def __str__(self):
        return f"{self.user.nickname} -> {self.friend.nickname}"


class FriendRequest(TimestampedModel):
    """A consent-based request that can establish a mutual friendship."""

    class Status(models.TextChoices):
        PENDING = "pending", "申請中"
        ACCEPTED = "accepted", "承認済み"
        DECLINED = "declined", "拒否"
        CANCELLED = "cancelled", "取消"

    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    pair_key = models.CharField(max_length=64, db_index=True, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_friend_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("recipient")),
                name="friend_request_users_must_differ",
            ),
            models.UniqueConstraint(
                fields=["pair_key"],
                condition=models.Q(status="pending"),
                name="unique_pending_friend_request_pair",
            ),
        ]

    @staticmethod
    def make_pair_key(first_user_id, second_user_id):
        low, high = sorted((int(first_user_id), int(second_user_id)))
        return f"{low}:{high}"

    def save(self, *args, **kwargs):
        if self.sender_id and self.recipient_id:
            self.pair_key = self.make_pair_key(self.sender_id, self.recipient_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender} -> {self.recipient} ({self.get_status_display()})"
