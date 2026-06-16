from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import requests
import logging
import socket
from django.conf import settings
from urllib.parse import urlparse

from accounts.models import DiscordDelivery, GroupDiscordSettings

from .google_tokens import get_google_access_token
from .handout_release import evaluate_release_conditions, publish_handout
from .models import (
    AsyncJob,
    GoogleCalendarSync,
    GoogleIntegration,
    HandoutInfo,
)

logger = logging.getLogger(__name__)


def _broker_available():
    broker_url = getattr(settings, 'CELERY_BROKER_URL', '')
    parsed = urlparse(broker_url)
    if parsed.scheme not in {'redis', 'rediss'}:
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
    settings_obj = GroupDiscordSettings.objects.filter(
        group_id=group_id,
        enabled=True,
    ).only('event_types').first()
    if not settings_obj or event_type not in settings_obj.event_types:
        return False
    if not _broker_available():
        logger.warning('Discord delivery was not queued because the broker is unavailable.')
        return False
    try:
        send_discord_webhook.delay(
            group_id, event_type, payload, idempotency_key
        )
        return True
    except Exception:
        logger.exception('Unable to enqueue Discord webhook delivery.')
        return False


def queue_google_calendar_sync(sync_id, job_id):
    if (
        not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
        and not _broker_available()
    ):
        logger.warning('Google sync was not queued because the broker is unavailable.')
        return False
    try:
        result = sync_google_calendar.delay(sync_id, job_id)
        AsyncJob.objects.filter(pk=job_id).update(celery_task_id=result.id)
        return True
    except Exception:
        logger.exception('Unable to enqueue Google Calendar synchronization.')
        return False


def queue_google_sheet_export(job_id, user_id, spreadsheet_id, range_name, values):
    if (
        not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
        and not _broker_available()
    ):
        logger.warning('Google Sheets export was not queued because the broker is unavailable.')
        return False
    try:
        result = export_google_sheet.delay(
            job_id, user_id, spreadsheet_id, range_name, values
        )
        AsyncJob.objects.filter(pk=job_id).update(celery_task_id=result.id)
        return True
    except Exception:
        logger.exception('Unable to enqueue Google Sheets export.')
        return False


def schedule_session_google_syncs(session):
    user_ids = set(session.participants.values_list('id', flat=True))
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
        sync.last_error = ''
        sync.save(update_fields=['status', 'last_error', 'updated_at'])
        job = AsyncJob.objects.create(
            owner_id=integration.user_id,
            job_type='google_calendar_sync',
            payload={'sync_id': sync.pk},
            expires_at=timezone.now() + timedelta(days=7),
        )
        if not queue_google_calendar_sync(sync.pk, str(job.pk)):
            job.mark_failed('Background task broker is unavailable.')
            sync.status = GoogleCalendarSync.Status.FAILED
            sync.last_error = 'Background task broker is unavailable.'
            sync.save(update_fields=['status', 'last_error', 'updated_at'])
@shared_task(name='schedules.tasks.expire_async_jobs')
def expire_async_jobs():
    return AsyncJob.objects.filter(expires_at__lt=timezone.now()).delete()[0]


@shared_task(name='schedules.tasks.publish_scheduled_handouts')
def publish_scheduled_handouts():
    published = 0
    handouts = HandoutInfo.objects.filter(
        release_status=HandoutInfo.ReleaseStatus.WAITING,
    ).select_related('session', 'participant')
    for handout in handouts:
        if evaluate_release_conditions(handout):
            published += int(publish_handout(handout))
        else:
            from .handout_release import get_next_evaluation_at
            next_run = get_next_evaluation_at(handout.release_conditions)
            if next_run != handout.next_evaluation_at:
                handout.next_evaluation_at = next_run
                handout.save(update_fields=['next_evaluation_at', 'updated_at'])
    return published


