import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class ShareLink(models.Model):
    class ResourceType(models.TextChoices):
        CHARACTER = "character", "Character"
        SESSION = "session", "Session"
        SCENARIO = "scenario", "Scenario"
        PROFILE_STATS = "profile_stats", "Profile stats"

    class ViewLevel(models.TextChoices):
        SUMMARY = "summary", "Summary"
        STANDARD = "standard", "Standard"
        FULL = "full", "Full"

    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    object_id = models.PositiveIntegerField()
    token_digest = models.CharField(max_length=64, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_share_links",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    allow_anonymous = models.BooleanField(default=True)
    view_level = models.CharField(
        max_length=20,
        choices=ViewLevel.choices,
        default=ViewLevel.STANDARD,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "object_id"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return f"{self.resource_type}:{self.object_id}"

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(
        cls,
        *,
        resource_type,
        object_id,
        created_by,
        expires_at=None,
        allow_anonymous=True,
        view_level=ViewLevel.STANDARD,
    ):
        token = secrets.token_urlsafe(32)
        share_link = cls.objects.create(
            resource_type=resource_type,
            object_id=object_id,
            token_digest=cls.digest(token),
            created_by=created_by,
            expires_at=expires_at,
            allow_anonymous=allow_anonymous,
            view_level=view_level,
        )
        return share_link, token

    @classmethod
    def active_for_token(cls, token, resource_type):
        now = timezone.now()
        return (
            cls.objects.filter(
                token_digest=cls.digest(token),
                resource_type=resource_type,
                revoked_at__isnull=True,
            )
            .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
            .first()
        )

    @property
    def is_active(self):
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    def revoke(self, save=True):
        self.revoked_at = timezone.now()
        if save:
            self.save(update_fields=["revoked_at"])

    def reissue(self):
        token = secrets.token_urlsafe(32)
        self.token_digest = self.digest(token)
        self.revoked_at = None
        self.save(update_fields=["token_digest", "revoked_at"])
        return token
