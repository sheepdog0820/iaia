from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import (
    BillingEmailDelivery,
    PremiumAccessCode,
    PremiumAccessCodeRedemption,
    PremiumAuditLog,
    PremiumSubscription,
    StripeBillingRequest,
    StripeInvoiceState,
)


def get_stripe():
    import stripe

    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured("STRIPE_SECRET_KEY is required")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2026-02-25.clover")
    return stripe


PRICE_SETTINGS_BY_PLAN = {
    "monthly": "STRIPE_PREMIUM_PRICE_ID",
    "yearly": "STRIPE_PREMIUM_YEARLY_PRICE_ID",
}


def get_configured_checkout_plans():
    plans = []
    monthly_price_id = getattr(settings, "STRIPE_PREMIUM_PRICE_ID", "")
    if monthly_price_id:
        plans.append(
            {
                "key": "monthly",
                "label": getattr(settings, "PREMIUM_MONTHLY_PRICE_LABEL", "月額プラン"),
                "description": getattr(settings, "PREMIUM_MONTHLY_PRICE_DESCRIPTION", "480円/月"),
            }
        )
    yearly_price_id = getattr(settings, "STRIPE_PREMIUM_YEARLY_PRICE_ID", "")
    if yearly_price_id:
        plans.append(
            {
                "key": "yearly",
                "label": getattr(settings, "PREMIUM_YEARLY_PRICE_LABEL", "年額プラン"),
                "description": getattr(settings, "PREMIUM_YEARLY_PRICE_DESCRIPTION", "4,800円/年"),
            }
        )
    return plans


def require_price_id(plan="monthly"):
    if plan not in PRICE_SETTINGS_BY_PLAN:
        raise ValueError("Invalid billing plan")
    setting_name = PRICE_SETTINGS_BY_PLAN[plan]
    price_id = getattr(settings, setting_name, "")
    if not price_id:
        raise ImproperlyConfigured(f"{setting_name} is required")
    return price_id


def timestamp_to_datetime(value):
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)


def stripe_object_get(obj, key, default=None):
    if hasattr(obj, "get"):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_subscription_price(subscription):
    items = stripe_object_get(subscription, "items", {}) or {}
    item_data = stripe_object_get(items, "data", []) or []
    if not item_data:
        return "", ""
    first_item = item_data[0]
    price = stripe_object_get(first_item, "price", {}) or {}
    price_id = stripe_object_get(price, "id", "") or ""
    recurring = stripe_object_get(price, "recurring", {}) or {}
    interval = stripe_object_get(recurring, "interval", "") or ""
    return price_id, interval


def get_or_create_subscription_record(user):
    record, _ = PremiumSubscription.objects.get_or_create(user=user)
    return record


def get_or_create_stripe_customer(user):
    stripe = get_stripe()
    record = get_or_create_subscription_record(user)
    # Persist the immutable retry parameters before making a remote write.
    with transaction.atomic():
        record = PremiumSubscription.objects.select_for_update().get(pk=record.pk)
        if record.stripe_customer_id:
            return record
        StripeBillingRequest.objects.get_or_create(
            subscription=record,
            operation="customer",
            defaults={
                "parameters": {
                    "email": user.email or None,
                    "name": user.get_full_name() or user.nickname or user.username,
                    "metadata": {"user_id": str(user.id)},
                }
            },
        )
    with transaction.atomic():
        record = PremiumSubscription.objects.select_for_update().get(pk=record.pk)
        if record.stripe_customer_id:
            return record
        attempt = StripeBillingRequest.objects.get(subscription=record, operation="customer")
        customer = execute_stripe_creation(attempt, stripe.Customer.create)
        record.stripe_customer_id = customer.id
        record.save(update_fields=["stripe_customer_id", "updated_at"])
        attempt.resource_id = customer.id
        attempt.save(update_fields=["resource_id"])
        return record


def execute_stripe_creation(attempt, create):
    # Stripe can discard idempotency keys after 24 hours. An unresolved write must
    # be reconciled by support, never silently retried with a fresh key.
    if attempt.created_at <= timezone.now() - timedelta(hours=23):
        raise ValueError("前回の購入処理の確認が必要です。お問い合わせ窓口へご連絡ください。")
    return create(**attempt.parameters, idempotency_key=str(attempt.idempotency_key))


