"""Start Google delivery once at a time using existing job state."""

from datetime import timedelta
from functools import wraps
from uuid import UUID, uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce, Least
from django.utils import timezone

from .models import AsyncJob, GoogleCalendarSync

GOOGLE_JOB_TYPES = ("google_calendar_sync", "google_sheets_export")
GOOGLE_EXECUTION_UNCERTAIN_MESSAGE = (
    "処理結果を確認できません。Google側に反映されている可能性があります。"
    "重複を避けるため、再実行する前にGoogle CalendarまたはGoogle Sheetsの結果を確認してください。"
)


def google_execution_window():
    limit = getattr(settings, "CELERY_TASK_TIME_LIMIT", 900)
    if type(limit) is not int or limit <= 0:
        limit = 900
    # This is an execution bound, not proof that a worker or provider has stopped.
    return timedelta(seconds=max(900, limit) + 60)


def _stalled_execution(now):
    return Q(execution_deadline__lte=now) | Q(
        execution_deadline__isnull=True, execution_start__lte=now - google_execution_window()
    )


def _with_execution_start(queryset):
    return queryset.annotate(execution_start=Coalesce("started_at", "created_at"))


def mark_stalled_google_jobs(queryset):
    """Classify only the supplied scope; never send or make an uncertain job retryable."""
    now = timezone.now()
    stalled = (
        _with_execution_start(queryset)
        .filter(job_type__in=GOOGLE_JOB_TYPES, status=AsyncJob.Status.RUNNING)
        .filter(_stalled_execution(now))
    )
    if not stalled.exists():
        return 0
    # Re-evaluate the same predicate in UPDATE after any concurrent completion or claim.
    return stalled.update(status=AsyncJob.Status.UNCERTAIN, error=GOOGLE_EXECUTION_UNCERTAIN_MESSAGE, finished_at=now)


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
    now = timezone.now()
    return _with_execution_start(
        AsyncJob.objects.filter(
            pk=job.pk,
            owner_id=job.owner_id,
            job_type=job.job_type,
            status=AsyncJob.Status.RUNNING,
            expires_at__gt=now,
            execution_token=job.execution_token,
        )
    ).exclude(_stalled_execution(now))


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


def uncertain_google_job(job):
    _update_running_google_job(
        job,
        status=AsyncJob.Status.UNCERTAIN,
        error=GOOGLE_EXECUTION_UNCERTAIN_MESSAGE,
        finished_at=timezone.now(),
    )
    return "uncertain"


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
        execution_token=uuid4(),
        execution_deadline=Least("expires_at", now + google_execution_window()),
    )
    if not updated:
        return False
    try:
        job.refresh_from_db(
            fields=["status", "progress", "started_at", "finished_at", "error", "execution_token", "execution_deadline"]
        )
    except AsyncJob.DoesNotExist:
        return False
    return True
