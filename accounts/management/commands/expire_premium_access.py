from django.core.management.base import BaseCommand

from accounts.billing import expire_promo_subscriptions


class Command(BaseCommand):
    help = "期限切れの運営コード由来プレミアム権限を失効します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="変更せず、失効対象の件数だけ表示します。",
        )

    def handle(self, *args, **options):
        count = expire_promo_subscriptions(dry_run=options["dry_run"])
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"expired_premium_access_dry_run={count}"))
            return
        self.stdout.write(self.style.SUCCESS(f"expired_premium_access={count}"))
