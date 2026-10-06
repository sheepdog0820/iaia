"""Consume sealed producer intent; this is not a shared execution holder."""

from copy import deepcopy
from datetime import datetime

from .google_job_connection import google_job_values_match
from .google_job_lifecycle import GoogleJobInactive, fail_google_job, uncertain_google_job
from .google_write_intake import calendar_event_key
from .google_write_ledger import (
    INVALID_ADMISSION_MESSAGE,
    InvalidGoogleWriteAdmission,
    _digest,
    _json,
    calendar_event_target_key,
    calendar_session_target_key,
    open_google_write_snapshot,
    sheet_target_key,
)
from .models import AsyncJob, GoogleCalendarSync, GoogleWriteAdmission


def _credential_identity_is_valid(credential):
    return (
        type(credential) is dict
        and set(credential) == {"pk", "account_id", "app_id", "account__uid"}
        and all(type(credential[key]) is int and credential[key] > 0 for key in ("pk", "account_id"))
        and (credential["app_id"] is None or (type(credential["app_id"]) is int and credential["app_id"] > 0))
        and type(credential["account__uid"]) is str
        and bool(credential["account__uid"])
    )


def _require_calendar_event(event, sync, sync_key):
    if (
        type(event) is not dict
        or set(event) != {"summary", "description", "location", "start", "end", "status", "extendedProperties"}
        or any(type(event[field]) is not str for field in ("summary", "description", "location"))
        or event["status"] != "confirmed"
        or event["extendedProperties"]
        != {"private": {"tableno_session_id": str(sync.session_id), "tableno_sync_key": sync_key}}
    ):
        raise InvalidGoogleWriteAdmission
    for field in ("start", "end"):
        when = event[field]
        if type(when) is not dict or set(when) != {"dateTime"} or type(when["dateTime"]) is not str:
            raise InvalidGoogleWriteAdmission
        try:
            datetime.fromisoformat(when["dateTime"])
        except ValueError:
            raise InvalidGoogleWriteAdmission from None


def read_worker_snapshot(job, credential, sync=None):
    if not isinstance(job, AsyncJob) or not _credential_identity_is_valid(credential):
        raise InvalidGoogleWriteAdmission
    source = AsyncJob.objects.filter(pk=job.pk).first()
    row = GoogleWriteAdmission.objects.filter(job_id=job.pk).first()
    if (
        source is None
        or row is None
        or (source.owner_id, source.job_type, source.created_at)
        != (row.owner_id_snapshot, row.job_type_snapshot, row.job_created_at)
        or (source.owner_id, source.job_type, source.created_at) != (job.owner_id, job.job_type, job.created_at)
        or not isinstance(source.payload, dict)
        or _digest(source.payload) != row.payload_digest
    ):
        raise InvalidGoogleWriteAdmission
    snapshot = open_google_write_snapshot(row)
    calendar = source.job_type == "google_calendar_sync"
    if (
        source.job_type not in ("google_calendar_sync", "google_sheets_export")
        or set(snapshot)
        != (
            {"version", "kind", "google_connection", "credential", "sync", "calendar"}
            if calendar
            else {"version", "kind", "google_connection", "credential", "sheets"}
        )
        or type(snapshot["version"]) is not int
        or snapshot["version"] != 1
        or snapshot["kind"] != source.job_type
        or _json(snapshot["google_connection"]) != _json(source.payload.get("google_connection"))
        or _json(snapshot["credential"]) != _json(credential)
    ):
        raise InvalidGoogleWriteAdmission
    if calendar:
        if not isinstance(sync, GoogleCalendarSync):
            raise InvalidGoogleWriteAdmission
        current = GoogleCalendarSync.objects.filter(pk=sync.pk).first()
        expected_sync = {
            "id": sync.pk,
            "user_id": sync.user_id,
            "session_id": sync.session_id,
            "created_at": sync.created_at.isoformat(),
        }
        plan = snapshot["calendar"]
        if (
            current is None
            or (current.user_id, current.session_id, current.created_at)
            != (sync.user_id, sync.session_id, sync.created_at)
            or _json(snapshot["sync"]) != _json(expected_sync)
            or _json(source.payload.get("sync_id")) != _json(sync.pk)
            or source.owner_id != sync.user_id
            or type(plan) is not dict
            or set(plan) != {"calendar_id", "event_id", "sync_key", "known_event", "operation", "event"}
            or plan["calendar_id"] != "primary"
            or type(plan["known_event"]) is not bool
            or plan["sync_key"] != calendar_event_key(sync)
            or plan["operation"] not in ("upsert", "cancel")
            or (plan["operation"] == "cancel" and plan["event"] is not None)
            or (not plan["known_event"] and plan["event_id"] != plan["sync_key"])
            or (plan["known_event"] and current.external_event_id != plan["event_id"])
            or (not plan["known_event"] and current.external_event_id not in ("", plan["event_id"]))
        ):
            raise InvalidGoogleWriteAdmission
        event = plan["event"]
        if event is not None:
            _require_calendar_event(event, sync, plan["sync_key"])
        keys = [
            calendar_session_target_key(source.owner_id, sync.session_id),
            calendar_event_target_key(credential["account__uid"], plan["event_id"]),
        ]
    else:
        plan = snapshot["sheets"]
        if (
            type(plan) is not dict
            or set(plan) != {"spreadsheet_id", "range", "values"}
            or plan["spreadsheet_id"] != source.payload.get("spreadsheet_id")
            or plan["range"] != source.payload.get("range")
            or not google_job_values_match(source, plan["values"])
        ):
            raise InvalidGoogleWriteAdmission
        keys = [sheet_target_key(plan["spreadsheet_id"])]
    if sorted(keys) != list(row.reservations.order_by("target_id").values_list("target_id", flat=True)):
        raise InvalidGoogleWriteAdmission
    return snapshot


def prepare_worker_snapshot(job, credential, sync=None):
    snapshot = read_worker_snapshot(job, credential, sync)
    job._google_worker_snapshot = deepcopy(snapshot)
    job._google_worker_credential = deepcopy(credential)
    return snapshot


def require_worker_snapshot(job, sync=None, *, accepted_write=False):
    try:
        credential = getattr(job, "_google_worker_credential", None)
        expected = getattr(job, "_google_worker_snapshot", None)
        if _json(read_worker_snapshot(job, credential, sync)) != _json(expected):
            raise InvalidGoogleWriteAdmission
    except InvalidGoogleWriteAdmission:
        if accepted_write:
            uncertain_google_job(job)
        else:
            fail_google_job(job, INVALID_ADMISSION_MESSAGE)
        raise GoogleJobInactive from None
