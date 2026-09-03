from django.core.management.base import BaseCommand

from accounts.background_removal_tasks import cleanup_background_removal_jobs


class Command(BaseCommand):
    help = "期限切れの背景透過画像とジョブを削除します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除せず対象件数だけを表示します。",
        )

    def handle(self, *args, **options):
        summary = cleanup_background_removal_jobs(dry_run=options["dry_run"])
        prefix = "削除予定" if options["dry_run"] else "削除完了"
        timeout_label = "タイムアウト対象ジョブ" if options["dry_run"] else "タイムアウト処理ジョブ"
        self.stdout.write(f"{timeout_label}: {summary['timed_out_jobs']}件")
        self.stdout.write(f"{prefix}画像: {summary['deleted_result_images']}件")
        self.stdout.write(f"削除対象画像: {summary['expired_result_images']}件")
        self.stdout.write(f"{prefix}ジョブ: {summary['deleted_jobs']}件")
        self.stdout.write(f"削除対象ジョブ: {summary['expired_jobs']}件")
        self.stdout.write(f"削除失敗ジョブ: {summary['failed_jobs']}件")
