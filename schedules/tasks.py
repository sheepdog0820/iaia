import logging
import re
import socket
import uuid
from copy import deepcopy
from datetime import timedelta
from functools import partial
from urllib.parse import quote, urlparse

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import CharacterSheet, DiscordDelivery, GroupDiscordSettings

from .google_job_connection import google_connection_binding, google_job_connection_matches, google_job_values_match
from .google_job_lifecycle import (
    GoogleJobInactive,
    claim_google_job_start,
    fail_google_job,
    fail_unstarted_google_dispatch,
    google_job_can_start,
    google_job_identity,
    mark_stalled_google_jobs,
    require_running_google_job,
    set_google_job_progress,
    stop_inactive_google_job,
    succeed_google_job,
    uncertain_google_job,
)
from .google_sheets import (
    SHEETS_EXPORT_CHUNK_ROWS,
    normalize_sheet_start_range,
    normalize_spreadsheet_id,
    offset_sheet_start_range,
    sheet_export_character_ids,
    sheet_values_update_url,
)
from .google_tokens import get_google_access_token, google_credential_identity, google_credential_is_current
from .google_write_outcome import GoogleWriteUncertain, google_write_request
from .handout_release import evaluate_release_conditions, publish_handout
from .holiday_sync import sync_japanese_holidays as run_japanese_holiday_sync
from .integration_access import visible_user_sessions
from .models import AsyncJob, GoogleCalendarSync, GoogleIntegration, HandoutInfo

logger = logging.getLogger(__name__)
BACKGROUND_TASK_UNAVAILABLE_MESSAGE = "バックグラウンド処理を開始できませんでした。時間をおいて再試行してください。"
DISCORD_DELIVERY_FAILED_MESSAGE = "Discord通知の送信に失敗しました。設定を確認して再送してください。"
GOOGLE_CALENDAR_DELIVERY_FAILED_MESSAGE = (
    "Google Calendar APIとの通信に失敗しました。連携状態を確認して再試行してください。"
)
GOOGLE_CALENDAR_NOT_AUTHORIZED_MESSAGE = "Google Calendar連携が無効、またはセッションを同期する権限がありません。"
GOOGLE_CALENDAR_SYNC_CHANGED_MESSAGE = (
    "Google Calendarの同期情報が削除されたか変更されました。"
    "予定が変更されている可能性があるため、Google Calendarを確認してください。"
)
GOOGLE_SHEETS_DELIVERY_FAILED_MESSAGE = (
    "Google Sheets APIとの通信に失敗しました。連携状態と出力先を確認して再試行してください。"
)
GOOGLE_SHEETS_PARTIAL_DELIVERY_FAILED_MESSAGE = (
    "Google Sheets APIとの通信に失敗しました。途中まで出力されている可能性があります。"
    "連携状態と出力先を確認して再試行してください。"
)
GOOGLE_SHEETS_INVALID_RESPONSE_MESSAGE = "Google Sheetsの応答形式を確認できません。出力先を確認して再試行してください。"
GOOGLE_SHEETS_NOT_AUTHORIZED_MESSAGE = "Google Sheets連携が無効、または出力する権限がありません。"
GOOGLE_CONNECTION_CHANGED_MESSAGE = "Googleの連携設定が処理中に変更されました。接続先を確認して再試行してください。"
GOOGLE_JOB_CONNECTION_FAILED_MESSAGE = (
    "ジョブ作成時のGoogle接続先を確認できません。接続先を確認して再実行してください。"
)
GOOGLE_JOB_TARGET_FAILED_MESSAGE = "ジョブの処理対象が一致しません。連携設定から新しく実行してください。"
GOOGLE_JOB_VALUES_FAILED_MESSAGE = (
    "ジョブ作成時のGoogle Sheets出力内容を確認できません。連携設定から新しく出力してください。"
)
GOOGLE_SHEETS_SELECTION_FAILED_MESSAGE = "ジョブ作成時の出力対象を確認できません。連携設定から新しく出力してください。"
GOOGLE_SHEETS_CHARACTERS_CHANGED_MESSAGE = (
    "出力対象のキャラクターが削除されたか、所有者が変更されました。連携設定から新しく出力してください。"
)


def _same_google_connection(original, current):
    return (original.pk, original.connected_at) == (current.pk, current.connected_at)