def create_checkout_session(request, plan="monthly"):
    stripe = get_stripe()
    price_id = require_price_id(plan)
    record = get_or_create_stripe_customer(request.user)

    success_url = request.build_absolute_uri(reverse("billing_success"))
    cancel_url = request.build_absolute_uri(reverse("billing_cancel"))

    parameters = {
        "mode": "subscription",
        "customer": record.stripe_customer_id,
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": cancel_url,
        "client_reference_id": str(request.user.id),
        "metadata": {"user_id": str(request.user.id), "billing_plan": plan},
        "subscription_data": {"metadata": {"user_id": str(request.user.id), "billing_plan": plan}},
    }
    # Each iteration commits an intent before its API call in the next iteration.
    # The customer row serializes purchase requests across processes on PostgreSQL.
    for _ in range(4):
        with transaction.atomic():
            record = PremiumSubscription.objects.select_for_update().get(pk=record.pk)
            subscriptions = stripe.Subscription.list(customer=record.stripe_customer_id, status="all", limit=100)
            if any(
                stripe_object_get(sub, "status") not in {"canceled", "incomplete_expired"}
                for sub in subscriptions.auto_paging_iter()
            ):
                raise ValueError("既に契約があります。請求管理画面で契約をご確認ください。")
            attempt = StripeBillingRequest.objects.filter(subscription=record, operation="checkout").first()
            if attempt is None:
                # Close untracked sessions from an older app version before
                # creating an intent; otherwise two browser tabs could both pay.
                open_sessions = stripe.checkout.Session.list(
                    customer=record.stripe_customer_id, status="open", limit=100
                )
                for old_session in open_sessions.auto_paging_iter():
                    stripe.checkout.Session.expire(old_session.id)
            if attempt is not None:
                session = (
                    stripe.checkout.Session.retrieve(attempt.resource_id)
                    if attempt.resource_id
                    else execute_stripe_creation(attempt, stripe.checkout.Session.create)
                )
                attempt.resource_id = session.id
                attempt.save(update_fields=["resource_id"])
                session_status = stripe_object_get(session, "status")
                if session_status == "open":
                    if attempt.parameters == parameters:
                        return session
                    # Expiration must succeed before another price can be purchased.
                    stripe.checkout.Session.expire(session.id)
                elif session_status == "complete":
                    subscription_id = stripe_object_get(session, "subscription")
                    current = stripe.Subscription.retrieve(subscription_id) if subscription_id else None
                    if stripe_object_get(current, "status") not in {"canceled", "incomplete_expired"}:
                        raise ValueError("既に契約があります。請求管理画面で契約をご確認ください。")
                elif session_status != "expired":
                    raise ValueError("購入処理を確認できません。時間をおいて再度お試しください。")
                attempt.delete()
            StripeBillingRequest.objects.create(subscription=record, operation="checkout", parameters=parameters)
    raise ValueError("別の購入操作が進行中です。時間をおいて再度お試しください。")


def create_portal_session(request):
    record = get_or_create_subscription_record(request.user)
    if not record.stripe_customer_id:
        raise ValueError("Stripe customer does not exist for this user")

    stripe = get_stripe()
    return_url = request.build_absolute_uri(reverse("billing"))
    session_params = {
        "customer": record.stripe_customer_id,
        "return_url": return_url,
    }
    portal_configuration_id = getattr(
        settings,
        "STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID",
        "",
    )
    if portal_configuration_id:
        session_params["configuration"] = portal_configuration_id
    return stripe.billing_portal.Session.create(**session_params)


