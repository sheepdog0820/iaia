"""Durable Google delivery intent; publish ACK is not a worker receipt."""

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import timedelta
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .google_job_connection import google_job_values_match
from .google_job_lifecycle import fail_unstarted_google_dispatch, google_job_identity, google_retry_source_is_superseded
from .models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch

logger = logging.getLogger(__name__)
INVALID_DISPATCH_MESSAGE = "配送情報を確認できません。Google連携設定から新しく実行してください。"
CLAIM_WINDOW = timedelta(minutes=5)


class InvalidGoogleDispatch(Exception):
    """Never include the envelope, cells, key, or crypto exception in diagnostics."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload):
    return hashlib.sha256(_json(payload)).hexdigest()


def _cipher():
    key = hmac.digest(settings.SECRET_KEY.encode("utf-8"), b"schedules.google_dispatch.envelope.v1", "sha256")
    return AESGCM(key)


def _aad(row):
    return _json(
        [
            str(row.job_id),
            row.owner_id_snapshot,
            row.job_type_snapshot,
            row.job_created_at.isoformat(),
            row.payload_digest,
        ]
    )


def open_google_dispatch(row):
    try:
        if not isinstance(row.ciphertext, str) or not row.ciphertext.startswith("v1."):
            raise InvalidGoogleDispatch
        encoded = base64.b64decode(row.ciphertext[3:], validate=True)
        decoded = _cipher().decrypt(encoded[:12], encoded[12:], _aad(row))
        return json.loads(decoded)
    except (InvalidTag, ValueError, UnicodeError):
        raise InvalidGoogleDispatch from None


def _args_match(job, args):
    if type(args) is not list or not isinstance(job.payload, dict):
        return False
    if job.job_type == "google_calendar_sync":
        return (
            len(args) == 2
            and type(args[0]) is int
            and args[0] > 0
            and args[0] == job.payload.get("sync_id")
            and args[1] == str(job.pk)
        )
    if job.job_type == "google_sheets_export":
        return (
            len(args) == 5
            and args[0] == str(job.pk)
            and type(args[1]) is int
            and args[1] == job.owner_id
            and args[2] == job.payload.get("spreadsheet_id")
            and args[3] == job.payload.get("range")
            and google_job_values_match(job, args[4])
        )
    return False


@transaction.atomic
def persist_google_dispatch(job, args):
    if not _args_match(job, args):
        raise InvalidGoogleDispatch
    row = GoogleJobDispatch(
        job=job,
        owner_id_snapshot=job.owner_id,
        job_type_snapshot=job.job_type,
        job_created_at=job.created_at,
        payload_digest=_digest(job.payload),
    )
    nonce = os.urandom(12)
    row.ciphertext = "v1." + base64.b64encode(nonce + _cipher().encrypt(nonce, _json(args), _aad(row))).decode("ascii")
    existing, created = GoogleJobDispatch.objects.get_or_create(
        job=job,
        defaults={
            "id": row.pk,
            "owner_id_snapshot": row.owner_id_snapshot,
            "job_type_snapshot": row.job_type_snapshot,
            "job_created_at": row.job_created_at,
            "payload_digest": row.payload_digest,
            "ciphertext": row.ciphertext,
        },
    )
    if not created:
        if (
            existing.owner_id_snapshot,
            existing.job_type_snapshot,
            existing.job_created_at,
            existing.payload_digest,
        ) != (row.owner_id_snapshot, row.job_type_snapshot, row.job_created_at, row.payload_digest):
            raise InvalidGoogleDispatch
        if existing.ciphertext and open_google_dispatch(existing) != args:
            raise InvalidGoogleDispatch
    return existing


def _job_for_dispatch(row, now):
    job = AsyncJob.objects.filter(
        pk=row.job_id,
        owner_id=row.owner_id_snapshot,
        job_type=row.job_type_snapshot,
        created_at=row.job_created_at,
        status=AsyncJob.Status.QUEUED,
        started_at__isnull=True,
        expires_at__gt=now,
    ).first()
    if job is None or not isinstance(job.payload, dict) or _digest(job.payload) != row.payload_digest:
        return None
    if google_retry_source_is_superseded(job):
        return None
    if (
        job.job_type == "google_calendar_sync"
        and not GoogleCalendarSync.objects.filter(pk=job.payload.get("sync_id"), user_id=job.owner_id).exists()
    ):
        return None
    return job


@transaction.atomic
def _claim(job_id):
    now = timezone.now()
    row = GoogleJobDispatch.objects.select_for_update().filter(job_id=job_id).first()
    if row is None or row.state not in (GoogleJobDispatch.State.PENDING, GoogleJobDispatch.State.CLAIMED):
        return None
    if row.state == GoogleJobDispatch.State.CLAIMED:
        if row.claim_until is not None and row.claim_until > now:
            return None
    elif row.next_attempt_at > now:
        return None
    job = _job_for_dispatch(row, now)
    if job is None:
        row.state, row.ciphertext, row.claim_token, row.claim_until = GoogleJobDispatch.State.DISCARDED, "", None, None
        row.save(update_fields=["state", "ciphertext", "claim_token", "claim_until"])
        return None
    row.state = GoogleJobDispatch.State.CLAIMED
    row.claim_token = uuid4()
    row.claim_until = now + CLAIM_WINDOW
    row.attempt_count += 1
    row.save(update_fields=["state", "claim_token", "claim_until", "attempt_count"])
    return row, job


def _finish(row, **values):
    # A worker receipt or newer relay claim must never be undone by an old publisher.
    return GoogleJobDispatch.objects.filter(
        pk=row.pk, state=GoogleJobDispatch.State.CLAIMED, claim_token=row.claim_token
    ).update(claim_token=None, claim_until=None, **values)


def _can_publish(row):
    now = timezone.now()
    return (
        GoogleJobDispatch.objects.filter(
            pk=row.pk, state=GoogleJobDispatch.State.CLAIMED, claim_token=row.claim_token, claim_until__gt=now
        ).exists()
        and _job_for_dispatch(row, now) is not None
    )


def dispatch_google_job(job_id):
    job_id = google_job_identity(job_id)
    if job_id is None:
        return False
    claimed = _claim(job_id)
    if claimed is None:
        return False
    row, job = claimed
    try:
        args = open_google_dispatch(row)
        if not _args_match(job, args):
            raise InvalidGoogleDispatch
    except InvalidGoogleDispatch:
        fail_unstarted_google_dispatch(job, INVALID_DISPATCH_MESSAGE)
        _finish(row, state=GoogleJobDispatch.State.FAILED, ciphertext="")
        return False
    from .tasks import _publish_google_calendar_sync, _publish_google_sheet_export

    if not _can_publish(row):
        return False
    publish = _publish_google_calendar_sync if job.job_type == "google_calendar_sync" else _publish_google_sheet_export
    try:
        published = publish(*args) is True
    except Exception:
        logger.warning("Google durable dispatch could not confirm publication.")
        published = False
    now = timezone.now()
    values = {
        "state": GoogleJobDispatch.State.PENDING,
        "next_attempt_at": now
        + timedelta(seconds=60 if published else min(3600, 60 * 2 ** min(row.attempt_count - 1, 6))),
    }
    if published:
        values["published_at"] = now
    _finish(row, **values)
    return published


def dispatch_google_jobs(limit=100):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("配送件数は1〜1000の整数で指定してください。")
    now = timezone.now()
    due = Q(state=GoogleJobDispatch.State.PENDING, next_attempt_at__lte=now) | (
        Q(state=GoogleJobDispatch.State.CLAIMED) & (Q(claim_until__lte=now) | Q(claim_until__isnull=True))
    )
    jobs = list(
        GoogleJobDispatch.objects.filter(due).order_by("next_attempt_at", "pk").values_list("job_id", flat=True)[:limit]
    )
    return {"attempted": len(jobs), "published": sum(dispatch_google_job(job_id) for job_id in jobs)}
