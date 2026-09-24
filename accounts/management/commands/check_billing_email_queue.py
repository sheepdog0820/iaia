import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Min, Q
from django.utils import timezone

from accounts.models import BillingEmailDelivery


class Command(BaseCommand):
    help = "課金メールの配送設定・滞留を送信せずに検査し、異常時は終了コード1を返します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-pending-age-seconds",
            type=int,
            required=True,
            help="未配送の経過時間がこの秒数以上なら異常とする（正の整数）",
        )

    def handle(self, *args, **options):
        threshold = options["max_pending_age_seconds"]
        if threshold <= 0:
            raise CommandError("未配送時間の閾値には正の整数を指定してください。")
        now = timezone.now()
        counts = BillingEmailDelivery.objects.filter(status="pending").aggregate(
            pending=Count("pk"),
            due=Count("pk", filter=Q(next_attempt_at__lte=now)),
            overdue=Count("pk", filter=Q(created_at__lte=now - timedelta(seconds=threshold))),
            oldest=Min("created_at"),
        )
        oldest = counts.pop("oldest")
        enabled = getattr(settings, "BILLING_EMAIL_DELIVERY_ENABLED", False)
        healthy = enabled and counts["overdue"] == 0
        self.stdout.write(
            json.dumps(
                {
                    "healthy": healthy,
                    "enabled": enabled,
                    **counts,
                    "oldest_pending_age_seconds": max(0, int((now - oldest).total_seconds())) if oldest else None,
                    "max_pending_age_seconds": threshold,
                }
            )
        )
        if not healthy:
            raise CommandError("課金メール配送が無効、または未配送時間が閾値に達しています。")