def sync_subscription_object(subscription, event_id=""):
    customer_id = stripe_object_get(subscription, "customer", "")
    if not customer_id:
        return None

    record = PremiumSubscription.objects.select_related("user").filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None

    subscription_id = stripe_object_get(subscription, "id", "") or ""
    status = stripe_object_get(subscription, "status", "") or ""
    current_period_end = stripe_object_get(subscription, "current_period_end")
    if current_period_end is None:
        # Basil and later store periods on items. Use the same item as the price.
        items = stripe_object_get(subscription, "items", {}) or {}
        item_data = stripe_object_get(items, "data", []) or []
        if item_data:
            current_period_end = stripe_object_get(item_data[0], "current_period_end")
    cancel_at_period_end = bool(stripe_object_get(subscription, "cancel_at_period_end", False))
    # Customer Portal can schedule the same period-end cancellation via cancel_at.
    cancel_at = stripe_object_get(subscription, "cancel_at")
    if current_period_end and cancel_at == current_period_end:
        cancel_at_period_end = True
    stripe_price_id, billing_interval = extract_subscription_price(subscription)

    was_active = record.user.is_premium
    previous_access_source = record.access_source

    if (
        previous_access_source == "promo_code"
        and record.is_promo_active
        and status not in PremiumSubscription.ACTIVE_STATUSES
    ):
        record.stripe_subscription_id = subscription_id or record.stripe_subscription_id
        record.stripe_price_id = stripe_price_id or record.stripe_price_id
        record.billing_interval = billing_interval or record.billing_interval
        record.cancel_at_period_end = cancel_at_period_end
        if event_id:
            record.last_webhook_event_id = event_id
        record.save(
            update_fields=[
                "stripe_subscription_id",
                "stripe_price_id",
                "billing_interval",
                "cancel_at_period_end",
                "last_webhook_event_id",
                "updated_at",
            ]
        )
        record.sync_user_premium_access()
        return record

    record.stripe_subscription_id = subscription_id
    record.subscription_status = status
    record.stripe_price_id = stripe_price_id
    record.billing_interval = billing_interval
    record.current_period_end = timestamp_to_datetime(current_period_end)
    record.cancel_at_period_end = cancel_at_period_end
    record.access_source = "stripe"
    record.premium_expires_at = None
    if status in PremiumSubscription.ACTIVE_STATUSES and not (record.revoked_at and previous_access_source == "stripe"):
        record.revoked_at = None
        record.revoked_reason = ""
    if event_id:
        record.last_webhook_event_id = event_id
    record.save(
        update_fields=[
            "stripe_subscription_id",
            "subscription_status",
            "stripe_price_id",
            "billing_interval",
            "current_period_end",
            "cancel_at_period_end",
            "access_source",
            "premium_expires_at",
            "revoked_at",
            "revoked_reason",
            "last_webhook_event_id",
            "updated_at",
        ]
    )
    record.sync_user_premium_access()
    audit_metadata = {
        "stripe_subscription_id": record.stripe_subscription_id,
        "stripe_price_id": record.stripe_price_id,
        "billing_interval": record.billing_interval,
        "cancel_at_period_end": record.cancel_at_period_end,
    }
    if record.user.is_premium and not was_active:
        create_premium_audit_log(
            record.user,
            action="granted",
            source="stripe",
            reason=f"Stripe subscription status: {status}",
            stripe_event_id=event_id,
            metadata=audit_metadata,
        )
    elif was_active and not record.user.is_premium:
        create_premium_audit_log(
            record.user,
            action="revoked",
            source="stripe",
            reason=f"Stripe subscription status: {status}",
            stripe_event_id=event_id,
            metadata=audit_metadata,
        )
    return record


@transaction.atomic
def handle_checkout_completed(session, event_id=""):
    from django.contrib.auth import get_user_model

    user_id = stripe_object_get(session, "client_reference_id") or stripe_object_get(
        stripe_object_get(session, "metadata", {}) or {}, "user_id"
    )
    if not user_id:
        return None

    user = get_user_model().objects.filter(id=user_id).first()
    if user is None:
        return None

    customer_id = stripe_reference_id(stripe_object_get(session, "customer"))
    subscription_id = stripe_reference_id(stripe_object_get(session, "subscription"))
    if not customer_id or not subscription_id:
        raise ValueError("Stripe checkout subscription reference missing")
    record = get_or_create_subscription_record(user)
    record = PremiumSubscription.objects.select_for_update().get(pk=record.pk)
    if record.stripe_customer_id and record.stripe_customer_id != customer_id:
        raise ValueError("Stripe checkout customer ownership mismatch")

    # Even expanded event payloads are historical snapshots. Fetch after locking.
    current = get_stripe().Subscription.retrieve(subscription_id)
    if (
        stripe_object_get(current, "id") != subscription_id
        or stripe_reference_id(stripe_object_get(current, "customer")) != customer_id
    ):
        raise ValueError("Stripe checkout subscription ownership mismatch")
    if (
        record.stripe_subscription_id
        and record.stripe_subscription_id != subscription_id
        and stripe_object_get(current, "status") in {"canceled", "incomplete_expired"}
    ):
        return record

    record.stripe_customer_id = customer_id
    record.save(update_fields=["stripe_customer_id", "updated_at"])
    return sync_subscription_object(current, event_id=event_id)


