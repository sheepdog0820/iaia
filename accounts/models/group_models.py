"""
Group-related models for accounts app
"""

import base64
import hashlib
import secrets
from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .base_models import TimestampedModel
from .user_models import CustomUser


class Group(TimestampedModel):
    """User group model with visibility settings"""

    VISIBILITY_CHOICES = [
        ("private", "プライベート"),
        ("public", "公開"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="private")
    members = models.ManyToManyField(CustomUser, through="GroupMembership")
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="created_groups",
        null=True,
        blank=True,
        verbose_name="作成者",
    )
    owner = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="owned_groups", verbose_name="所有者")

    def save(self, *args, **kwargs):
        if self._state.adding and self.owner_id is None:
            self.owner_id = self.created_by_id
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GroupDiscordSettings(TimestampedModel):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="discord_settings")
    encrypted_webhook_url = models.TextField(blank=True, default="")
    enabled = models.BooleanField(default=False)
    event_types = models.JSONField(default=list, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    disabled_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def _fernet():
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def set_webhook_url(self, webhook_url):
        self.encrypted_webhook_url = (
            self._fernet().encrypt(webhook_url.encode("utf-8")).decode("ascii") if webhook_url else ""
        )

    def get_webhook_url(self):
        if not self.encrypted_webhook_url:
            return ""
        return self._fernet().decrypt(self.encrypted_webhook_url.encode("ascii")).decode("utf-8")

    @property
    def is_configured(self):
        return bool(self.encrypted_webhook_url)


class DiscordDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    settings = models.ForeignKey(GroupDiscordSettings, on_delete=models.CASCADE, related_name="deliveries")
    event_type = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class GroupLink(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    source_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="outgoing_links")
    target_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="incoming_links")
    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="requested_group_links")
    responded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responded_group_links",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_group", "target_group"],
                name="unique_directed_group_link",
            ),
            models.CheckConstraint(
                check=~models.Q(source_group=models.F("target_group")),
                name="group_link_groups_must_differ",
            ),
        ]


class GroupLinkShare(models.Model):
    class ResourceType(models.TextChoices):
        SESSION = "session", "Session"
        DATE_POLL = "date_poll", "Date poll"
        SCENARIO = "scenario", "Scenario"

    link = models.ForeignKey(GroupLink, on_delete=models.CASCADE, related_name="shares")
    owner_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="outgoing_resource_shares")
    resource_type = models.CharField(max_length=32, choices=ResourceType.choices)
    object_id = models.PositiveIntegerField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="created_group_link_shares")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["link", "owner_group", "resource_type", "object_id"],
                name="unique_group_link_resource_share",
            ),
        ]


class GroupMembership(models.Model):
    """Group membership model with role management"""

    OWNER_ROLE_ERROR = "所有者の管理者権限は解除できません。先に所有権を移譲してください。"
    OWNER_IDENTITY_ERROR = "所有者のメンバー情報は付け替えできません。先に所有権を移譲してください。"

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "group")

    def clean(self):
        super().clean()
        if self.pk:
            previous = type(self).objects.select_related("group").filter(pk=self.pk).first()
            if previous is not None:
                self._validate_owner_identity(previous, previous.group)
        owner_id = Group.objects.filter(pk=self.group_id).values_list("owner_id", flat=True).first()
        if owner_id is not None and owner_id == self.user_id:
            if self._state.adding:
                self.role = "admin"
            elif self.role != "admin":
                raise ValidationError({"role": self.OWNER_ROLE_ERROR})

    def _validate_owner_identity(self, previous, group):
        if group.owner_id == previous.user_id and (
            self.user_id != previous.user_id or self.group_id != previous.group_id
        ):
            raise ValidationError(self.OWNER_IDENTITY_ERROR)

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db or "default"
        with transaction.atomic(using=using):
            previous_group_id = (
                type(self).objects.using(using).filter(pk=self.pk).values_list("group_id", flat=True).first()
                if self.pk
                else None
            )
            group_ids = {self.group_id, previous_group_id} - {None}
            groups = {
                group.pk: group
                for group in Group.objects.using(using).select_for_update().filter(pk__in=group_ids).order_by("pk")
            }
            if self.group_id not in groups:
                raise Group.DoesNotExist
            previous = (
                type(self).objects.using(using).select_for_update().filter(pk=self.pk).first() if self.pk else None
            )
            if previous is not None:
                if previous.group_id not in groups:
                    raise ValidationError("所属先が変わりました。画面を再読み込みしてください。")
                self._validate_owner_identity(previous, groups[previous.group_id])
            group = groups[self.group_id]
            if group.owner_id == self.user_id:
                if self._state.adding:
                    self.role = "admin"
                elif self.role != "admin":
                    raise ValidationError(self.OWNER_ROLE_ERROR)
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.nickname} in {self.group.name} ({self.role})"


