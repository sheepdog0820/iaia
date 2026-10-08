"""Start Google delivery once at a time using existing job state."""

from datetime import timedelta
from functools import wraps
from uuid import UUID, uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, Q
from django.db.models.functions import Coalesce, Least
from django.utils import timezone

from .models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch

GOOGLE_JOB_TYPES = ("google_calendar_sync", "google_sheets_export")
GOOGLE_RETRY_SUCCESSOR_KEY = "google_retry_successor"
GOOGLE_RETRY_ALREADY_ACCEPTED_MESSAGE = (
    "このジョブは既に再試行を受け付けています。ジョブ一覧で新しい処理の結果を確認してください。"
)
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
        updated = (
            AsyncJob.objects.filter(
                pk=job.pk,
                owner_id=job.owner_id,
                job_type=job.job_type,
                status=AsyncJob.Status.QUEUED,
                started_at__isnull=True,
                expires_at__gt=now,
            )
            .exclude(payload__has_key=GOOGLE_RETRY_SUCCESSOR_KEY)
            .filter(~Exists(google_job_retry_successors(job)))
            .update(status=AsyncJob.Status.FAILED, error=str(error), finished_at=now)
        )
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


def google_job_retry_successors(job):
    """Recognize retained legacy successors as well as new manual retries."""
    return AsyncJob.objects.filter(owner_id=job.owner_id, job_type=job.job_type, payload__retry_of=str(job.pk)).exclude(
        pk=job.pk
    )


def google_retry_source_is_superseded(job):
    # Presence is fail-closed, including malformed markers. Consult current DB
    # state, not a worker's pre-acceptance payload snapshot or a deleted successor.
    return (
        AsyncJob.objects.filter(pk=job.pk, owner_id=job.owner_id, job_type=job.job_type)
        .filter(Q(payload__has_key=GOOGLE_RETRY_SUCCESSOR_KEY) | Q(Exists(google_job_retry_successors(job))))
        .exists()
    )


class GoogleJobInactive(Exception):
    """The claimed job can no longer authorize state changes or another send."""


class _GoogleStartRejected(Exception):
    """Rollback an acquired holder when the RUNNING update did not commit."""


def stop_inactive_google_job(function):
    @wraps(function)
    def run(*args, **kwargs):
        from .google_target_execution import execution_scope

        with execution_scope():
            try:
                return function(*args, **kwargs)
            except GoogleJobInactive:
                return "inactive-job"

    return run


def _running_google_job(job):
    now = timezone.now()
    return (
        _with_execution_start(
            AsyncJob.objects.filter(
                pk=job.pk,
                owner_id=job.owner_id,
                job_type=job.job_type,
                status=AsyncJob.Status.RUNNING,
                expires_at__gt=now,
                execution_token=job.execution_token,
            )
        )
        .exclude(_stalled_execution(now))
        .exclude(payload__has_key=GOOGLE_RETRY_SUCCESSOR_KEY)
        .filter(~Exists(google_job_retry_successors(job)))
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


def uncertain_google_job(job):
    _update_running_google_job(
        job,
        status=AsyncJob.Status.UNCERTAIN,
        error=GOOGLE_EXECUTION_UNCERTAIN_MESSAGE,
        finished_at=timezone.now(),
    )
    return "uncertain"


def succeed_google_job(job, result):
    from .google_target_execution import finish_execution

    with transaction.atomic():
        AsyncJob.objects.select_for_update().filter(pk=job.pk).first()
        _update_running_google_job(
            job,
            status=AsyncJob.Status.SUCCEEDED,
            progress=100,
            result=result or {},
            error="",
            finished_at=timezone.now(),
        )
        finish_execution(job)


def google_job_can_start(job):
    return (
        job.status in (AsyncJob.Status.QUEUED, AsyncJob.Status.FAILED)
        and job.expires_at > timezone.now()
        and not google_retry_source_is_superseded(job)
    )


@transaction.atomic
def claim_google_job_start(job):
    # Use the same source row as the retry API. A stale pre-lock FAILED read
    # cannot restart after another transaction has committed its successor.
    source = (
        AsyncJob.objects.select_for_update().filter(pk=job.pk, owner_id=job.owner_id, job_type=job.job_type).first()
    )
    if source is None or google_retry_source_is_superseded(source):
        return False
    if source.status not in (AsyncJob.Status.QUEUED, AsyncJob.Status.FAILED) or source.expires_at <= timezone.now():
        return False
    from .google_target_execution import claim_targets, finish_execution, track_execution

    token = uuid4()
    try:
        # Only the acquisition/start phase rolls back on a rejected update.
        # A later source deletion must not be undone to recreate that job.
        with transaction.atomic():
            execution = claim_targets(source, token)
            if execution is False:
                job._google_target_waiting = not getattr(source, "_google_sequence_retired", False)
                return False
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
                execution_token=token,
                execution_deadline=Least("expires_at", now + google_execution_window()),
            )
            if not updated:
                raise _GoogleStartRejected
    except _GoogleStartRejected:
        return False
    job.execution_token = token
    if execution is not None:
        track_execution(job)
    # Receipt and job claim are one commit: relay never republishes a started job.
    GoogleJobDispatch.objects.filter(job_id=job.pk).update(
        state=GoogleJobDispatch.State.DELIVERED, ciphertext="", claim_token=None, claim_until=None
    )
    try:
        job.refresh_from_db(
            fields=["status", "progress", "started_at", "finished_at", "error", "execution_token", "execution_deadline"]
        )
    except AsyncJob.DoesNotExist:
        if execution is not None:
            finish_execution(job)
        return False
    return True