def current_invoice_state(stripe, invoice_id, customer_id):
    current = stripe.Invoice.retrieve(invoice_id)
    if stripe_object_get(current, "id") != invoice_id or stripe_object_get(current, "customer") != customer_id:
        raise ValueError("Stripe invoice ownership mismatch")
    status = stripe_object_get(current, "status")
    if status not in {"open", "paid", "void", "uncollectible"}:
        raise ValueError("Unexpected Stripe invoice state")
    return status


@transaction.atomic
def reconcile_invoice_payment(invoice, event_type, event_id=""):
    customer_id = invoice.get("customer")
    record = PremiumSubscription.objects.select_for_update().filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None
    stripe = get_stripe()
    states = StripeInvoiceState.objects.filter(subscription=record)
    if not states.exists():
        # Seed pre-upgrade failures from audit history and current Stripe state.
        # Never attribute a legacy warning to an unrelated successful invoice.
        prior_ids = {
            metadata.get("invoice_id")
            for metadata in PremiumAuditLog.objects.filter(
                user=record.user, source="stripe", action="payment_failed"
            ).values_list("metadata", flat=True)
            if metadata.get("invoice_id")
        }
        if record.last_payment_failed_at and not prior_ids:
            raise ValueError("Legacy payment failure requires invoice reconciliation")
        for prior_id in sorted(prior_ids):
            current_status = current_invoice_state(stripe, prior_id, customer_id)
            StripeInvoiceState.objects.create(
                subscription=record,
                invoice_id=prior_id,
                status=current_status,
                payment_failed=current_status in {"open", "uncollectible"},
            )
    invoice_id = invoice["id"]
    current_status = current_invoice_state(stripe, invoice_id, customer_id)
    state, _ = StripeInvoiceState.objects.get_or_create(
        subscription=record, invoice_id=invoice_id, defaults={"status": current_status}
    )
    was_failed = state.payment_failed
    state.status = current_status
    if current_status in {"paid", "void"}:
        state.payment_failed = False
    elif event_type == "invoice.payment_failed":
        state.payment_failed = True
    state.last_event_id = event_id
    state.save(update_fields=["status", "payment_failed", "last_event_id", "updated_at"])
    if state.payment_failed and not was_failed:
        return mark_invoice_payment_failed(invoice, event_id=event_id)
    if not states.filter(payment_failed=True).exists():
        return mark_invoice_payment_succeeded(invoice, event_id=event_id)
    if record.last_payment_failed_at is None:
        record.last_payment_failed_at = timezone.now()
    record.last_webhook_event_id = event_id
    record.save(update_fields=["last_payment_failed_at", "last_webhook_event_id", "updated_at"])
    return record


@transaction.atomic
def mark_invoice_payment_failed(invoice, event_id=""):
    customer_id = invoice.get("customer")
    record = PremiumSubscription.objects.select_related("user").filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None
    record.last_payment_failed_at = timezone.now()
    if event_id:
        record.last_webhook_event_id = event_id
    record.save(update_fields=["last_payment_failed_at", "last_webhook_event_id", "updated_at"])
    audit = create_premium_audit_log(
        record.user,
        action="payment_failed",
        source="stripe",
        reason="Invoice payment failed",
        stripe_event_id=event_id,
        metadata={
            "invoice_id": invoice.get("id", ""),
            "email_sent": False,
            "email_status": "pending",
        },
    )
    BillingEmailDelivery.objects.create(audit=audit, subscription=record, invoice_id=invoice.get("id", ""))
    return record