@receiver(pre_delete, sender=GroupMembership)
def protect_group_owner_membership(sender, instance, using, origin=None, **kwargs):
    # Explicit group deletion remains available to the existing group admins.
    if isinstance(origin, Group) or getattr(origin, "model", None) is Group:
        return
    with transaction.atomic(using=using):
        original = sender.objects.using(using).filter(pk=instance.pk).values("group_id", "user_id").first()
        if original is None:
            return
        group = Group.objects.using(using).select_for_update().filter(pk=original["group_id"]).first()
        current = (
            sender.objects.using(using).select_for_update().filter(pk=instance.pk).values("group_id", "user_id").first()
        )
        if current is None:
            return
        if current["group_id"] != original["group_id"]:
            raise ProtectedError("所属先が変わったため削除を中止しました。画面を再読み込みしてください。", {instance})
        # Deleted inline forms can contain edited user/group fields even when
        # Django ignores their model-validation errors. Protect the stored row.
        if group is not None and group.owner_id == current["user_id"]:
            raise ProtectedError("所有者は退出・除名できません。先に所有権を移譲してください。", {instance})


class GroupOwnershipTransfer(TimestampedModel):
    """One pending consent request; completed/cancelled requests are removed."""

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="ownership_transfer")
    requested_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sent_group_ownership_transfers"
    )
    target = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_group_ownership_transfers")
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(requested_by=models.F("target")), name="group_ownership_users_must_differ"
            ),
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("created_at")), name="group_ownership_expiry_after_creation"
            ),
        ]


class GroupInvitation(models.Model):
    """Group invitation model with status tracking"""

    INVITATION_EXPIRY_DAYS = 7
    STATUS_CHOICES = [
        ("pending", "保留中"),
        ("accepted", "承認済み"),
        ("declined", "拒否"),
        ("expired", "期限切れ"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invitations")
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_invitations")
    invitee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_invitations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True, help_text="招待メッセージ")

    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("group", "invitee")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inviter.nickname} invited {self.invitee.nickname} to {self.group.name}"

    @property
    def expires_at(self):
        return self.created_at + timedelta(days=self.INVITATION_EXPIRY_DAYS)

    @property
    def is_expired(self):
        return self.status == "pending" and timezone.now() >= self.expires_at

    def mark_expired(self, save=True):
        self.status = "expired"
        self.responded_at = timezone.now()
        if save:
            self.save(update_fields=["status", "responded_at"])

    @classmethod
    def expire_pending(cls):
        """期限切れの招待を一括更新"""
        cutoff = timezone.now() - timedelta(days=cls.INVITATION_EXPIRY_DAYS)
        return cls.objects.filter(status="pending", created_at__lt=cutoff).update(
            status="expired", responded_at=timezone.now()
        )


class GroupInviteLink(models.Model):
    """Token-based group invitation link for login-gated membership joins."""

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="invite_links",
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="created_group_invite_links",
    )
    token_digest = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(default=1)
    use_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite link for {self.group.name}"

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, group, created_by, expires_at, max_uses):
        token = secrets.token_urlsafe(32)
        invite_link = cls.objects.create(
            group=group,
            created_by=created_by,
            token_digest=cls.digest(token),
            expires_at=expires_at,
            max_uses=max_uses,
        )
        return invite_link, token

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now() and self.use_count < self.max_uses
