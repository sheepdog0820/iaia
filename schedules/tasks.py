from celery import shared_task
from django.utils import timezone
import requests
import logging

from accounts.models import DiscordDelivery, GroupDiscordSettings

from .handout_release import evaluate_release_conditions, publish_handout
from .models import AsyncJob, HandoutInfo

logger = logging.getLogger(__name__)


def queue_discord_event(group_id, event_type, payload, idempotency_key):
    if not group_id:
        return False
    settings_obj = GroupDiscordSettings.objects.filter(
        group_id=group_id,
        enabled=True,
    ).only('event_types').first()
    if not settings_obj or event_type not in settings_obj.event_types:
        return False
    try:
        send_discord_webhook.delay(
            group_id, event_type, payload, idempotency_key
        )
        return True
    except Exception:
        logger.exception('Unable to enqueue Discord webhook delivery.')
        return False


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
