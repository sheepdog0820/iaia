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


def fail_stale_background_removal_job(job, *, now=None):
    """Fail a pending/running job that can no longer be expected to finish."""
    if job.status not in {BackgroundRemovalJob.Status.PENDING, BackgroundRemovalJob.Status.RUNNING}:
        return False
    timeout_seconds = max(int(getattr(settings, "BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS", 900)), 60)
    if job.updated_at > (now or timezone.now()) - timedelta(seconds=timeout_seconds):
        return False
    job.status = BackgroundRemovalJob.Status.FAILED
    job.error_message = "Background removal timed out."
    update_fields = ["status", "error_message", "updated_at"]
    if clear_background_removal_source(job):
        update_fields.append("source_image")
    job.save(update_fields=update_fields)
    return True


def _delete_job_file(job, field_name):
    field_file = getattr(job, field_name)
    if not field_file:
        return True
    try:
        field_file.delete(save=False)
    except Exception:
        logger.exception("Background removal %s cleanup failed for job %s", field_name, job.pk)
        return False
    setattr(job, field_name, "")
    return True


def cleanup_background_removal_jobs(*, now=None, dry_run=False):
    """Remove expired background-removal results and terminal job records."""
    now = now or timezone.now()
    result_retention_hours = max(
        int(getattr(settings, "BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS", 24)),
        1,
    )
    job_retention_days = max(
        int(getattr(settings, "BACKGROUND_REMOVAL_JOB_RETENTION_DAYS", 7)),
        1,
    )
    timeout_seconds = max(int(getattr(settings, "BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS", 900)), 60)
    result_cutoff = now - timedelta(hours=result_retention_hours)
    job_cutoff = now - timedelta(days=job_retention_days)
    timeout_cutoff = now - timedelta(seconds=timeout_seconds)
    stale_active_jobs = BackgroundRemovalJob.objects.filter(
        status__in=(BackgroundRemovalJob.Status.PENDING, BackgroundRemovalJob.Status.RUNNING),
        updated_at__lte=timeout_cutoff,
    ).order_by("pk")
    terminal_statuses = (BackgroundRemovalJob.Status.COMPLETED, BackgroundRemovalJob.Status.FAILED)
    expired_jobs = BackgroundRemovalJob.objects.filter(
        status__in=terminal_statuses,
        updated_at__lte=job_cutoff,
    ).order_by("pk")
    expired_results = BackgroundRemovalJob.objects.filter(
        status=BackgroundRemovalJob.Status.COMPLETED,
        result_image__gt="",
        updated_at__lte=result_cutoff,
        updated_at__gt=job_cutoff,
    ).order_by("pk")
    summary = {
        "timed_out_jobs": stale_active_jobs.count(),
        "expired_jobs": expired_jobs.count(),
        "expired_result_images": expired_results.count(),
        "deleted_jobs": 0,
        "deleted_result_images": 0,
        "failed_jobs": 0,
    }
    if dry_run:
        return summary

    timed_out_jobs = 0
    for job in stale_active_jobs.iterator():
        if fail_stale_background_removal_job(job, now=now):
            timed_out_jobs += 1
    summary["timed_out_jobs"] = timed_out_jobs

    for job in expired_jobs.iterator():
        cleared_fields = []
        deletion_failed = False
        for field_name in ("source_image", "result_image"):
            if not getattr(job, field_name):
                continue
            if _delete_job_file(job, field_name):
                cleared_fields.append(field_name)
            else:
                deletion_failed = True
        if deletion_failed:
            if cleared_fields:
                job.save(update_fields=cleared_fields)
            summary["failed_jobs"] += 1
            continue
        job.delete()
        summary["deleted_jobs"] += 1

    for job in expired_results.iterator():
        if not _delete_job_file(job, "result_image"):
            summary["failed_jobs"] += 1
            continue
        job.save(update_fields=["result_image"])
        summary["deleted_result_images"] += 1

    return summary


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
