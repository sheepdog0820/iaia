"""Start Google delivery once at a time using existing job state."""

from functools import wraps
from uuid import UUID

from django.db import transaction
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import AsyncJob, GoogleCalendarSync


def fail_unstarted_google_dispatch(job, error, sync=None):
    """A late publisher failure must never overwrite a worker's claimed job."""
    now = timezone.now()
    with transaction.atomic():
        updated = AsyncJob.objects.filter(
            pk=job.pk,
            owner_id=job.owner_id,
            job_type=job.job_type,
            status=AsyncJob.Status.QUEUED,
            started_at__isnull=True,
            expires_at__gt=now,
        ).update(status=AsyncJob.Status.FAILED, error=str(error), finished_at=now)
        if updated and sync is not None:
            # Keep both changes atomic with the worker's claim; never recreate a deleted target.
            GoogleCalendarSync.objects.filter(
                pk=sync.pk,
                user_id=sync.user_id,
                session_id=sync.session_id,
                created_at=sync.created_at,
                status=GoogleCalendarSync.Status.PENDING,
            ).update(status=GoogleCalendarSync.Status.FAILED, last_error=str(error), updated_at=now)
    return bool(updated)


def google_job_identity(value):
    if type(value) is UUID:
        return value
    if type(value) is not str or len(value) > 45:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


class GoogleJobInactive(Exception):
    """The claimed job can no longer authorize state changes or another send."""


def stop_inactive_google_job(function):
    @wraps(function)
    def run(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except GoogleJobInactive:
            return "inactive-job"

    return run


def _running_google_job(job):
    return AsyncJob.objects.filter(
        pk=job.pk,
        owner_id=job.owner_id,
        job_type=job.job_type,
        status=AsyncJob.Status.RUNNING,
        expires_at__gt=timezone.now(),
    )


def require_running_google_job(job):
    if not _running_google_job(job).exists():
        raise GoogleJobInactive


def _update_running_google_job(job, **values):
    if not _running_google_job(job).update(**values):
        raise GoogleJobInactive


def set_google_job_progress(job, progress):
    _update_running_google_job(job, progress=max(0, min(100, int(progress))))


def fail_google_job(job, error):
    _update_running_google_job(job, status=AsyncJob.Status.FAILED, error=str(error), finished_at=timezone.now())


def succeed_google_job(job, result):
    _update_running_google_job(
        job, status=AsyncJob.Status.SUCCEEDED, progress=100, result=result or {}, error="", finished_at=timezone.now()
    )


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
    try:
        job.refresh_from_db(fields=["status", "progress", "started_at", "finished_at", "error"])
    except AsyncJob.DoesNotExist:
        return False
    return True
