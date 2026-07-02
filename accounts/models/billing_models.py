import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class PremiumSubscription(models.Model):
    ACTIVE_STATUSES = {"active", "trialing"}
    PROMO_STATUS = "promo"
    ACCESS_SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("stripe", "Stripe"),
        ("promo_code", "Promo code"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="premium_subscription",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, db_index=True)
    billing_interval = models.CharField(max_length=32, blank=True, db_index=True)
    subscription_status = models.CharField(max_length=64, blank=True, db_index=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    access_source = models.CharField(
        max_length=32,
        choices=ACCESS_SOURCE_CHOICES,
        default="manual",
        db_index=True,
    )
    premium_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, blank=True)
    last_webhook_event_id = models.CharField(max_length=255, blank=True)
    last_payment_failed_at = models.DateTimeField(null=True, blank=True)
    last_refund_or_dispute_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Premium subscription"
        verbose_name_plural = "Premium subscriptions"

    def __str__(self):
        return f'{self.user} ({self.subscription_status or "no subscription"})'

    @property
    def is_stripe_active(self):
        return self.subscription_status in self.ACTIVE_STATUSES and self.revoked_at is None

    @property
    def is_promo_active(self):
        return (
            self.subscription_status == self.PROMO_STATUS
            and self.revoked_at is None
            and (self.premium_expires_at is None or self.premium_expires_at > timezone.now())
        )

    @property
    def is_access_active(self):
        return self.is_stripe_active or self.is_promo_active

    @property
    def has_manual_premium_override(self):
        latest_manual_log = (
            PremiumAuditLog.objects.filter(
                user=self.user,
                source="manual",
                action__in=("granted", "revoked"),
            )
            .order_by("-created_at", "-pk")
            .first()
        )
        return bool(latest_manual_log and latest_manual_log.action == "granted")

    @property
    def expected_user_premium_access(self):
        return self.is_access_active or self.has_manual_premium_override

    def sync_user_premium_access(self, save=True):
        self.user.is_premium = self.expected_user_premium_access
        if save:
            self.user.save(update_fields=["is_premium"])

    def revoke_access(self, reason, save=True, preserve_manual_override=False):
        self.subscription_status = "revoked"
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.user.is_premium = self.has_manual_premium_override if preserve_manual_override else False
        if save:
            self.save(
                update_fields=[
                    "subscription_status",
                    "revoked_at",
                    "revoked_reason",
                    "updated_at",
                ]
            )
            self.user.save(update_fields=["is_premium"])


class StripeWebhookEvent(models.Model):
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    )

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    processing_status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_SUCCEEDED,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.event_type}: {self.event_id}"


class PremiumAccessCode(models.Model):
    code_digest = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=100, blank=True)
    campaign_name = models.CharField(max_length=100, blank=True, db_index=True)
    note = models.TextField(blank=True)
    max_uses = models.PositiveIntegerField(default=1)
    use_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_premium_access_codes",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.label or f"Premium code #{self.pk}"

    @staticmethod
    def normalize_code(code):
        return (code or "").strip().replace(" ", "").upper()

    @classmethod
    def digest(cls, code):
        return hashlib.sha256(cls.normalize_code(code).encode("utf-8")).hexdigest()

    @classmethod
    def generate_code(cls):
        return f'PREMIUM-{secrets.token_urlsafe(12).replace("_", "").replace("-", "").upper()}'

    @classmethod
    def issue(
        cls,
        *,
        code=None,
        max_uses=1,
        expires_at=None,
        label="",
        campaign_name="",
        note="",
        created_by=None,
    ):
        raw_code = cls.normalize_code(code) if code else cls.generate_code()
        access_code = cls.objects.create(
            code_digest=cls.digest(raw_code),
            max_uses=max_uses,
            expires_at=expires_at,
            label=label,
            campaign_name=campaign_name,
            note=note,
            created_by=created_by,
        )
        return access_code, raw_code

    @property
    def is_active(self):
        return (
            self.revoked_at is None
            and (self.expires_at is None or self.expires_at > timezone.now())
            and self.use_count < self.max_uses
        )

    @property
    def status_label(self):
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return "expired"
        if self.use_count >= self.max_uses:
            return "exhausted"
        return "active"


class PremiumAccessCodeRedemption(models.Model):
    access_code = models.ForeignKey(
        PremiumAccessCode,
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="premium_code_redemptions",
    )
    redeemed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("access_code", "user")
        ordering = ["-redeemed_at"]

    def __str__(self):
        return f"{self.user} redeemed {self.access_code}"


class PremiumAuditLog(models.Model):
    ACTION_CHOICES = [
        ("granted", "Granted"),
        ("restored", "Restored"),
        ("revoked", "Revoked"),
        ("payment_failed", "Payment failed"),
        ("payment_recovered", "Payment recovered"),
        ("refunded", "Refunded"),
        ("disputed", "Disputed"),
        ("reviewed", "Reviewed"),
        ("webhook", "Webhook"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="premium_audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="premium_audit_actions",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    source = models.CharField(max_length=32, blank=True, db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    stripe_event_id = models.CharField(max_length=255, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} ({self.source})"
