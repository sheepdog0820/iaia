"""Bind queued Google work to its requested connection without storing identities."""

import json

from django.utils.crypto import constant_time_compare, salted_hmac

from .google_tokens import google_credential_identity


def _connection_digest(integration, credential):
    if not integration or not credential:
        return None
    identity = {
        "integration": integration.pk,
        "user": integration.user_id,
        "connected_at": integration.connected_at.isoformat(),
        "credential": credential,
    }
    return salted_hmac(
        "schedules.google_connection.v1", json.dumps(identity, sort_keys=True), algorithm="sha256"
    ).hexdigest()


def google_connection_binding(integration):
    if not integration:
        return None
    return _connection_digest(integration, google_credential_identity(integration.user_id))


def google_job_connection_matches(job, integration, credential):
    if not isinstance(job.payload, dict):
        return False
    expected = job.payload.get("google_connection")
    current = _connection_digest(integration, credential)
    return isinstance(expected, str) and bool(current) and constant_time_compare(expected, current)


def google_sheet_values_binding(values):
    """Seal the queued table without retaining its private cell contents."""
    if not isinstance(values, list):
        return None
    if any(not isinstance(row, list) for row in values):
        return None
    if any(type(cell) not in (str, int, float, bool, type(None)) for row in values for cell in row):
        return None
    try:
        encoded = json.dumps(values, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError):
        return None
    return salted_hmac("schedules.google_sheet_values.v1", encoded, algorithm="sha256").hexdigest()


def google_job_values_match(job, values):
    if not isinstance(job.payload, dict):
        return False
    expected = job.payload.get("google_values")
    current = google_sheet_values_binding(values)
    return isinstance(expected, str) and bool(current) and constant_time_compare(expected, current)
