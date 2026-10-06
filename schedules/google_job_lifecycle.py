"""Start Google delivery once at a time using existing job state."""

from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import AsyncJob


def google_job_can_start(job):
    return job.status in (AsyncJob.Status.QUEUED, AsyncJob.Status.FAILED) and job.expires_at > timezone.now()


def claim_google_job_start(job):
    now = timezone.now()
    updated = AsyncJob.objects.filter(
        pk=job.pk,
        owner_id=job.owner_id,
        job_type=job.job_type,
        status__in=(AsyncJob.Status.QUEUED, AsyncJob.Status.FAILED),
        expires_at__gt=now,
    ).update(
        status=AsyncJob.Status.RUNNING,
        progress=0,
        started_at=Coalesce("started_at", now),
        finished_at=None,
        error="",
    )
    if not updated:
        return False
    job.refresh_from_db(fields=["status", "progress", "started_at", "finished_at", "error"])
    return True