def mark_invoice_payment_succeeded(invoice, event_id=""):
    customer_id = invoice.get("customer")
    record = PremiumSubscription.objects.select_related("user").filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None
    had_payment_failure = record.last_payment_failed_at is not None
    record.last_payment_failed_at = None
    if event_id:
        record.last_webhook_event_id = event_id
    record.save(update_fields=["last_payment_failed_at", "last_webhook_event_id", "updated_at"])
    if had_payment_failure:
        create_premium_audit_log(
            record.user,
            action="payment_recovered",
            source="stripe",
            reason="Invoice payment succeeded after failure",
            stripe_event_id=event_id,
            metadata={"invoice_id": invoice.get("id", "")},
        )
    return record


def stripe_reference_id(value):
    return value if isinstance(value, str) else stripe_object_get(value, "id", "")


@transaction.atomic
def reconcile_dispute_event(data_object, *, event_type, event_id=""):
    stripe = get_stripe()
    dispute_id = stripe_object_get(data_object, "id")
    charge_id = stripe_reference_id(stripe_object_get(data_object, "charge"))
    if not dispute_id or not charge_id:
        raise ValueError("Stripe dispute reference missing")
    charge = stripe.Charge.retrieve(charge_id)
    customer_id = stripe_reference_id(stripe_object_get(charge, "customer"))
    if stripe_object_get(charge, "id") != charge_id or not customer_id:
        raise ValueError("Stripe dispute charge ownership mismatch")
    record = PremiumSubscription.objects.select_for_update().filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None
    # Read under the same row lock as subscription/refund updates so an older
    # notification cannot overwrite a completed dispute with its old snapshot.
    current = stripe.Dispute.retrieve(dispute_id)
    if (
        stripe_object_get(current, "id") != dispute_id
        or stripe_reference_id(stripe_object_get(current, "charge")) != charge_id
    ):
        raise ValueError("Stripe dispute charge mismatch")
    current_status = stripe_object_get(current, "status")
    closed_statuses = {"won", "lost", "warning_closed", "prevented"}
    if current_status not in closed_statuses | {
        "needs_response",
        "under_review",
        "warning_needs_response",
        "warning_under_review",
    }:
        raise ValueError("Unexpected Stripe dispute state")
    current_data = {
        key: stripe_object_get(current, key, "")
        for key in ("id", "status", "amount", "currency", "reason", "payment_intent")
    }
    current_data.update(
        customer=customer_id,
        charge=charge_id,
        invoice=stripe_reference_id(stripe_object_get(charge, "invoice")),
        payment_intent=stripe_reference_id(stripe_object_get(current, "payment_intent")),
    )
    effective_type = "charge.dispute.closed" if current_status in closed_statuses else "charge.dispute.created"
    return mark_refund_or_dispute(current_data, event_type=effective_type, event_id=event_id)


def has_other_automatic_payment_revocation(user, winning_dispute_id):
    if not winning_dispute_id:
        return True
    disputes = {}
    history = PremiumAuditLog.objects.filter(
        user=user, source="stripe", action__in=["refunded", "disputed", "granted", "restored"]
    )
    for audit in history.order_by("-created_at", "-pk").iterator():
        # A completed access restoration starts a new period of automatic holds.
        if audit.action in {"granted", "restored"}:
            break
        metadata = audit.metadata
        automatic = metadata.get("auto_revoked", True)
        if audit.action == "refunded":
            if automatic:
                return True
            continue
        dispute_id = metadata.get("object_id")
        if dispute_id == winning_dispute_id:
            continue
        if not dispute_id:
            if automatic:
                return True
            continue
        disposition = disputes.setdefault(dispute_id, {"status": metadata.get("dispute_status"), "automatic": False})
        disposition["automatic"] = disposition["automatic"] or automatic
    return any(item["automatic"] and item["status"] != "won" for item in disputes.values())


