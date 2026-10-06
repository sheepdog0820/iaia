"""Producer-side sealed acceptance; execution fencing is a separate protocol."""

import uuid
from datetime import timedelta

from django.db import transaction

from .google_job_connection import google_job_connection_matches, google_job_values_match
from .google_tokens import google_credential_identity
from .google_write_ledger import (
    InvalidGoogleWriteAdmission,
    calendar_event_target_key,
    calendar_session_target_key,
    register_google_write,
    sheet_target_key,
)
from .integration_access import visible_user_sessions
from .models import AsyncJob, GoogleIntegration


def calendar_event_key(sync):
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"https://tableno.jp/calendar-sync/{sync.pk}/{sync.user_id}/{sync.session_id}/{sync.created_at.isoformat()}",
    ).hex


def calendar_event_payload(session):
    start = session.date
    end = start + timedelta(minutes=session.duration_minutes or 180)
    return {
        "summary": session.title,
        "description": session.description,
        "location": session.location,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "status": "cancelled" if session.status == "cancelled" else "confirmed",
        "extendedProperties": {"private": {"tableno_session_id": str(session.pk)}},
    }


def _connection(job, kind):
    if not isinstance(job, AsyncJob) or not isinstance(job.payload, dict) or job.job_type != kind:
        raise InvalidGoogleWriteAdmission
    enabled, scope = {
        "google_calendar_sync": ("calendar_enabled", GoogleIntegration.REQUIRED_CALENDAR_SCOPE),
        "google_sheets_export": ("sheets_enabled", GoogleIntegration.REQUIRED_SHEETS_SCOPE),
    }[kind]
    integration = GoogleIntegration.objects.filter(
        user_id=job.owner_id, user__is_active=True, **{enabled: True}
    ).first()
    credential = google_credential_identity(job.owner_id)
    if (
        not integration
        or not isinstance(integration.scopes, list)
        or scope not in integration.scopes
        or not google_job_connection_matches(job, integration, credential)
    ):
        raise InvalidGoogleWriteAdmission
    return credential


@transaction.atomic
def register_calendar_intake(job, sync, session):
    credential = _connection(job, "google_calendar_sync")
    if (sync.user_id, sync.session_id, job.payload.get("sync_id")) != (
        job.owner_id,
        session.pk,
        sync.pk,
    ) or not visible_user_sessions(sync.user).filter(pk=session.pk).exists():
        raise InvalidGoogleWriteAdmission
    generated = calendar_event_key(sync)
    event_id = sync.external_event_id or generated
    cancelling = session.status == "cancelled"
    event = calendar_event_payload(session) if session.date is not None and not cancelling else None
    if event is not None:
        event["extendedProperties"]["private"]["tableno_sync_key"] = generated
    return register_google_write(
        job,
        [
            calendar_session_target_key(job.owner_id, session.pk),
            calendar_event_target_key(credential["account__uid"], event_id),
        ],
        {
            "version": 1,
            "kind": job.job_type,
            "google_connection": job.payload["google_connection"],
            "credential": credential,
            "sync": {
                "id": sync.pk,
                "user_id": sync.user_id,
                "session_id": sync.session_id,
                "created_at": sync.created_at.isoformat(),
            },
            "calendar": {
                "calendar_id": "primary",
                "event_id": event_id,
                "sync_key": generated,
                "known_event": bool(sync.external_event_id),
                "operation": "cancel" if cancelling else "upsert",
                "event": event,
            },
        },
    )


@transaction.atomic
def register_sheets_intake(job, values):
    credential = _connection(job, "google_sheets_export")
    if not google_job_values_match(job, values):
        raise InvalidGoogleWriteAdmission
    return register_google_write(
        job,
        [sheet_target_key(job.payload.get("spreadsheet_id"))],
        {
            "version": 1,
            "kind": job.job_type,
            "google_connection": job.payload["google_connection"],
            "credential": credential,
            "sheets": {
                "spreadsheet_id": job.payload["spreadsheet_id"],
                "range": job.payload["range"],
                "values": values,
            },
        },
    )
