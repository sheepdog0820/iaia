"""FIFO shared holders, durable send boundaries, and no time-based unlock."""

import hmac
import re
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .google_write_ledger import InvalidGoogleWriteAdmission, _digest, _json, _material, open_google_write_snapshot
from .google_write_outcome import GoogleWriteUncertain, google_write_request
from .models import (
    AsyncJob,
    GoogleWriteAdmission,
    GoogleWriteExecution,
    GoogleWriteExecutionTarget,
    GoogleWriteRequest,
    GoogleWriteReservation,
    GoogleWriteTarget,
)

_scope = ContextVar("google_target_execution_scope", default=None)


def _execution_binding(execution, allocations):
    # Authenticate the independent journal, not just the mutable target marker.
    # It remains verifiable when source cleanup has removed the admission.
    return hmac.digest(
        _material(b"schedules.google_write.execution.targets.v1"),
        _json(
            [
                str(execution.pk),
                str(execution.job_id_snapshot),
                execution.admission_binding,
                execution.created_at.isoformat(),
                allocations,
            ]
        ),
        "sha256",
    ).hex()


def claim_targets(source, token):
    """Called under the source job lock, before RUNNING or delivery receipt."""
    row = GoogleWriteAdmission.objects.filter(job_id=source.pk).first()
    # Existing negative/legacy jobs still reach their original validation error;
    # only authenticated admission can acquire rights or authorize any HTTP.
    if row is None:
        return None
    try:
        if (source.owner_id, source.job_type, source.created_at) != (
            row.owner_id_snapshot,
            row.job_type_snapshot,
            row.job_created_at,
        ) or _digest(source.payload) != row.payload_digest:
            return None
        open_google_write_snapshot(row)
    except InvalidGoogleWriteAdmission:
        return None
    allocations = list(row.reservations.order_by("target_id").values_list("target_id", "sequence"))
    targets = [GoogleWriteTarget.objects.select_for_update().get(pk=key) for key, _ in allocations]
    now = timezone.now()
    for target, (_, sequence) in zip(targets, allocations):
        if target.last_started_sequence > sequence:
            source._google_sequence_retired = True
            return False
        if (
            target.active_execution_token
            or target.executions.exclude(execution__state=GoogleWriteExecution.State.FINISHED).exists()
        ):
            return False
        earlier = GoogleWriteReservation.objects.filter(
            target=target,
            sequence__lt=sequence,
            sequence__gt=target.last_started_sequence,
            admission__job__status__in=(AsyncJob.Status.QUEUED, AsyncJob.Status.RUNNING),
            admission__job__expires_at__gt=now,
        ).exclude(admission__job__payload__has_key="google_retry_successor")
        if earlier.exists():
            return False
    execution = GoogleWriteExecution(token=token, job_id_snapshot=source.pk, admission_binding=row.snapshot_binding)
    execution.allocation_binding = _execution_binding(execution, allocations)
    execution.save(force_insert=True)
    GoogleWriteExecutionTarget.objects.bulk_create(
        [GoogleWriteExecutionTarget(execution=execution, target_id=key, sequence=seq) for key, seq in allocations]
    )
    for target, (_, sequence) in zip(targets, allocations):
        target.active_execution_token = token
        target.last_started_sequence = sequence
        target.save(update_fields=["active_execution_token", "last_started_sequence"])
    return execution


def track_execution(job):
    jobs = _scope.get()
    if jobs is not None:
        jobs.append(job)


def _locked_execution(job):
    from .google_job_lifecycle import GoogleJobInactive

    allocations = list(
        GoogleWriteExecutionTarget.objects.filter(execution_id=job.execution_token)
        .order_by("target_id")
        .values_list("target_id", "sequence")
    )
    targets = [GoogleWriteTarget.objects.select_for_update().get(pk=key) for key, _ in allocations]
    execution = GoogleWriteExecution.objects.select_for_update().filter(token=job.execution_token).first()
    if (
        not 1 <= len(targets) <= 2
        or execution is None
        or execution.job_id_snapshot != job.pk
        or execution.state != GoogleWriteExecution.State.ACTIVE
        or any(
            target.active_execution_token != job.execution_token or target.last_started_sequence != sequence
            for target, (_, sequence) in zip(targets, allocations)
        )
    ):
        raise GoogleJobInactive
    try:
        if not re.fullmatch(r"[0-9a-f]{64}", execution.allocation_binding) or not hmac.compare_digest(
            execution.allocation_binding, _execution_binding(execution, allocations)
        ):
            raise GoogleJobInactive
    except InvalidGoogleWriteAdmission:
        raise GoogleJobInactive from None
    return execution, targets, allocations