@transaction.atomic
def mark_refund_or_dispute(data_object, *, event_type, event_id=""):
    customer_id = stripe_object_get(data_object, "customer")
    charge_id = stripe_object_get(data_object, "charge") or stripe_object_get(data_object, "id", "")
    charge_obj = None
    if not customer_id and charge_id:
        # Let the webhook record a failure so Stripe can retry a transient outage.
        stripe = get_stripe()
        charge_obj = stripe.Charge.retrieve(charge_id)
        customer_id = stripe_object_get(charge_obj, "customer", "")

    record = (
        PremiumSubscription.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(stripe_customer_id=customer_id)
        .first()
    )
    if record is None:
        return None

    action = "disputed" if "dispute" in event_type else "refunded"
    dispute_status = stripe_object_get(data_object, "status", "")
    dispute_closed_without_loss = event_type == "charge.dispute.closed" and dispute_status not in {
        "lost",
        "warning_closed",
    }
    dispute_closed_won = event_type == "charge.dispute.closed" and dispute_status == "won"
    reason = "Stripe charge disputed" if action == "disputed" else "Stripe charge refunded"
    was_active = record.user.is_premium
    access_restored = False
    if not dispute_closed_without_loss:
        record.last_refund_or_dispute_at = timezone.now()
    if event_id:
        record.last_webhook_event_id = event_id
    update_fields = ["last_webhook_event_id", "updated_at"]
    if not dispute_closed_without_loss:
        update_fields.insert(0, "last_refund_or_dispute_at")
    record.save(update_fields=update_fields)
    auto_revoked = bool(getattr(settings, "STRIPE_REVOKE_ON_REFUND_OR_DISPUTE", True))
    access_revoked = False
    if auto_revoked and not dispute_closed_without_loss:
        record.revoke_access(reason, save=True, preserve_manual_override=True)
        access_revoked = was_active and not record.user.is_premium
    elif (
        auto_revoked
        and dispute_closed_won
        and record.access_source == "stripe"
        and record.revoked_at is not None
        and record.revoked_reason == "Stripe charge disputed"
        and record.stripe_subscription_id
        and not has_other_automatic_payment_revocation(record.user, stripe_object_get(data_object, "id"))
    ):
        current_subscription = get_stripe().Subscription.retrieve(record.stripe_subscription_id)
        if (
            stripe_object_get(current_subscription, "id") != record.stripe_subscription_id
            or stripe_object_get(current_subscription, "customer") != record.stripe_customer_id
        ):
            raise ValueError("Stripe subscription ownership mismatch")
        record.subscription_status = stripe_object_get(current_subscription, "status", "")
        record.revoked_at = None
        record.revoked_reason = ""
        record.last_refund_or_dispute_at = None
        if event_id:
            record.last_webhook_event_id = event_id
        record.save(
            update_fields=[
                "subscription_status",
                "revoked_at",
                "revoked_reason",
                "last_refund_or_dispute_at",
                "last_webhook_event_id",
                "updated_at",
            ]
        )
        record.sync_user_premium_access()
        access_restored = record.user.is_premium
    invoice_id = stripe_object_get(data_object, "invoice", "") or stripe_object_get(charge_obj, "invoice", "")
    payment_intent_id = stripe_object_get(data_object, "payment_intent", "") or stripe_object_get(
        charge_obj, "payment_intent", ""
    )
    create_premium_audit_log(
        record.user,
        action=action,
        source="stripe",
        reason=reason,
        stripe_event_id=event_id,
        metadata={
            "event_type": event_type,
            "object_id": stripe_object_get(data_object, "id", ""),
            "charge_id": charge_id,
            "invoice_id": invoice_id,
            "payment_intent_id": payment_intent_id,
            "amount": stripe_object_get(data_object, "amount", ""),
            "currency": stripe_object_get(data_object, "currency", ""),
            "dispute_status": dispute_status,
            "dispute_reason": stripe_object_get(data_object, "reason", ""),
            "access_was_active": was_active,
            "auto_revoked": auto_revoked,
            "access_revoked": access_revoked,
            "access_restored": access_restored,
        },
    )
    if access_restored:
        create_premium_audit_log(
            record.user,
            action="restored",
            source="stripe",
            reason="Stripe dispute won",
            stripe_event_id=event_id,
            metadata={
                "event_type": event_type,
                "object_id": stripe_object_get(data_object, "id", ""),
                "charge_id": charge_id,
                "dispute_status": dispute_status,
            },
        )
    return record


class PremiumCodeRedeemError(ValueError):
    pass


