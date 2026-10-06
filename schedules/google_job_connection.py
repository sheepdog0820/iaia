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