@transaction.atomic
def require_execution(job):
    AsyncJob.objects.select_for_update().filter(pk=job.pk).first()
    execution, _, _ = _locked_execution(job)
    row = GoogleWriteAdmission.objects.filter(job_id=job.pk).first()
    from .google_job_lifecycle import GoogleJobInactive, require_running_google_job

    require_running_google_job(job)
    if row is None or row.snapshot_binding != execution.admission_binding:
        raise GoogleJobInactive


@transaction.atomic
def _begin_request(job, method, url, kwargs):
    from .google_job_lifecycle import GoogleJobInactive

    require_execution(job)
    execution, _, _ = _locked_execution(job)
    if execution.requests.exclude(state=GoogleWriteRequest.State.KNOWN).exists():
        raise GoogleJobInactive
    last = execution.requests.aggregate(value=Max("ordinal"))["value"] or 0
    digest = _digest([method, url, kwargs.get("json"), kwargs.get("params"), kwargs.get("headers", {}).get("If-Match")])
    return GoogleWriteRequest.objects.create(execution=execution, ordinal=last + 1, request_digest=digest)


@transaction.atomic
def _receive_request(job, request, status=None):
    # A response is evidence even after source cleanup/expiry, but an old or
    # forged token cannot change another holder or close its request boundary.
    AsyncJob.objects.select_for_update().filter(pk=job.pk).first()
    _locked_execution(job)
    from .google_job_lifecycle import GoogleJobInactive

    changed = GoogleWriteRequest.objects.filter(
        pk=request.pk, execution_id=job.execution_token, state=GoogleWriteRequest.State.INTENT
    ).update(
        state=GoogleWriteRequest.State.KNOWN if status is not None else GoogleWriteRequest.State.UNKNOWN,
        response_status=status,
        received_at=timezone.now(),
    )
    if not changed:
        raise GoogleJobInactive


def execution_write_request(job, method, send, url, **kwargs):
    request = _begin_request(job, method, url, kwargs)
    try:
        response = google_write_request(send, url, **kwargs)
    except GoogleWriteUncertain:
        _receive_request(job, request)
        raise
    _receive_request(job, request, response.status_code)
    return response


@transaction.atomic
def finish_execution(job):
    from .google_job_lifecycle import GoogleJobInactive

    source = AsyncJob.objects.select_for_update().filter(pk=job.pk).first()
    existing = GoogleWriteExecution.objects.filter(token=job.execution_token).first()
    if existing is None or existing.job_id_snapshot != job.pk or existing.state != GoogleWriteExecution.State.ACTIVE:
        return
    try:
        execution, targets, _ = _locked_execution(job)
    except GoogleJobInactive:
        # Inconsistent markers/allocation are not proof of a closed boundary.
        # Preserve this job's independent prohibition without masking the
        # worker's inactive result or ever unlocking someone else's holder.
        GoogleWriteExecution.objects.filter(
            token=job.execution_token, job_id_snapshot=job.pk, state=GoogleWriteExecution.State.ACTIVE
        ).update(state=GoogleWriteExecution.State.UNKNOWN)
        return
    known_terminal = (
        source is not None
        and source.execution_token == job.execution_token
        and source.status in (AsyncJob.Status.SUCCEEDED, AsyncJob.Status.FAILED)
        and not execution.requests.exclude(state=GoogleWriteRequest.State.KNOWN).exists()
    )
    if not known_terminal:
        execution.state = GoogleWriteExecution.State.UNKNOWN
        execution.save(update_fields=["state"])
        return
    execution.state = GoogleWriteExecution.State.FINISHED
    execution.closed_at = timezone.now()
    execution.save(update_fields=["state", "closed_at"])
    for target in targets:
        target.active_execution_token = None
        target.save(update_fields=["active_execution_token"])


@contextmanager
def execution_scope():
    jobs = []
    handle = _scope.set(jobs)
    try:
        yield
    finally:
        try:
            for job in jobs:
                finish_execution(job)
        finally:
            _scope.reset(handle)


def preserve_newer_calendar_pending(job, sync):
    """The caller holds source job then sorted target locks until sync save."""
    from .google_write_ledger import calendar_session_target_key

    execution = GoogleWriteExecution.objects.filter(token=job.execution_token).first()
    if execution is None:
        return False
    _, _, allocations = _locked_execution(job)
    sequence = dict(allocations).get(calendar_session_target_key(sync.user_id, sync.session_id))
    return (
        sequence is not None
        and GoogleWriteReservation.objects.filter(
            target_id=calendar_session_target_key(sync.user_id, sync.session_id),
            sequence__gt=sequence,
            admission__job__status__in=(AsyncJob.Status.QUEUED, AsyncJob.Status.RUNNING),
            admission__job__expires_at__gt=timezone.now(),
        ).exists()
    )
