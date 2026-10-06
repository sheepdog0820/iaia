from django.core.management.base import BaseCommand, CommandError

from schedules.google_dispatch_outbox import dispatch_google_jobs


class Command(BaseCommand):
    help = "Googleの永続配送待ちジョブを最大指定件数までキューへ投入します。"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        try:
            result = dispatch_google_jobs(limit=options["limit"])
        except ValueError:
            raise CommandError("配送件数は1〜1000の整数で指定してください。") from None
        self.stdout.write(f"対象 {result['attempted']} 件、投入確認 {result['published']} 件")
