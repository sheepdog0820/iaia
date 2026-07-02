from django.core.management.base import BaseCommand, CommandError

from schedules.holiday_sync import JapaneseHolidaySyncError, sync_japanese_holidays


class Command(BaseCommand):
    help = "Sync Japanese public holidays from the Cabinet Office CSV into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=None,
            help="Override the Japanese holiday CSV URL.",
        )

    def handle(self, *args, **options):
        try:
            result = sync_japanese_holidays(url=options.get("url"))
        except JapaneseHolidaySyncError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Failed to sync Japanese holidays: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Synced Japanese holidays: "
                f'created={result["created"]}, '
                f'updated={result["updated"]}, '
                f'deleted_stale={result["deleted_stale"]}, '
                f'total={result["total"]}, '
                f'source={result["source_url"]}'
            )
        )
