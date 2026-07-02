from django.core.management.base import BaseCommand, CommandError

from schedules.tasks import publish_scheduled_handouts


class Command(BaseCommand):
    help = "Publish eligible scheduled handouts once without requiring Celery beat."

    def handle(self, *args, **options):
        try:
            published_count = publish_scheduled_handouts()
        except Exception as exc:
            raise CommandError(f"Failed to publish scheduled handouts: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Published scheduled handouts: published={published_count}"))