def _google_sheets_export_integration(user_id):
    integration = GoogleIntegration.objects.filter(user_id=user_id, user__is_active=True, sheets_enabled=True).first()
    if integration and integration.has_scope(GoogleIntegration.REQUIRED_SHEETS_SCOPE):
        return integration
    return None


def _sheet_characters_are_owned(user_id, character_ids):
    return CharacterSheet.objects.filter(user_id=user_id, pk__in=character_ids).count() == len(character_ids)


def _broker_available():
    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    if not broker_url:
        return False
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True
    try:
        with socket.create_connection(
            (parsed.hostname, parsed.port or 6379),
            timeout=0.25,
        ):
            return True
    except OSError:
        return False


def queue_discord_event(group_id, event_type, payload, idempotency_key):
    if not group_id:
        return False
    settings_obj = (
        GroupDiscordSettings.objects.filter(
            group_id=group_id,
            enabled=True,
        )
        .only("event_types")
        .first()
    )
    if not settings_obj or event_type not in settings_obj.event_types:
        return False
    if not _broker_available():
        logger.warning("Discord delivery was not queued because the broker is unavailable.")
        return False
    try:
        send_discord_webhook.delay(group_id, event_type, payload, idempotency_key)
        return True
    except Exception:
        logger.exception("Unable to enqueue Discord webhook delivery.")
        return False


def _store_google_task_id(job_id, result):
    try:
        AsyncJob.objects.filter(pk=job_id).update(celery_task_id=result.id)
    except Exception:
        # Dispatch already returned successfully. Diagnostic ID storage is not delivery failure.
        logger.warning("Google task was published but its task ID could not be saved.")


def _publish_google_calendar_sync(sync_id, job_id):
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and not _broker_available():
        logger.warning("Google sync was not queued because the broker is unavailable.")
        return False
    try:
        result = sync_google_calendar.delay(sync_id, job_id)
    except Exception:
        logger.exception("Unable to enqueue Google Calendar synchronization.")
        return False
    _store_google_task_id(job_id, result)
    return True


def _publish_google_sheet_export(job_id, user_id, spreadsheet_id, range_name, values):
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and not _broker_available():
        logger.warning("Google Sheets export was not queued because the broker is unavailable.")
        return False
    try:
        result = export_google_sheet.delay(job_id, user_id, spreadsheet_id, range_name, values)
    except Exception:
        logger.exception("Unable to enqueue Google Sheets export.")
        return False
    _store_google_task_id(job_id, result)
    return True


