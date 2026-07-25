from django.core.management.base import BaseCommand, CommandError

from accounts.background_removal_tasks import process_background_removal_job


class Command(BaseCommand):
    help = "Process one persisted character portrait background-removal job."

    def add_arguments(self, parser):
        parser.add_argument("job_id")

    def handle(self, *args, **options):
        try:
            job = process_background_removal_job(options["job_id"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        if job.status != job.Status.COMPLETED:
            raise CommandError(job.error_message or "Background removal failed.")
        self.stdout.write(self.style.SUCCESS(f"Background removal job {job.pk} completed."))
