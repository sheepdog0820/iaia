from celery import shared_task
from django.utils import timezone

from .models import AsyncJob


@shared_task(name='schedules.tasks.expire_async_jobs')
def expire_async_jobs():
    return AsyncJob.objects.filter(expires_at__lt=timezone.now()).delete()[0]


@shared_task(name='schedules.tasks.publish_scheduled_handouts')
def publish_scheduled_handouts():
    # The handout release evaluator is wired in when release conditions are added.
    return 0
