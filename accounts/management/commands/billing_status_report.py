import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from accounts.models import PremiumAccessCodeRedemption, PremiumAuditLog, PremiumSubscription, StripeWebhookEvent

STALE_PROCESSING_WEBHOOK_MINUTES = 15
PROMO_EXPIRING_SOON_DAYS = 7


class Command(BaseCommand):
    help = "課金レコードとプレミアム権限の運用状態を集計します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="機械処理しやすいJSONで出力します。",
        )
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help="権限ずれまたは期限切れpromoがある場合にエラー終了します。",
        )
        parser.add_argument(
            "--include-payment-issues",
            action="store_true",
            help="--fail-on-issues時に支払い失敗と返金/チャージバック検知もエラー条件に含めます。",
        )

    def handle(self, *args, **options):
        report = build_billing_status_report()
        issues = build_issue_list(
            report,
            include_payment_issues=options["include_payment_issues"],
        )
        if options["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
            if options["fail_on_issues"] and issues:
                raise CommandError("billing_status_report issues: " + ", ".join(issues))
            return

        self.stdout.write(self.style.SUCCESS("billing_status_report=ok"))
        self.stdout.write(f'total_subscriptions={report["total_subscriptions"]}')
        self.stdout.write(f'active_access={report["active_access"]}')
        self.stdout.write(f'stripe_checkout_enabled={str(report["stripe_checkout_enabled"]).lower()}')
        self.stdout.write(f'expected_stripe_price_currency={report["expected_stripe_price_currency"] or "(none)"}')
        self.stdout.write(f'expected_monthly_unit_amount={report["expected_monthly_unit_amount"] or "(none)"}')
        self.stdout.write(f'expected_yearly_unit_amount={report["expected_yearly_unit_amount"] or "(none)"}')
        self.stdout.write(f'manual_override_users={report["manual_override_users"]}')
        self.stdout.write(f'manual_override_without_subscription={report["manual_override_without_subscription"]}')
        self.stdout.write(f'stale_user_flags={report["stale_user_flags"]}')
        self.stdout.write(f'expired_promo_records={report["expired_promo_records"]}')
        self.stdout.write(f'promo_indefinite_records={report["promo_indefinite_records"]}')
        self.stdout.write(f'promo_expiring_active_records={report["promo_expiring_active_records"]}')
        self.stdout.write(f'promo_expiring_soon_records={report["promo_expiring_soon_records"]}')
        self.stdout.write(f'cancel_at_period_end_records={report["cancel_at_period_end_records"]}')
        self.stdout.write("billing_intervals:")
        for interval, count in report["billing_intervals"].items():
            self.stdout.write(f'- {interval or "(blank)"}={count}')
        self.stdout.write(f'payment_failed_records={report["payment_failed_records"]}')
        self.stdout.write(f'refund_or_dispute_records={report["refund_or_dispute_records"]}')
        self.stdout.write(f'refund_or_dispute_active_records={report["refund_or_dispute_active_records"]}')
        self.stdout.write(f'last_webhook_event_id={report["last_webhook_event_id"] or "(none)"}')
        self.stdout.write(f'last_webhook_event_type={report["last_webhook_event_type"] or "(none)"}')
        self.stdout.write(f'last_webhook_processed_at={report["last_webhook_processed_at"] or "(none)"}')
        self.stdout.write(f'failed_webhook_events={report["failed_webhook_events"]}')
        self.stdout.write(f'processing_webhook_events={report["processing_webhook_events"]}')
        self.stdout.write(f'stale_processing_webhook_events={report["stale_processing_webhook_events"]}')
        self.stdout.write(f'last_failed_webhook_event_id={report["last_failed_webhook_event_id"] or "(none)"}')
        self.stdout.write(f'last_failed_webhook_event_type={report["last_failed_webhook_event_type"] or "(none)"}')
        self.stdout.write(
            f"last_stale_processing_webhook_event_id=" f'{report["last_stale_processing_webhook_event_id"] or "(none)"}'
        )
        self.stdout.write("statuses:")
        for status, count in report["statuses"].items():
            self.stdout.write(f'- {status or "(blank)"}={count}')
        self.stdout.write("promo_campaigns:")
        for campaign in report["promo_campaigns"]:
            self.stdout.write(
                "- {campaign_name}: total={total} active={active} "
                "expired={expired} expiring_soon={expiring_soon} "
                "indefinite={indefinite}".format(**campaign)
            )
        if issues:
            self.stdout.write(self.style.WARNING("issues:"))
            for issue in issues:
                self.stdout.write(self.style.WARNING(f"- {issue}"))
        if options["fail_on_issues"] and issues:
            raise CommandError("billing_status_report issues: " + ", ".join(issues))


def build_issue_list(report, *, include_payment_issues=False):
    issues = []
    if report["stale_user_flags"]:
        issues.append(f'stale_user_flags={report["stale_user_flags"]}')
    if report["expired_promo_records"]:
        issues.append(f'expired_promo_records={report["expired_promo_records"]}')
    if include_payment_issues and report["payment_failed_records"]:
        issues.append(f'payment_failed_records={report["payment_failed_records"]}')
    if include_payment_issues and report["refund_or_dispute_records"]:
        issues.append(f'refund_or_dispute_records={report["refund_or_dispute_records"]}')
    if include_payment_issues and report["refund_or_dispute_active_records"]:
        issues.append(f'refund_or_dispute_active_records={report["refund_or_dispute_active_records"]}')
    if include_payment_issues and report["failed_webhook_events"]:
        issues.append(f'failed_webhook_events={report["failed_webhook_events"]}')
    if include_payment_issues and report["stale_processing_webhook_events"]:
        issues.append(f'stale_processing_webhook_events={report["stale_processing_webhook_events"]}')
    return issues


def build_billing_status_report(now=None):
    now = now or timezone.now()
    records = PremiumSubscription.objects.select_related("user")
    total = records.count()
    statuses = {
        row["subscription_status"]: row["count"]
        for row in records.values("subscription_status").annotate(count=Count("id")).order_by("subscription_status")
    }

    active_access = 0
    stale_user_flags = 0
    for record in records:
        expected = record.expected_user_premium_access
        if expected:
            active_access += 1
        if record.user.is_premium != expected:
            stale_user_flags += 1
    manual_override_user_ids = get_manual_override_user_ids()
    subscription_user_ids = set(records.values_list("user_id", flat=True))
    manual_override_without_subscription_ids = manual_override_user_ids - subscription_user_ids
    manual_override_without_subscription = len(manual_override_without_subscription_ids)
    active_access += manual_override_without_subscription
    User = get_user_model()
    stale_user_flags += User.objects.filter(
        pk__in=manual_override_without_subscription_ids,
        is_premium=False,
    ).count()

    expired_promo_records = records.filter(
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source="promo_code",
        premium_expires_at__isnull=False,
        premium_expires_at__lte=now,
        revoked_at__isnull=True,
    ).count()
    promo_indefinite_records = records.filter(
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source="promo_code",
        premium_expires_at__isnull=True,
        revoked_at__isnull=True,
    ).count()
    promo_expiring_active_records = records.filter(
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source="promo_code",
        premium_expires_at__isnull=False,
        premium_expires_at__gt=now,
        revoked_at__isnull=True,
    ).count()
    promo_expiring_soon_records = records.filter(
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source="promo_code",
        premium_expires_at__isnull=False,
        premium_expires_at__gt=now,
        premium_expires_at__lte=now + timezone.timedelta(days=PROMO_EXPIRING_SOON_DAYS),
        revoked_at__isnull=True,
    ).count()
    promo_campaigns = build_promo_campaign_report(records, now)
    billing_intervals = {
        row["billing_interval"]: row["count"]
        for row in records.values("billing_interval").annotate(count=Count("id")).order_by("billing_interval")
    }

    last_webhook_event = StripeWebhookEvent.objects.order_by("-processed_at").first()
    failed_webhook_events = StripeWebhookEvent.objects.filter(
        processing_status=StripeWebhookEvent.STATUS_FAILED,
    )
    processing_webhook_events = StripeWebhookEvent.objects.filter(
        processing_status=StripeWebhookEvent.STATUS_PROCESSING,
    )
    stale_processing_cutoff = now - timezone.timedelta(
        minutes=STALE_PROCESSING_WEBHOOK_MINUTES,
    )
    stale_processing_webhook_events = processing_webhook_events.filter(
        processed_at__lte=stale_processing_cutoff,
    )
    last_failed_webhook_event = failed_webhook_events.order_by("-processed_at").first()
    last_stale_processing_webhook_event = stale_processing_webhook_events.order_by("-processed_at").first()

    return {
        "total_subscriptions": total,
        "active_access": active_access,
        "stripe_checkout_enabled": bool(getattr(settings, "STRIPE_CHECKOUT_ENABLED", False)),
        "expected_stripe_price_currency": getattr(
            settings,
            "STRIPE_PREMIUM_EXPECTED_CURRENCY",
            "",
        ),
        "expected_monthly_unit_amount": getattr(
            settings,
            "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT",
            "",
        ),
        "expected_yearly_unit_amount": getattr(
            settings,
            "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT",
            "",
        ),
        "manual_override_users": len(manual_override_user_ids),
        "manual_override_without_subscription": manual_override_without_subscription,
        "stale_user_flags": stale_user_flags,
        "expired_promo_records": expired_promo_records,
        "promo_indefinite_records": promo_indefinite_records,
        "promo_expiring_active_records": promo_expiring_active_records,
        "promo_expiring_soon_records": promo_expiring_soon_records,
        "promo_campaigns": promo_campaigns,
        "billing_intervals": billing_intervals,
        "cancel_at_period_end_records": records.filter(cancel_at_period_end=True).count(),
        "payment_failed_records": records.filter(last_payment_failed_at__isnull=False).count(),
        "refund_or_dispute_records": records.filter(last_refund_or_dispute_at__isnull=False).count(),
        "refund_or_dispute_active_records": sum(
            1
            for record in records
            if (record.last_refund_or_dispute_at is not None and record.expected_user_premium_access)
        ),
        "last_webhook_event_id": last_webhook_event.event_id if last_webhook_event else "",
        "last_webhook_event_type": last_webhook_event.event_type if last_webhook_event else "",
        "last_webhook_processed_at": (last_webhook_event.processed_at.isoformat() if last_webhook_event else ""),
        "failed_webhook_events": failed_webhook_events.count(),
        "processing_webhook_events": processing_webhook_events.count(),
        "stale_processing_webhook_events": stale_processing_webhook_events.count(),
        "last_failed_webhook_event_id": (last_failed_webhook_event.event_id if last_failed_webhook_event else ""),
        "last_failed_webhook_event_type": (last_failed_webhook_event.event_type if last_failed_webhook_event else ""),
        "last_stale_processing_webhook_event_id": (
            last_stale_processing_webhook_event.event_id if last_stale_processing_webhook_event else ""
        ),
        "statuses": statuses,
    }


def get_manual_override_user_ids():
    latest_manual_logs = {}
    logs = PremiumAuditLog.objects.filter(source="manual", action__in=("granted", "revoked")).order_by(
        "user_id", "-created_at", "-pk"
    )
    for log in logs:
        latest_manual_logs.setdefault(log.user_id, log.action)
    return {user_id for user_id, action in latest_manual_logs.items() if action == "granted"}


def build_promo_campaign_report(records, now):
    promo_records = list(
        records.filter(
            subscription_status=PremiumSubscription.PROMO_STATUS,
            access_source="promo_code",
        ).select_related("user")
    )
    if not promo_records:
        return []

    latest_redemptions = {}
    user_ids = [record.user_id for record in promo_records]
    redemptions = (
        PremiumAccessCodeRedemption.objects.select_related("access_code")
        .filter(user_id__in=user_ids)
        .order_by("user_id", "-redeemed_at")
    )
    for redemption in redemptions:
        latest_redemptions.setdefault(redemption.user_id, redemption)

    campaigns = {}
    for record in promo_records:
        redemption = latest_redemptions.get(record.user_id)
        raw_campaign_name = ""
        if redemption:
            raw_campaign_name = redemption.access_code.campaign_name
        campaign_name = raw_campaign_name or "(none)"
        row = campaigns.setdefault(
            campaign_name,
            {
                "campaign_name": campaign_name,
                "total": 0,
                "active": 0,
                "expired": 0,
                "expiring_soon": 0,
                "indefinite": 0,
            },
        )
        row["total"] += 1
        if record.revoked_at is not None:
            continue
        if record.premium_expires_at is None:
            row["active"] += 1
            row["indefinite"] += 1
        elif record.premium_expires_at <= now:
            row["expired"] += 1
        elif record.premium_expires_at <= now + timezone.timedelta(days=PROMO_EXPIRING_SOON_DAYS):
            row["active"] += 1
            row["expiring_soon"] += 1
        else:
            row["active"] += 1

    return [campaigns[name] for name in sorted(campaigns)]
