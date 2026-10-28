from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.billing import create_premium_audit_log, expire_promo_subscriptions
from accounts.models import PremiumSubscription


class Command(BaseCommand):
    help = "課金レコードを正としてユーザーのプレミアム権限を再同期します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="変更せず、同期対象件数だけ表示します。",
        )
        parser.add_argument(
            "--skip-expire",
            action="store_true",
            help="期限切れ運営コード由来プレミアムの失効処理をスキップします。",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        expired_count = 0
        if not options["skip_expire"] and not dry_run:
            expired_count = expire_promo_subscriptions()

        checked = 0
        changed = 0
        record_ids = PremiumSubscription.objects.order_by("pk").values_list("pk", flat=True)
        for record_id in record_ids.iterator():
            with transaction.atomic():
                records = PremiumSubscription.objects.all()
                if not dry_run:
                    records = records.select_for_update()
                record = records.filter(pk=record_id).first()
                if record is None:
                    continue
                # Load the user after acquiring the billing lock, not from a stale join.
                checked += 1
                expected = record.expected_user_premium_access
                current = record.user.is_premium
                if expected == current:
                    continue

                if not dry_run:
                    record.user.is_premium = expected
                    record.user.save(update_fields=["is_premium"])
                    create_premium_audit_log(
                        record.user,
                        action="granted" if expected else "revoked",
                        source=record.access_source,
                        reason="Premium access reconciled from billing record",
                        metadata={
                            "subscription_id": record.pk,
                            "subscription_status": record.subscription_status,
                            "dry_run": False,
                        },
                    )

            changed += 1
            self.stdout.write(
                f"{record.user.username}: is_premium {current} -> {expected} "
                f"({record.access_source}:{record.subscription_status})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"reconcile_premium_access=ok checked={checked} changed={changed} expired={expired_count}"
            )
        )
