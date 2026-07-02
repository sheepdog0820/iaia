from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.billing import (
    handle_checkout_completed,
    mark_invoice_payment_failed,
    mark_invoice_payment_succeeded,
    mark_refund_or_dispute,
    sync_subscription_object,
)
from accounts.models import PremiumAuditLog, PremiumSubscription


class Command(BaseCommand):
    help = "Stripe Webhookで受ける主要な購読状態遷移をローカルDB上で検証します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="billing-smoke-user",
            help="スモーク確認に使うテストユーザー名。",
        )
        parser.add_argument(
            "--email",
            default="billing-smoke@example.com",
            help="スモーク確認に使うテストユーザーのメールアドレス。",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=options["username"],
            defaults={"email": options["email"]},
        )
        if not user.email:
            user.email = options["email"]
            user.save(update_fields=["email"])

        customer_id = f"cus_smoke_{user.pk}"
        subscription_id = f"sub_smoke_{user.pk}"
        record, _ = PremiumSubscription.objects.update_or_create(
            user=user,
            defaults={
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_status": "",
                "access_source": "stripe",
                "current_period_end": None,
                "cancel_at_period_end": False,
                "premium_expires_at": None,
                "revoked_at": None,
                "revoked_reason": "",
            },
        )

        now = int(timezone.now().timestamp())
        monthly_price = {
            "id": "price_smoke_monthly",
            "recurring": {"interval": "month"},
        }
        yearly_price = {
            "id": "price_smoke_yearly",
            "recurring": {"interval": "year"},
        }
        checkout_record = handle_checkout_completed(
            {
                "id": "cs_smoke_checkout_completed",
                "client_reference_id": str(user.pk),
                "customer": customer_id,
                "subscription": {
                    "id": subscription_id,
                    "customer": customer_id,
                    "status": "active",
                    "current_period_end": now + 3600,
                    "cancel_at_period_end": False,
                },
            },
            event_id="evt_smoke_checkout_completed",
        )
        if checkout_record.stripe_customer_id != customer_id:
            raise AssertionError("checkout.session.completed did not link customer")
        if checkout_record.stripe_subscription_id != subscription_id:
            raise AssertionError("checkout.session.completed did not link subscription")
        self._assert_state(checkout_record, expected_premium=True, label="checkout.session.completed")

        active_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
                "items": {"data": [{"price": monthly_price}]},
            },
            event_id="evt_smoke_subscription_active",
        )
        self._assert_state(active_record, expected_premium=True, label="subscription.active")
        self._assert_billing_plan(
            active_record,
            expected_price_id="price_smoke_monthly",
            expected_interval="month",
            label="subscription.active",
        )

        canceling_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": True,
                "items": {"data": [{"price": monthly_price}]},
            },
            event_id="evt_smoke_subscription_canceling",
        )
        self._assert_state(canceling_record, expected_premium=True, label="subscription.cancel_at_period_end")
        if not canceling_record.cancel_at_period_end:
            raise AssertionError("cancel_at_period_end was not recorded")
        self._assert_billing_plan(
            canceling_record,
            expected_price_id="price_smoke_monthly",
            expected_interval="month",
            label="subscription.cancel_at_period_end",
        )

        yearly_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 31536000,
                "cancel_at_period_end": False,
                "items": {"data": [{"price": yearly_price}]},
            },
            event_id="evt_smoke_subscription_yearly_active",
        )
        self._assert_state(yearly_record, expected_premium=True, label="subscription.yearly_active")
        self._assert_billing_plan(
            yearly_record,
            expected_price_id="price_smoke_yearly",
            expected_interval="year",
            label="subscription.yearly_active",
        )

        failed_record = mark_invoice_payment_failed(
            {"id": "in_smoke_failed", "customer": customer_id},
            event_id="evt_smoke_invoice_payment_failed",
        )
        if failed_record.last_payment_failed_at is None:
            raise AssertionError("invoice.payment_failed was not recorded")
        self.stdout.write(self.style.SUCCESS("OK invoice.payment_failed"))

        succeeded_record = mark_invoice_payment_succeeded(
            {"id": "in_smoke_succeeded", "customer": customer_id},
            event_id="evt_smoke_invoice_payment_succeeded",
        )
        if succeeded_record.last_payment_failed_at is not None:
            raise AssertionError("invoice.payment_succeeded did not clear payment failure")
        self.stdout.write(self.style.SUCCESS("OK invoice.payment_succeeded"))

        unpaid_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "unpaid",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_unpaid",
        )
        self._assert_state(unpaid_record, expected_premium=False, label="subscription.unpaid")

        deleted_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "canceled",
                "current_period_end": now,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_deleted",
        )
        self._assert_state(deleted_record, expected_premium=False, label="subscription.deleted")

        refundable_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_refundable_active",
        )
        self._assert_state(refundable_record, expected_premium=True, label="subscription.active.before_refund")

        refund_record = mark_refund_or_dispute(
            {"id": "ch_smoke_refunded", "customer": customer_id},
            event_type="charge.refunded",
            event_id="evt_smoke_charge_refunded",
        )
        if refund_record.last_refund_or_dispute_at is None:
            raise AssertionError("charge.refunded was not recorded")
        self._assert_state(refund_record, expected_premium=False, label="charge.refunded")
        self.stdout.write(self.style.SUCCESS("OK charge.refunded"))

        post_refund_active_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_active_after_refund",
        )
        if post_refund_active_record.revoked_at is None:
            raise AssertionError("refund revocation was cleared by active subscription update")
        self._assert_state(
            post_refund_active_record,
            expected_premium=False,
            label="subscription.active_after_refund",
        )

        # Simulate an administrator reviewing the refund and restoring access before a dispute.
        post_refund_active_record.revoked_at = None
        post_refund_active_record.revoked_reason = ""
        post_refund_active_record.save(update_fields=["revoked_at", "revoked_reason", "updated_at"])
        restored_before_dispute_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_active_before_dispute",
        )
        self._assert_state(
            restored_before_dispute_record,
            expected_premium=True,
            label="subscription.active.before_dispute",
        )

        dispute_record = mark_refund_or_dispute(
            {"id": "dp_smoke_disputed", "charge": "ch_smoke_disputed", "customer": customer_id},
            event_type="charge.dispute.created",
            event_id="evt_smoke_charge_dispute_created",
        )
        if dispute_record.last_refund_or_dispute_at is None:
            raise AssertionError("charge.dispute.created was not recorded")
        self._assert_state(dispute_record, expected_premium=False, label="charge.dispute.created")
        self.stdout.write(self.style.SUCCESS("OK charge.dispute.created"))

        post_dispute_active_record = sync_subscription_object(
            {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": now + 3600,
                "cancel_at_period_end": False,
            },
            event_id="evt_smoke_subscription_active_after_dispute",
        )
        if post_dispute_active_record.revoked_at is None:
            raise AssertionError("dispute revocation was cleared by active subscription update")
        self._assert_state(
            post_dispute_active_record,
            expected_premium=False,
            label="subscription.active_after_dispute",
        )

        dispute_won_record = mark_refund_or_dispute(
            {
                "id": "dp_smoke_disputed",
                "charge": "ch_smoke_disputed",
                "customer": customer_id,
                "status": "won",
            },
            event_type="charge.dispute.closed",
            event_id="evt_smoke_charge_dispute_won",
        )
        if dispute_won_record.revoked_at is not None:
            raise AssertionError("charge.dispute.closed won did not restore access")
        self._assert_state(dispute_won_record, expected_premium=True, label="charge.dispute.closed.won")
        self.stdout.write(self.style.SUCCESS("OK charge.dispute.closed.won"))

        audit_count = PremiumAuditLog.objects.filter(user=user).count()
        self.stdout.write(self.style.SUCCESS(f"billing_webhook_smoke=ok user={user.username} audits={audit_count}"))

    def _assert_billing_plan(self, record, *, expected_price_id, expected_interval, label):
        if record.stripe_price_id != expected_price_id:
            raise AssertionError(
                f"{label} expected stripe_price_id={expected_price_id}, " f"got {record.stripe_price_id}"
            )
        if record.billing_interval != expected_interval:
            raise AssertionError(
                f"{label} expected billing_interval={expected_interval}, " f"got {record.billing_interval}"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"OK {label} stripe_price_id={record.stripe_price_id} " f"billing_interval={record.billing_interval}"
            )
        )

    def _assert_state(self, record, *, expected_premium, label):
        record.user.refresh_from_db()
        if record.user.is_premium != expected_premium:
            raise AssertionError(f"{label} expected is_premium={expected_premium}, got {record.user.is_premium}")
        self.stdout.write(self.style.SUCCESS(f"OK {label} is_premium={record.user.is_premium}"))
