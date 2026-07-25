"""Dispatch and execute isolated background-removal jobs."""

import io
import logging
import os
import re
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from accounts.background_removal import remove_background
from accounts.background_removal_models import BackgroundRemovalJob

logger = logging.getLogger(__name__)


def clear_background_removal_source(job):
    """Delete a persisted source image without changing the job outcome."""
    if not job.source_image:
        return False
    try:
        job.source_image.delete(save=False)
    except Exception:
        logger.exception("Background removal source cleanup failed for job %s", job.pk)
        return False
    job.source_image = ""
    return True


def fail_stale_background_removal_job(job):
    """Fail a pending/running job that can no longer be expected to finish."""
    if job.status not in {BackgroundRemovalJob.Status.PENDING, BackgroundRemovalJob.Status.RUNNING}:
        return False
    timeout_seconds = max(int(getattr(settings, "BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS", 900)), 60)
    if job.updated_at > timezone.now() - timedelta(seconds=timeout_seconds):
        return False
    job.status = BackgroundRemovalJob.Status.FAILED
    job.error_message = "Background removal timed out."
    update_fields = ["status", "error_message", "updated_at"]
    if clear_background_removal_source(job):
        update_fields.append("source_image")
    job.save(update_fields=update_fields)
    return True


def start_background_removal_task(job):
    """Launch one Fargate task for a persisted job; never run inference in web."""
    task_definition = getattr(settings, "BACKGROUND_REMOVAL_TASK_DEFINITION", "")
    container_name = getattr(settings, "BACKGROUND_REMOVAL_CONTAINER_NAME", "background-removal")
    subnets = getattr(settings, "BACKGROUND_REMOVAL_SUBNETS", [])
    security_groups = getattr(settings, "BACKGROUND_REMOVAL_SECURITY_GROUPS", [])
    assign_public_ip = getattr(settings, "BACKGROUND_REMOVAL_ASSIGN_PUBLIC_IP", False)
    if not task_definition or not container_name or not subnets or not security_groups:
        raise RuntimeError("Background removal worker is not configured.")

    import boto3

    response = boto3.client("ecs", region_name=getattr(settings, "AWS_S3_REGION_NAME", None)).run_task(
        cluster=getattr(settings, "BACKGROUND_REMOVAL_ECS_CLUSTER", "tableno-aws-pre"),
        launchType="FARGATE",
        taskDefinition=task_definition,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": container_name,
                    "command": ["python", "manage.py", "process_background_removal_job", str(job.pk)],
                }
            ]
        },
    )
    failures = response.get("failures", [])
    if failures or not response.get("tasks"):
        raise RuntimeError(f"Unable to launch background removal worker: {failures}")
    job.task_arn = response["tasks"][0]["taskArn"]
    job.save(update_fields=["task_arn", "updated_at"])


def process_background_removal_job(job_id):
    with transaction.atomic():
        job = BackgroundRemovalJob.objects.select_for_update().get(pk=job_id)
        if job.status != BackgroundRemovalJob.Status.PENDING:
            return job
        job.status = BackgroundRemovalJob.Status.RUNNING
        job.save(update_fields=["status", "updated_at"])

    try:
        with job.source_image.open("rb") as source_file:
            transparent_png = remove_background(source_file.read())
        with Image.open(io.BytesIO(transparent_png)) as result:
            if result.format != "PNG":
                raise ValueError("Background removal returned a non-PNG image.")
        filename_root = os.path.splitext(os.path.basename(job.original_filename or "character"))[0]
        filename_root = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", filename_root).strip(" ._") or "character"
        filename = f"{filename_root}-transparent.png"
        job.result_image.save(filename, ContentFile(transparent_png), save=False)
        job.status = BackgroundRemovalJob.Status.COMPLETED
        job.error_message = ""
        update_fields = ["result_image", "status", "error_message", "updated_at"]
    except Exception:
        logger.exception("Background removal worker failed for job %s", job.pk)
        job.status = BackgroundRemovalJob.Status.FAILED
        job.error_message = "Background removal could not be completed."
        update_fields = ["status", "error_message", "updated_at"]
    if clear_background_removal_source(job):
        update_fields.append("source_image")
    job.save(update_fields=update_fields)
    return job
