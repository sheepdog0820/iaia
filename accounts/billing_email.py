"""Durable payment-warning delivery; SMTP acceptance is not exactly-once delivery."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.billing import send_payment_failed_email
from accounts.models import BillingEmailDelivery, PremiumAuditLog, PremiumSubscription, StripeInvoiceState


@transaction.atomic
def deliver_billing_email(delivery_id):
    if not getattr(settings, "BILLING_EMAIL_DELIVERY_ENABLED", False):
        return "disabled"
    candidate = BillingEmailDelivery.objects.filter(pk=delivery_id).values("subscription_id").first()
    if candidate is None:
        return "missing"
    # Use the same lock order as incoming invoice updates: subscription, then delivery.
    record = PremiumSubscription.objects.select_for_update().filter(pk=candidate["subscription_id"]).first()
    delivery = BillingEmailDelivery.objects.select_for_update().filter(pk=delivery_id).first()
    if record is None or delivery is None:
        return "missing"
    if delivery.status != "pending" or delivery.next_attempt_at > timezone.now():
        return delivery.status
    state = StripeInvoiceState.objects.filter(subscription=record, invoice_id=delivery.invoice_id).first()
    latest_failure = (
        PremiumAuditLog.objects.filter(
            user_id=record.user_id, action="payment_failed", source="stripe", metadata__invoice_id=delivery.invoice_id
        )
        .order_by("-created_at", "-pk")
        .first()
    )
    if (
        record.last_payment_failed_at is None
        or (state is not None and not state.payment_failed)
        or (latest_failure is not None and latest_failure.pk != delivery.audit_id)
    ):
        delivery.status = "canceled"
        delivery.last_error_code = "resolved_or_superseded"
    else:
        delivery.attempts += 1
        try:
            sent = send_payment_failed_email(record.user)
            delivery.last_error_code = "" if sent else "not_accepted"
        except Exception:
            # Do not persist SMTP exception text: it may contain recipients or credentials.
            sent = False
            delivery.last_error_code = "transport_error"
        if sent:
            delivery.status = "sent"
            delivery.sent_at = timezone.now()
        else:
            delivery.next_attempt_at = timezone.now() + timedelta(
                seconds=min(3600, 60 * 2 ** min(delivery.attempts - 1, 6))
            )
    delivery.save(update_fields=["status", "attempts", "sent_at", "next_attempt_at", "last_error_code"])
    audit = delivery.audit
    audit.metadata = {**audit.metadata, "email_sent": delivery.status == "sent", "email_status": delivery.status}
    audit.save(update_fields=["metadata"])
    return delivery.status


def dispatch_billing_emails(limit=25):
    if not getattr(settings, "BILLING_EMAIL_DELIVERY_ENABLED", False):
        return {"disabled": 1}
    ids = list(
        BillingEmailDelivery.objects.filter(status="pending", next_attempt_at__lte=timezone.now())
        .order_by("next_attempt_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    counts = {}
    for delivery_id in ids:
        status = deliver_billing_email(delivery_id)
        counts[status] = counts.get(status, 0) + 1
    return counts
