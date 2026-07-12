from celery import shared_task

from support.models import LineWebhookEvent


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_line_event_task(self, event_pk):
    from support.services import process_line_event

    event = LineWebhookEvent.objects.get(pk=event_pk)
    process_line_event(event.raw_payload)
