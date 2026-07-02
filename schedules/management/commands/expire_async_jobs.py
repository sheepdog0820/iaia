from django.core.management.base import BaseCommand, CommandError

from schedules.tasks import expire_async_jobs


class Command(BaseCommand):
    help = "Expire old async job records once without requiring Celery beat."

    def handle(self, *args, **options):
        try:
            deleted_count = expire_async_jobs()
        except Exception as exc:
            raise CommandError(f"Failed to expire async jobs: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Expired async jobs: deleted={deleted_count}"))
