from django.db import models
from django.utils import timezone


class SupportTicket(models.Model):
    class Source(models.TextChoices):
        LINE = "line", "LINE"

    class Status(models.TextChoices):
        NEW = "new", "新規"
        INVESTIGATING = "investigating", "調査中"
        WAITING = "waiting", "利用者回答待ち"
        RESOLVED = "resolved", "対応済み"
        CLOSED = "closed", "終了"

    reference = models.CharField(max_length=32, unique=True, blank=True, null=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.LINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    subject = models.CharField(max_length=200)
    line_user_id = models.CharField(max_length=255, db_index=True)
    notification_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.reference:
            reference = f"LIN-{timezone.localdate():%Y}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(reference=reference)
            self.reference = reference

    def __str__(self):
        return f"{self.reference}: {self.subject}"


class SupportMessage(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "テキスト"
        IMAGE = "image", "画像"
        OTHER = "other", "その他"

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    body = models.TextField(blank=True)
    line_message_id = models.CharField(max_length=255, unique=True)
    attachment = models.FileField(upload_to="support/line/%Y/%m/%d/", blank=True)
    raw_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.ticket.reference} / {self.get_kind_display()}"


class LineWebhookEvent(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "受信済み"
        PROCESSED = "processed", "処理済み"
        IGNORED = "ignored", "対象外"
        FAILED = "failed", "失敗"

    event_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    raw_payload = models.JSONField(default=dict)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.SET_NULL,
        related_name="line_events",
        null=True,
        blank=True,
    )
    last_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return self.event_id