def _queue_google_after_commit(job_id, publish, sync_id=None):
    """True/False confirms immediate dispatch; None means commit is still pending.

    This callback is not a durable outbox: process loss after commit still needs
    persistent recovery. Never publish a job that can disappear on rollback.
    """
    if not transaction.get_connection().in_atomic_block:
        if not transaction.get_autocommit():
            logger.warning("Google dispatch requires autocommit or an atomic transaction.")
            return False
        return publish()
    job = AsyncJob.objects.filter(pk=job_id).first()
    if job is None:
        return False
    sync = GoogleCalendarSync.objects.filter(pk=sync_id).first() if sync_id is not None else None

    def dispatch_committed_job():
        try:
            if not AsyncJob.objects.filter(
                pk=job.pk,
                owner_id=job.owner_id,
                job_type=job.job_type,
                status=AsyncJob.Status.QUEUED,
                started_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists():
                return
            if not publish():
                fail_unstarted_google_dispatch(job, BACKGROUND_TASK_UNAVAILABLE_MESSAGE, sync)
        except Exception:
            # Commit is already final. Do not turn a committed request into a 500
            # or log provider payloads/DB exceptions; a durable relay is still needed.
            logger.error("Unable to finish Google dispatch after database commit.")

    transaction.on_commit(dispatch_committed_job)
    return None


def queue_google_calendar_sync(sync_id, job_id):
    return _queue_google_after_commit(job_id, partial(_publish_google_calendar_sync, sync_id, job_id), sync_id)


def queue_google_sheet_export(job_id, user_id, spreadsheet_id, range_name, values):
    return _queue_google_after_commit(
        job_id, partial(_publish_google_sheet_export, job_id, user_id, spreadsheet_id, range_name, deepcopy(values))
    )


def schedule_session_google_syncs(session):
    user_ids = set(session.participants.values_list("id", flat=True))
    user_ids.add(session.gm_id)
    integrations = GoogleIntegration.objects.filter(
        user_id__in=user_ids,
        calendar_enabled=True,
    )
    for integration in integrations:
        if not integration.has_scope(GoogleIntegration.REQUIRED_CALENDAR_SCOPE):
            continue
        sync, _ = GoogleCalendarSync.objects.get_or_create(
            user_id=integration.user_id,
            session=session,
        )
        sync.status = GoogleCalendarSync.Status.PENDING
        sync.last_error = ""
        sync.save(update_fields=["status", "last_error", "updated_at"])
        job = AsyncJob.objects.create(
            owner_id=integration.user_id,
            job_type="google_calendar_sync",
            payload={"sync_id": sync.pk, "google_connection": google_connection_binding(integration)},
            expires_at=timezone.now() + timedelta(days=7),
        )
        if queue_google_calendar_sync(sync.pk, str(job.pk)) is False:
            fail_unstarted_google_dispatch(job, BACKGROUND_TASK_UNAVAILABLE_MESSAGE, sync)


@shared_task(name="schedules.tasks.expire_async_jobs")
def expire_async_jobs():
    mark_stalled_google_jobs(AsyncJob.objects.all())
    return AsyncJob.objects.filter(expires_at__lt=timezone.now()).delete()[0]


@shared_task(name="schedules.tasks.expire_premium_access")
def expire_premium_access():
    from accounts.billing import expire_promo_subscriptions

    return expire_promo_subscriptions()


@shared_task(name="schedules.tasks.publish_scheduled_handouts")
def publish_scheduled_handouts():
    published = 0
    handouts = HandoutInfo.objects.filter(
        release_status=HandoutInfo.ReleaseStatus.WAITING,
    ).select_related("session", "participant")
    for handout in handouts:
        if evaluate_release_conditions(handout):
            published += int(publish_handout(handout))
        else:
            from .handout_release import get_next_evaluation_at

            next_run = get_next_evaluation_at(handout.release_conditions)
            if next_run != handout.next_evaluation_at:
                handout.next_evaluation_at = next_run
                handout.save(update_fields=["next_evaluation_at", "updated_at"])
    return published


@shared_task(bind=True, max_retries=3, name="schedules.tasks.sync_japanese_holidays")
def sync_japanese_holidays(self):
    try:
        return run_japanese_holiday_sync()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3, name="schedules.tasks.send_discord_webhook")