@shared_task(bind=True, max_retries=3, name='schedules.tasks.send_discord_webhook')
def send_discord_webhook(self, group_id, event_type, payload, idempotency_key):
    try:
        settings_obj = GroupDiscordSettings.objects.get(
            group_id=group_id,
            enabled=True,
        )
    except GroupDiscordSettings.DoesNotExist:
        return 'disabled'
    if event_type not in settings_obj.event_types:
        return 'event-disabled'

    delivery, _ = DiscordDelivery.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            'settings': settings_obj,
            'event_type': event_type,
            'payload': payload,
        },
    )
    if delivery.status == DiscordDelivery.Status.SENT:
        return 'already-sent'

    delivery.attempts += 1
    delivery.save(update_fields=['attempts'])
    try:
        response = requests.post(
            settings_obj.get_webhook_url(),
            json=payload,
            timeout=10,
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise requests.RequestException(f'Discord returned {response.status_code}')
        response.raise_for_status()
    except requests.RequestException as exc:
        delivery.status = DiscordDelivery.Status.FAILED
        delivery.last_error = str(exc)
        delivery.save(update_fields=['status', 'last_error'])
        settings_obj.failure_count += 1
        settings_obj.save(update_fields=['failure_count', 'updated_at'])
        raise self.retry(exc=exc, countdown=min(60, 2 ** delivery.attempts))

    delivery.status = DiscordDelivery.Status.SENT
    delivery.last_error = ''
    delivery.sent_at = timezone.now()
    delivery.save(update_fields=['status', 'last_error', 'sent_at'])
    if settings_obj.failure_count:
        settings_obj.failure_count = 0
        settings_obj.save(update_fields=['failure_count', 'updated_at'])
    return 'sent'


def _calendar_event_payload(session):
    start = session.date
    end = start + timedelta(minutes=session.duration_minutes or 180)
    return {
        'summary': session.title,
        'description': session.description,
        'location': session.location,
        'start': {'dateTime': start.isoformat()},
        'end': {'dateTime': end.isoformat()},
        'status': 'cancelled' if session.status == 'cancelled' else 'confirmed',
        'extendedProperties': {
            'private': {'tableno_session_id': str(session.pk)},
        },
    }


@shared_task(bind=True, max_retries=3, name='schedules.tasks.sync_google_calendar')
def sync_google_calendar(self, sync_id, job_id):
    sync = GoogleCalendarSync.objects.select_related('session', 'user').get(pk=sync_id)
    job = AsyncJob.objects.get(pk=job_id)
    job.mark_running(10)
    try:
        access_token = get_google_access_token(sync.user)
    except ValueError as exc:
        error = str(exc)
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = error
        sync.save(update_fields=['status', 'last_error', 'updated_at'])
        job.mark_failed(error)
        return 'missing-token'
    if sync.session.date is None:
        error = 'Undated sessions cannot be synchronized to Google Calendar.'
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = error
        sync.save(update_fields=['status', 'last_error', 'updated_at'])
        job.mark_failed(error)
        return 'undated'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    base_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    try:
        if sync.session.status == 'cancelled' and sync.external_event_id:
            response = requests.delete(
                f'{base_url}/{sync.external_event_id}',
                headers=headers,
                timeout=15,
            )
            if response.status_code not in {204, 404}:
                response.raise_for_status()
            sync.status = GoogleCalendarSync.Status.DELETED
        elif sync.external_event_id:
            response = requests.put(
                f'{base_url}/{sync.external_event_id}',
                headers=headers,
                json=_calendar_event_payload(sync.session),
                timeout=15,
            )
            response.raise_for_status()
            sync.status = GoogleCalendarSync.Status.SYNCED
        else:
            response = requests.post(
                base_url,
                headers=headers,
                json=_calendar_event_payload(sync.session),
                timeout=15,
            )
            response.raise_for_status()
            sync.external_event_id = response.json()['id']
            sync.status = GoogleCalendarSync.Status.SYNCED
    except (requests.RequestException, KeyError) as exc:
        sync.status = GoogleCalendarSync.Status.FAILED
        sync.last_error = str(exc)
        sync.save(update_fields=['status', 'last_error', 'updated_at'])
        job.mark_failed(exc)
        if isinstance(exc, requests.RequestException):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        return 'invalid-response'

    sync.last_error = ''
    sync.synced_at = timezone.now()
    sync.save(update_fields=[
        'external_event_id',
        'status',
        'last_error',
        'synced_at',
        'updated_at',
    ])
    job.mark_succeeded({
        'sync_id': sync.pk,
        'external_event_id': sync.external_event_id,
        'status': sync.status,
    })
    return sync.status


@shared_task(bind=True, max_retries=3, name='schedules.tasks.export_google_sheet')
def export_google_sheet(
    self,
    job_id,
    user_id,
    spreadsheet_id,
    range_name,
    values,
):
    job = AsyncJob.objects.get(pk=job_id, owner_id=user_id)
    job.mark_running(10)
    try:
        access_token = get_google_access_token(job.owner)
    except ValueError as exc:
        job.mark_failed(exc)
        return 'missing-token'
    try:
        response = requests.put(
            f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}',
            params={'valueInputOption': 'RAW'},
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json={'majorDimension': 'ROWS', 'values': values},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        job.mark_failed(exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    result = response.json()
    job.mark_succeeded({
        'spreadsheet_id': spreadsheet_id,
        'range': range_name,
        'updated_cells': result.get('updatedCells', 0),
    })
    return 'exported'
