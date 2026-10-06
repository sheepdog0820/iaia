"""Immutable, transactional Google write admissions; worker integration follows."""

import base64
import hashlib
import hmac
import json
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from .google_job_lifecycle import GOOGLE_JOB_TYPES, google_retry_source_is_superseded
from .google_sheets import normalize_spreadsheet_id
from .models import AsyncJob, GoogleWriteAdmission, GoogleWriteReservation, GoogleWriteTarget

INVALID_ADMISSION_MESSAGE = "Googleの処理受付情報を確認できません。連携設定から新しく実行してください。"
_RESOURCE_KEY = re.compile(r"[0-9a-f]{64}")
_MAX_SEQUENCE = 2**63 - 1


class InvalidGoogleWriteAdmission(Exception):
    def __init__(self):
        super().__init__(INVALID_ADMISSION_MESSAGE)


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError):
        raise InvalidGoogleWriteAdmission from None


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def calendar_session_target_key(user_id, session_id):
    if any(type(value) is not int or not 0 < value < 2**63 for value in (user_id, session_id)):
        raise InvalidGoogleWriteAdmission
    return _digest(["google-write-target.v1", "calendar-session", user_id, session_id])


def calendar_event_target_key(account_uid, event_id):
    if any(type(value) is not str or not value for value in (account_uid, event_id)):
        raise InvalidGoogleWriteAdmission
    return _digest(["google-write-target.v1", "calendar-event", account_uid, "primary", event_id])


def sheet_target_key(spreadsheet_id):
    try:
        spreadsheet_id = normalize_spreadsheet_id(spreadsheet_id)
    except ValueError:
        raise InvalidGoogleWriteAdmission from None
    # Owner, credential, reconnect generation and A1 aliases never split a shared target.
    return _digest(["google-write-target.v1", "spreadsheet", spreadsheet_id])


def _material(purpose):
    try:
        secret = settings.SECRET_KEY
        if type(secret) is not str:
            raise InvalidGoogleWriteAdmission
        return hmac.digest(secret.encode("utf-8"), purpose, "sha256")
    except (ImproperlyConfigured, UnicodeError):
        raise InvalidGoogleWriteAdmission from None


def _snapshot_binding(snapshot):
    return hmac.digest(_material(b"schedules.google_write.snapshot.binding.v1"), _json(snapshot), "sha256").hex()


def _cipher():
    return AESGCM(_material(b"schedules.google_write.snapshot.envelope.v1"))


def _allocations(row):
    return list(row.reservations.order_by("target_id").values_list("target_id", "sequence"))


def _aad(row):
    return _json(
        [
            "google-write-admission.v1",
            str(row.pk),
            str(row.job_id),
            row.owner_id_snapshot,
            row.job_type_snapshot,
            row.job_created_at.isoformat(),
            row.created_at.isoformat(),
            row.payload_digest,
            row.allocation_digest,
            row.snapshot_binding,
        ]
    )


def open_google_write_snapshot(row):
    """Authenticate metadata and allocation rows; never repair a changed receipt."""
    if not isinstance(row, GoogleWriteAdmission) or row._state.adding:
        raise InvalidGoogleWriteAdmission
    allocations = _allocations(row)
    if not allocations or _digest(allocations) != row.allocation_digest:
        raise InvalidGoogleWriteAdmission
    try:
        if type(row.ciphertext) is not str or not row.ciphertext.startswith("v1."):
            raise InvalidGoogleWriteAdmission
        envelope = base64.b64decode(row.ciphertext[3:], validate=True)
        decoded = _cipher().decrypt(envelope[:12], envelope[12:], _aad(row))
        snapshot = json.loads(decoded)
        if type(snapshot) is not dict or not hmac.compare_digest(_snapshot_binding(snapshot), row.snapshot_binding):
            raise InvalidGoogleWriteAdmission
        return snapshot
    except (InvalidTag, AttributeError, TypeError, ValueError, UnicodeError):
        raise InvalidGoogleWriteAdmission from None


def _source(job):
    if not isinstance(job, AsyncJob):
        raise InvalidGoogleWriteAdmission
    source = (
        AsyncJob.objects.select_for_update()
        .only("id", "owner_id", "job_type", "created_at", "payload")
        .filter(
            pk=job.pk,
            owner_id=job.owner_id,
            job_type=job.job_type,
            created_at=job.created_at,
            status=AsyncJob.Status.QUEUED,
            started_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .first()
    )
    if (
        source is None
        or source.job_type not in GOOGLE_JOB_TYPES
        or not isinstance(source.payload, dict)
        or _digest(source.payload) != _digest(job.payload)
        or google_retry_source_is_superseded(source)
    ):
        raise InvalidGoogleWriteAdmission
    return source


@transaction.atomic
def register_google_write(job, resource_keys, snapshot):
    """Allocate committed FIFO sequences, no HTTP, no execution claim or permission grant.

    Internal callers must derive keys/snapshot from authorized immutable targets.
    Producers and worker do not use this foundation until their integration unit.
    """
    if (
        type(resource_keys) not in (list, tuple)
        or not 1 <= len(resource_keys) <= 2
        or any(type(key) is not str or not _RESOURCE_KEY.fullmatch(key) for key in resource_keys)
        or len(set(resource_keys)) != len(resource_keys)
        or type(snapshot) is not dict
    ):
        raise InvalidGoogleWriteAdmission
    keys = sorted(resource_keys)
    # Reject values whose JSON round-trip silently changes their meaning/type.
    encoded_snapshot = _json(snapshot)
    frozen_snapshot = json.loads(encoded_snapshot)
    if frozen_snapshot != snapshot:
        raise InvalidGoogleWriteAdmission
    binding = _snapshot_binding(frozen_snapshot)
    source = _source(job)
    payload_digest = _digest(source.payload)
    existing = GoogleWriteAdmission.objects.filter(job=source).first()
    if existing is not None:
        if (
            (existing.owner_id_snapshot, existing.job_type_snapshot, existing.job_created_at, existing.payload_digest)
            != (source.owner_id, source.job_type, source.created_at, payload_digest)
            or [key for key, _ in _allocations(existing)] != keys
            or open_google_write_snapshot(existing) != frozen_snapshot
        ):
            raise InvalidGoogleWriteAdmission
        return existing
    allocations = []
    # Source job first, targets in one global order. Never hold these locks over HTTP.
    for key in keys:
        GoogleWriteTarget.objects.get_or_create(resource_key=key)
        target = GoogleWriteTarget.objects.select_for_update().get(pk=key)
        if target.last_sequence >= _MAX_SEQUENCE:
            raise InvalidGoogleWriteAdmission
        target.last_sequence += 1
        target.save(update_fields=["last_sequence"])
        allocations.append((key, target.last_sequence))
    row = GoogleWriteAdmission(
        job=source,
        owner_id_snapshot=source.owner_id,
        job_type_snapshot=source.job_type,
        job_created_at=source.created_at,
        payload_digest=payload_digest,
        allocation_digest=_digest(allocations),
        snapshot_binding=binding,
    )
    nonce = os.urandom(12)
    row.ciphertext = "v1." + base64.b64encode(nonce + _cipher().encrypt(nonce, encoded_snapshot, _aad(row))).decode(
        "ascii"
    )
    row.save(force_insert=True)
    GoogleWriteReservation.objects.bulk_create(
        [GoogleWriteReservation(admission=row, target_id=key, sequence=sequence) for key, sequence in allocations]
    )
    return row