def send_discord_webhook(self, group_id, event_type, payload, idempotency_key):
    try:
        settings_obj = GroupDiscordSettings.objects.get(
            group_id=group_id,
            enabled=True,
        )
    except GroupDiscordSettings.DoesNotExist:
        return "disabled"
    if event_type not in settings_obj.event_types:
        return "event-disabled"

    delivery, _ = DiscordDelivery.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "settings": settings_obj,
            "event_type": event_type,
            "payload": payload,
        },
    )
    if delivery.status == DiscordDelivery.Status.SENT:
        return "already-sent"

    delivery.attempts += 1
    delivery.save(update_fields=["attempts"])
    try:
        response = requests.post(
            settings_obj.get_webhook_url(),
            json=payload,
            timeout=10,
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise requests.RequestException(f"Discord returned {response.status_code}")
        response.raise_for_status()
    except requests.RequestException:
        delivery.status = DiscordDelivery.Status.FAILED
        delivery.last_error = DISCORD_DELIVERY_FAILED_MESSAGE
        delivery.save(update_fields=["status", "last_error"])
        settings_obj.failure_count += 1
        settings_obj.save(update_fields=["failure_count", "updated_at"])
        retry_error = requests.RequestException(DISCORD_DELIVERY_FAILED_MESSAGE)
        raise self.retry(exc=retry_error, countdown=min(60, 2**delivery.attempts)) from None

    delivery.status = DiscordDelivery.Status.SENT
    delivery.last_error = ""
    delivery.sent_at = timezone.now()
    delivery.save(update_fields=["status", "last_error", "sent_at"])
    if settings_obj.failure_count:
        settings_obj.failure_count = 0
        settings_obj.save(update_fields=["failure_count", "updated_at"])
    return "sent"


def _calendar_event_payload(session):
    start = session.date
    end = start + timedelta(minutes=session.duration_minutes or 180)
    return {
        "summary": session.title,
        "description": session.description,
        "location": session.location,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "status": "cancelled" if session.status == "cancelled" else "confirmed",
        "extendedProperties": {
            "private": {"tableno_session_id": str(session.pk)},
        },
    }


def _calendar_response_event(response):
    event = response.json()
    if not isinstance(event, dict):
        raise ValueError("Google Calendarの応答形式を確認できません。連携状態を確認してください。")
    return event


def _calendar_private_properties(event):
    properties = event.get("extendedProperties", {})
    if not isinstance(properties, dict):
        raise ValueError("Google Calendarの応答形式を確認できません。連携状態を確認してください。")
    return properties.get("private", {})


def _calendar_event_headers(response, event_id, sync_key, session_id, headers):
    event = _calendar_response_event(response)
    private = _calendar_private_properties(event)
    if event.get("id") != event_id or private != {
        "tableno_session_id": str(session_id),
        "tableno_sync_key": sync_key,
    }:
        raise ValueError("Google Calendarの予定IDが一致しません。連携状態を確認してください。")
    etag = event.get("etag")
    # One strong opaque ETag; never a wildcard, list, weak tag or injected header.
    if not isinstance(etag, str) or not re.fullmatch(r'"[\x21\x23-\x7e\x80-\xff]*"', etag):
        raise ValueError("Google Calendarの予定の更新情報を確認できません。連携状態を確認してください。")
    return {**headers, "If-Match": etag}


def _calendar_event_is_deleted(response, event_id):
    event = _calendar_response_event(response)
    return event.get("id") == event_id and event.get("status") == "cancelled"


class _GoogleCalendarNotAuthorized(Exception):
    pass


class _GoogleConnectionChanged(Exception):
    pass


def _current_calendar_sync(sync):
    return GoogleCalendarSync.objects.filter(
        pk=sync.pk, user_id=sync.user_id, session_id=sync.session_id, created_at=sync.created_at
    )


def _require_current_calendar_sync(sync, job):
    if not _current_calendar_sync(sync).exists():
        fail_google_job(job, GOOGLE_CALENDAR_SYNC_CHANGED_MESSAGE)
        raise GoogleJobInactive


def _save_current_calendar_sync(sync, job, fields):
    values = {field: getattr(sync, field) for field in fields if field != "updated_at"}
    values["updated_at"] = timezone.now()
    if not _current_calendar_sync(sync).update(**values):
        # Never recreate the target or overwrite a same-PK replacement. If the job
        # already failed, its original failure wins and the inactive guard stops retry.
        fail_google_job(job, GOOGLE_CALENDAR_SYNC_CHANGED_MESSAGE)
        raise GoogleJobInactive


def _google_calendar_sync_integration(sync):
    integration = GoogleIntegration.objects.filter(
        user_id=sync.user_id, user__is_active=True, calendar_enabled=True
    ).first()
    if (
        integration
        and integration.has_scope(GoogleIntegration.REQUIRED_CALENDAR_SCOPE)
        and visible_user_sessions(sync.user).filter(pk=sync.session_id).exists()
    ):
        return integration
    return None


def _calendar_request(job, sync, connection, credential, access_token, send, url, **kwargs):
    require_running_google_job(job)
    _require_current_calendar_sync(sync, job)
    current = _google_calendar_sync_integration(sync)
    if not current:
        raise _GoogleCalendarNotAuthorized
    if not _same_google_connection(connection, current) or not google_credential_is_current(
        sync.user_id, credential, access_token
    ):
        raise _GoogleConnectionChanged
    require_running_google_job(job)
    _require_current_calendar_sync(sync, job)
    if send is not requests.get:
        return google_write_request(send, url, **kwargs)
    return send(url, **kwargs)


def _calendar_conditional_request(*args, **kwargs):
    response = _calendar_request(*args, **kwargs)
    if response.status_code == 412:
        # Retrying against a freshly fetched version would overwrite the concurrent edit.
        raise ValueError("Google Calendarの予定が確認後に変更されました。予定を確認して再実行してください。")
    return response


def _fail_calendar_authorization(sync, job, error=GOOGLE_CALENDAR_NOT_AUTHORIZED_MESSAGE, result="not-authorized"):
    fail_google_job(job, error)
    sync.status = GoogleCalendarSync.Status.FAILED
    sync.last_error = error
    _save_current_calendar_sync(sync, job, ["status", "last_error", "updated_at"])
    return result


@shared_task(bind=True, max_retries=3, name="schedules.tasks.sync_google_calendar")
@stop_inactive_google_job
def sync_google_calendar(self, sync_id, job_id):
    if type(sync_id) is not int or not 0 < sync_id < 2**63:
        return "invalid-job"
    job_id = google_job_identity(job_id)
    if job_id is None:
        return "invalid-job"
    sync = GoogleCalendarSync.objects.select_related("session", "user").filter(pk=sync_id).first()
    if not sync:
        return "invalid-job"
    job = AsyncJob.objects.filter(pk=job_id, owner_id=sync.user_id, job_type="google_calendar_sync").first()
    if not job:
        # Never mutate a different owner's job or sync on malformed dispatch.
        return "invalid-job"
    if not google_job_can_start(job):
        return "inactive-job"
    if not claim_google_job_start(job):
        return "inactive-job"
    if (
        not isinstance(job.payload, dict)
        or type(job.payload.get("sync_id")) is not int
        or job.payload["sync_id"] != sync.pk
    ):
        fail_google_job(job, GOOGLE_JOB_TARGET_FAILED_MESSAGE)
        return "invalid-target"
    _require_current_calendar_sync(sync, job)
    connection = _google_calendar_sync_integration(sync)
    if not connection:
        return _fail_calendar_authorization(sync, job)
    set_google_job_progress(job, 10)
    credential = google_credential_identity(sync.user_id)
    if not google_job_connection_matches(job, connection, credential):
        return _fail_calendar_authorization(sync, job, GOOGLE_JOB_CONNECTION_FAILED_MESSAGE, "connection-changed")
    require_running_google_job(job)
    try:
        access_token = get_google_access_token(sync.user)
    except ValueError as exc:
        error = str(exc)
        fail_google_job(job, error)
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = error
        _save_current_calendar_sync(sync, job, ["status", "last_error", "updated_at"])
        return "missing-token"
    cancelling = sync.session.status == "cancelled"
    if sync.session.date is None and not cancelling:
        error = "開催日時が未設定のセッションはGoogle Calendarへ同期できません。"
        fail_google_job(job, error)
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = error
        _save_current_calendar_sync(sync, job, ["status", "last_error", "updated_at"])
        return "undated"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    base_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    generated_event_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"https://tableno.jp/calendar-sync/{sync.pk}/{sync.user_id}/{sync.session_id}/{sync.created_at.isoformat()}",
    ).hex
    write_accepted = False
    try:
        if sync.external_event_id in {".", ".."}:
            raise ValueError("Google Calendarの予定IDを確認できません。連携状態を確認してください。")
        if cancelling:
            event_id = sync.external_event_id or generated_event_id
            event_url = f"{base_url}/{quote(event_id, safe='')}"
            existing = _calendar_request(
                job, sync, connection, credential, access_token, requests.get, event_url, headers=headers, timeout=15
            )
            if existing.status_code not in {404, 410}:
                existing.raise_for_status()
                if not _calendar_event_is_deleted(existing, event_id):
                    conditional_headers = _calendar_event_headers(
                        existing, event_id, generated_event_id, sync.session_id, headers
                    )
                    response = _calendar_conditional_request(
                        job,
                        sync,
                        connection,
                        credential,
                        access_token,
                        requests.delete,
                        event_url,
                        headers=conditional_headers,
                        timeout=15,
                    )
                    if response.status_code not in {204, 404, 410}:
                        response.raise_for_status()
                sync.external_event_id = event_id
            sync.status = GoogleCalendarSync.Status.DELETED
        elif sync.external_event_id:
            event_url = f"{base_url}/{quote(sync.external_event_id, safe='')}"
            existing = _calendar_request(
                job, sync, connection, credential, access_token, requests.get, event_url, headers=headers, timeout=15
            )
            existing.raise_for_status()
            conditional_headers = _calendar_event_headers(
                existing, sync.external_event_id, generated_event_id, sync.session_id, headers
            )
            payload = _calendar_event_payload(sync.session)
            payload["extendedProperties"]["private"]["tableno_sync_key"] = generated_event_id
            response = _calendar_conditional_request(
                job,
                sync,
                connection,
                credential,
                access_token,
                requests.put,
                event_url,
                headers=conditional_headers,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            write_accepted = 200 <= response.status_code < 300
            if _calendar_response_event(response).get("id") != sync.external_event_id:
                raise ValueError("Google Calendarの予定IDが一致しません。連携状態を確認してください。")
            sync.status = GoogleCalendarSync.Status.SYNCED
        else:
            event_id = generated_event_id
            payload = _calendar_event_payload(sync.session)
            payload["id"] = event_id
            payload["extendedProperties"]["private"]["tableno_sync_key"] = event_id
            response = _calendar_request(
                job,
                sync,
                connection,
                credential,
                access_token,
                requests.post,
                base_url,
                headers=headers,
                json=payload,
                timeout=15,
            )
            if response.status_code == 409:
                existing = _calendar_request(
                    job,
                    sync,
                    connection,
                    credential,
                    access_token,
                    requests.get,
                    f"{base_url}/{event_id}",
                    headers=headers,
                    timeout=15,
                )
                existing.raise_for_status()
                conditional_headers = _calendar_event_headers(
                    existing, event_id, generated_event_id, sync.session_id, headers
                )
                response = _calendar_conditional_request(
                    job,
                    sync,
                    connection,
                    credential,
                    access_token,
                    requests.put,
                    f"{base_url}/{event_id}",
                    headers=conditional_headers,
                    json=payload,
                    timeout=15,
                )
            response.raise_for_status()
            write_accepted = 200 <= response.status_code < 300
            if _calendar_response_event(response).get("id") != event_id:
                raise ValueError("Google Calendarの予定IDが一致しません。連携状態を確認してください。")
            sync.external_event_id = event_id
            sync.status = GoogleCalendarSync.Status.SYNCED
    except GoogleWriteUncertain:
        return uncertain_google_job(job)
    except _GoogleCalendarNotAuthorized:
        return _fail_calendar_authorization(sync, job)
    except _GoogleConnectionChanged:
        return _fail_calendar_authorization(sync, job, GOOGLE_CONNECTION_CHANGED_MESSAGE, "connection-changed")
    except (requests.RequestException, KeyError, ValueError) as exc:
        if write_accepted:
            return uncertain_google_job(job)
        if isinstance(exc, requests.RequestException):
            error = GOOGLE_CALENDAR_DELIVERY_FAILED_MESSAGE
        elif isinstance(exc, KeyError):
            error = "Google Calendarの応答形式を確認できません。連携状態を確認してください。"
        else:
            error = str(exc)
        fail_google_job(job, error)
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = error
        _save_current_calendar_sync(sync, job, ["status", "last_error", "updated_at"])
        if isinstance(exc, requests.RequestException):
            retry_error = requests.RequestException(GOOGLE_CALENDAR_DELIVERY_FAILED_MESSAGE)
            raise self.retry(exc=retry_error, countdown=2**self.request.retries) from None
        return "invalid-response"

    sync.last_error = ""
    sync.synced_at = timezone.now()
    _save_current_calendar_sync(
        sync,
        job,
        [
            "external_event_id",
            "status",
            "last_error",
            "synced_at",
            "updated_at",
        ],
    )
    succeed_google_job(
        job,
        {
            "sync_id": sync.pk,
            "external_event_id": sync.external_event_id,
            "status": sync.status,
        },
    )
    return sync.status


@shared_task(bind=True, max_retries=3, name="schedules.tasks.export_google_sheet")
@stop_inactive_google_job
def export_google_sheet(
    self,
    job_id,
    user_id,
    spreadsheet_id,
    range_name,
    values,
):
    if type(user_id) is not int or not 0 < user_id < 2**63:
        return "invalid-job"
    job_id = google_job_identity(job_id)
    if job_id is None:
        return "invalid-job"
    job = AsyncJob.objects.filter(pk=job_id, owner_id=user_id, job_type="google_sheets_export").first()
    if not job:
        return "invalid-job"
    if not google_job_can_start(job):
        return "inactive-job"
    if not claim_google_job_start(job):
        return "inactive-job"
    connection = _google_sheets_export_integration(user_id)
    if not connection:
        fail_google_job(job, GOOGLE_SHEETS_NOT_AUTHORIZED_MESSAGE)
        return "not-authorized"
    set_google_job_progress(job, 10)
    try:
        spreadsheet_id = normalize_spreadsheet_id(spreadsheet_id)
    except ValueError as exc:
        fail_google_job(job, exc)
        return "invalid-spreadsheet"
    try:
        range_name = normalize_sheet_start_range(range_name)
    except ValueError as exc:
        fail_google_job(job, exc)
        return "invalid-range"
    credential = google_credential_identity(user_id)
    if not google_job_connection_matches(job, connection, credential):
        fail_google_job(job, GOOGLE_JOB_CONNECTION_FAILED_MESSAGE)
        return "connection-changed"
    if job.payload.get("spreadsheet_id") != spreadsheet_id or job.payload.get("range") != range_name:
        fail_google_job(job, GOOGLE_JOB_TARGET_FAILED_MESSAGE)
        return "invalid-target"
    if not google_job_values_match(job, values):
        fail_google_job(job, GOOGLE_JOB_VALUES_FAILED_MESSAGE)
        return "invalid-values"
    character_ids = sheet_export_character_ids(job.payload, values)
    if character_ids is None:
        fail_google_job(job, GOOGLE_SHEETS_SELECTION_FAILED_MESSAGE)
        return "invalid-selection"
    if not _sheet_characters_are_owned(user_id, character_ids):
        fail_google_job(job, GOOGLE_SHEETS_CHARACTERS_CHANGED_MESSAGE)
        return "characters-changed"
    require_running_google_job(job)
    try:
        access_token = get_google_access_token(job.owner)
    except ValueError as exc:
        fail_google_job(job, exc)
        return "missing-token"

    chunks = [
        values[index : index + SHEETS_EXPORT_CHUNK_ROWS] for index in range(0, len(values), SHEETS_EXPORT_CHUNK_ROWS)
    ]
    if not chunks:
        chunks = [[]]
    total_rows = len(values)
    completed_rows = 0
    updated_cells = 0
    for chunk in chunks:
        require_running_google_job(job)
        current = _google_sheets_export_integration(user_id)
        if (
            not current
            or not _same_google_connection(connection, current)
            or not google_credential_is_current(user_id, credential, access_token)
        ):
            changed = bool(current)
            error = GOOGLE_CONNECTION_CHANGED_MESSAGE if changed else GOOGLE_SHEETS_NOT_AUTHORIZED_MESSAGE
            if completed_rows:
                error += "途中まで出力されている可能性があります。出力先を確認してください。"
            fail_google_job(job, error)
            return "connection-changed" if changed else "not-authorized"
        if not _sheet_characters_are_owned(user_id, character_ids):
            error = GOOGLE_SHEETS_CHARACTERS_CHANGED_MESSAGE
            if completed_rows:
                error += "途中まで出力されている可能性があります。出力先を確認してください。"
            fail_google_job(job, error)
            return "characters-changed"
        chunk_range = offset_sheet_start_range(range_name, completed_rows)
        require_running_google_job(job)
        try:
            response = google_write_request(
                requests.put,
                sheet_values_update_url(spreadsheet_id, chunk_range),
                params={"valueInputOption": "RAW"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"majorDimension": "ROWS", "values": chunk},
                timeout=15,
            )
            response.raise_for_status()
        except GoogleWriteUncertain:
            return uncertain_google_job(job)
        except requests.RequestException:
            if completed_rows:
                # Earlier chunks are already acknowledged; replay would rewrite those cells.
                return uncertain_google_job(job)
            failure_message = (
                GOOGLE_SHEETS_PARTIAL_DELIVERY_FAILED_MESSAGE
                if completed_rows
                else GOOGLE_SHEETS_DELIVERY_FAILED_MESSAGE
            )
            fail_google_job(job, failure_message)
            retry_error = requests.RequestException(failure_message)
            raise self.retry(exc=retry_error, countdown=2**self.request.retries) from None
        try:
            result = response.json()
        except ValueError:
            result = None
        if not isinstance(result, dict):
            return uncertain_google_job(job)
        chunk_updated_cells = result.get("updatedCells", 0)
        if not isinstance(chunk_updated_cells, int) or isinstance(chunk_updated_cells, bool) or chunk_updated_cells < 0:
            return uncertain_google_job(job)
        updated_cells += chunk_updated_cells
        completed_rows += len(chunk)
        if total_rows:
            set_google_job_progress(job, 10 + int((completed_rows / total_rows) * 80))
    succeed_google_job(
        job,
        {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "updated_cells": updated_cells,
            "request_count": len(chunks),
        },
    )
    return "exported"