def premium_access_code_metadata(access_code):
    return {
        "access_code_id": access_code.pk,
        "access_code_label": access_code.label,
        "access_code_campaign_name": access_code.campaign_name,
    }


def redeem_premium_access_code(user, raw_code):
    normalized_code = PremiumAccessCode.normalize_code(raw_code)
    if not normalized_code:
        raise PremiumCodeRedeemError("コードを入力してください。")

    code_digest = PremiumAccessCode.digest(normalized_code)
    with transaction.atomic():
        access_code = PremiumAccessCode.objects.select_for_update().filter(code_digest=code_digest).first()
        if access_code is None:
            raise PremiumCodeRedeemError("コードが見つかりません。")

        if PremiumAccessCodeRedemption.objects.filter(
            access_code=access_code,
            user=user,
        ).exists():
            return access_code, False

        if not access_code.is_active:
            raise PremiumCodeRedeemError("このコードは利用できません。")

        if user.has_premium_access:
            return access_code, False

        PremiumAccessCodeRedemption.objects.create(access_code=access_code, user=user)
        access_code.use_count += 1
        access_code.save(update_fields=["use_count"])

        user.is_premium = True
        user.save(update_fields=["is_premium"])

        record = get_or_create_subscription_record(user)
        record.subscription_status = "promo"
        record.access_source = "promo_code"
        record.current_period_end = access_code.expires_at
        record.premium_expires_at = access_code.expires_at
        record.cancel_at_period_end = False
        record.revoked_at = None
        record.revoked_reason = ""
        record.save(
            update_fields=[
                "subscription_status",
                "access_source",
                "current_period_end",
                "premium_expires_at",
                "cancel_at_period_end",
                "revoked_at",
                "revoked_reason",
                "updated_at",
            ]
        )
        create_premium_audit_log(
            user,
            action="granted",
            source="promo_code",
            reason=f"Premium access code redeemed: {access_code.label or access_code.pk}",
            metadata=premium_access_code_metadata(access_code),
        )

    return access_code, True


def expire_promo_subscriptions(now=None, dry_run=False):
    now = now or timezone.now()
    expired = PremiumSubscription.objects.select_related("user").filter(
        subscription_status=PremiumSubscription.PROMO_STATUS,
        access_source="promo_code",
        premium_expires_at__isnull=False,
        premium_expires_at__lte=now,
        revoked_at__isnull=True,
        user__is_premium=True,
    )
    count = 0
    for record in expired:
        count += 1
        if dry_run:
            continue
        redemption = (
            PremiumAccessCodeRedemption.objects.select_related("access_code")
            .filter(user=record.user)
            .order_by("-redeemed_at")
            .first()
        )
        record.revoke_access(
            "Premium access code expired",
            save=True,
            preserve_manual_override=True,
        )
        create_premium_audit_log(
            record.user,
            action="revoked",
            source="promo_code",
            reason="Premium access code expired",
            metadata=(
                premium_access_code_metadata(redemption.access_code) if redemption else {"subscription_id": record.pk}
            ),
        )
    return count


def create_premium_audit_log(user, *, action, source="", reason="", stripe_event_id="", metadata=None, actor=None):
    return PremiumAuditLog.objects.create(
        user=user,
        actor=actor,
        action=action,
        source=source,
        reason=reason,
        stripe_event_id=stripe_event_id or "",
        metadata=metadata or {},
    )


def send_payment_failed_email(user):
    if not user.email:
        return False
    site_url = getattr(settings, "PUBLIC_SITE_URL", "").rstrip("/")
    billing_url = f"{site_url}/accounts/billing/" if site_url else "/accounts/billing/"
    sent_count = send_mail(
        subject="[タブレノ] プレミアム料金のお支払いを確認できませんでした",
        message=(
            f"{user.nickname or user.username} 様\n\n"
            "プレミアム料金のお支払いを確認できませんでした。\n"
            "カード更新が必要です。\n"
            "ログイン後、プレミアム管理画面から支払い方法を確認してください。\n\n"
            f"{billing_url}\n"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@tableno.jp"),
        recipient_list=[user.email],
        connection=get_connection(timeout=10),
        fail_silently=True,
    )
    return bool(sent_count)
