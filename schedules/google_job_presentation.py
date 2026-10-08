"""Read-only, owner-safe status hints; never release a holder or authorize HTTP."""

from django.db.models import CharField, Exists, F, OuterRef, Q, Value
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Replace
from django.utils import timezone

from .google_job_lifecycle import GOOGLE_JOB_TYPES, GOOGLE_RETRY_SUCCESSOR_KEY
from .models import AsyncJob, GoogleWriteExecution, GoogleWriteExecutionTarget, GoogleWriteReservation

GOOGLE_EXECUTION_REVIEW_MESSAGE = (
    "この処理の結果を確認できないため、再試行できません。Google側の反映結果を確認してください。"
)
STATUS_MESSAGES = {
    "queued": "処理を受け付けています。進捗と結果はジョブ履歴で確認してください。",
    "target_waiting": (
        "同じ対象への先行処理を待っています。重複を避けるため、同じ操作を繰り返さず、"
        "履歴を更新して状態を確認してください。"
    ),
    "running": "処理中です。進捗と結果はジョブ履歴で確認してください。",
    "succeeded": "処理が完了しました。",
    "failed": "処理に失敗しました。下記の案内と連携状態を確認してください。",
    "uncertain": GOOGLE_EXECUTION_REVIEW_MESSAGE,
    "needs_review": GOOGLE_EXECUTION_REVIEW_MESSAGE,
    "expired": "このジョブの受付期限が切れています。Google側の結果と連携状態を確認してください。",
    "superseded": "このジョブは後続の処理に引き継がれています。ジョブ履歴で新しい処理の結果を確認してください。",
    "unknown": "このジョブの状態を確認できません。履歴を更新して状態を確認してください。",
}
ANNOTATIONS = (
    "_google_ui_unresolved",
    "_google_ui_review",
    "_google_ui_superseded",
    "_google_ui_retired",
    "_google_ui_waiting",
)


def google_job_has_unresolved_execution(job):
    # The retry API calls this under the same source row lock used by worker
    # acquisition/finalization. FAILED alone is not proof that HTTP has ended.
    return (
        GoogleWriteExecution.objects.filter(job_id_snapshot=job.pk)
        .exclude(state=GoogleWriteExecution.State.FINISHED)
        .exists()
    )


def annotate_google_job_presentation(queryset):
    """Evaluate job and journal hints in one SQL snapshot, without per-row reads."""
    own_execution = GoogleWriteExecution.objects.filter(job_id_snapshot=OuterRef("pk")).exclude(
        state=GoogleWriteExecution.State.FINISHED
    )
    reservations = GoogleWriteReservation.objects.filter(admission__job_id=OuterRef("pk"))
    earlier = GoogleWriteReservation.objects.filter(
        target_id=OuterRef("target_id"),
        sequence__lt=OuterRef("sequence"),
        sequence__gt=OuterRef("target__last_started_sequence"),
        admission__job__status__in=(AsyncJob.Status.QUEUED, AsyncJob.Status.RUNNING),
        admission__job__expires_at__gt=timezone.now(),
    ).exclude(admission__job__payload__has_key=GOOGLE_RETRY_SUCCESSOR_KEY)
    holders = GoogleWriteExecutionTarget.objects.filter(target_id=OuterRef("target_id")).exclude(
        execution__state=GoogleWriteExecution.State.FINISHED
    )
    waiting = reservations.filter(
        Q(target__active_execution_token__isnull=False) | Q(Exists(holders)) | Q(Exists(earlier))
    )
    # UUID columns are stored without hyphens on SQLite and with hyphens on PG.
    # Normalize only the representation for retained legacy retry_of receipts.
    successors = (
        AsyncJob.objects.annotate(
            _retry_source=Replace(
                KeyTextTransform("retry_of", "payload"), Value("-"), Value(""), output_field=CharField()
            )
        )
        .filter(
            owner_id=OuterRef("owner_id"),
            job_type=OuterRef("job_type"),
            _retry_source=Replace(Cast(OuterRef("pk"), CharField()), Value("-"), Value("")),
        )
        .exclude(pk=OuterRef("pk"))
    )
    return queryset.annotate(
        _google_ui_unresolved=Exists(own_execution),
        _google_ui_review=Exists(own_execution.exclude(state=GoogleWriteExecution.State.ACTIVE)),
        _google_ui_superseded=Exists(successors),
        _google_ui_retired=Exists(reservations.filter(sequence__lt=F("target__last_started_sequence"))),
        _google_ui_waiting=Exists(waiting),
    )


def google_job_presentation(job):
    cached = getattr(job, "_google_presentation", None)
    if cached is not None:
        return cached
    is_google = job.job_type in GOOGLE_JOB_TYPES
    if is_google and not hasattr(job, ANNOTATIONS[0]):
        # Direct serializer callers still use a single read for all hints.
        hints = annotate_google_job_presentation(AsyncJob.objects.filter(pk=job.pk)).values(*ANNOTATIONS).first()
        if hints is None:
            return {"display_state": "unknown", "status_message": STATUS_MESSAGES["unknown"], "can_retry": False}
        for key, value in hints.items():
            setattr(job, key, value)
    state = job.status if job.status in AsyncJob.Status.values else "unknown"
    if is_google:
        if job._google_ui_review or (job._google_ui_unresolved and state != "running"):
            state = "needs_review"
        elif state in ("queued", "failed"):
            if not isinstance(job.payload, dict):
                state = "unknown"
            elif job.expires_at <= timezone.now():
                state = "expired"
            elif GOOGLE_RETRY_SUCCESSOR_KEY in job.payload or job._google_ui_superseded or job._google_ui_retired:
                state = "superseded"
            elif state == "queued" and job._google_ui_waiting:
                state = "target_waiting"
    job._google_presentation = {
        "display_state": state,
        "status_message": STATUS_MESSAGES[state],
        # A lifecycle hint, not permission. The retry API rechecks connection,
        # authorization, source existence, and current journal under its lock.
        "can_retry": is_google and state == "failed",
    }
    return job._google_presentation
