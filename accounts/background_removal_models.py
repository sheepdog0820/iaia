import uuid

from django.conf import settings
from django.db import models


class BackgroundRemovalJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="background_removal_jobs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    source_image = models.ImageField(upload_to="background_removal/input/", blank=True)
    result_image = models.ImageField(upload_to="background_removal/output/", blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    task_arn = models.CharField(max_length=512, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
