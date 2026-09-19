from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.billing_email import dispatch_billing_emails
from accounts.models import BillingEmailDelivery


class Command(BaseCommand):
    help = "確定済みの課金失敗メールを配送・再試行します（送信設定の有効化が必要）。"

    def add_arguments(self, parser):
        parser.add_argument("--status", action="store_true", help="送信せず、配送待ち件数と最古の待機時刻を表示")

    def handle(self, *args, **options):
        if options["status"]:
            pending = BillingEmailDelivery.objects.filter(status="pending")
            self.stdout.write(
                str(
                    {
                        "enabled": getattr(settings, "BILLING_EMAIL_DELIVERY_ENABLED", False),
                        "pending": pending.count(),
                        "due": pending.filter(next_attempt_at__lte=timezone.now()).count(),
                        "oldest_pending_at": pending.order_by("created_at")
                        .values_list("created_at", flat=True)
                        .first(),
                    }
                )
            )
            return
        self.stdout.write(str(dispatch_billing_emails()))
