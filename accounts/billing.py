from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import PremiumAccessCode, PremiumAccessCodeRedemption, PremiumAuditLog, PremiumSubscription


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
    if record.stripe_customer_id:
        return record

    customer = stripe.Customer.create(
        email=user.email or None,
        name=user.get_full_name() or user.nickname or user.username,
        metadata={"user_id": str(user.id)},
    )
    record.stripe_customer_id = customer.id
    record.save(update_fields=["stripe_customer_id", "updated_at"])
    return record


def create_checkout_session(request, plan="monthly"):
    stripe = get_stripe()
    price_id = require_price_id(plan)
    record = get_or_create_stripe_customer(request.user)

    success_url = request.build_absolute_uri(reverse("billing_success"))
    cancel_url = request.build_absolute_uri(reverse("billing_cancel"))

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=record.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url,
        client_reference_id=str(request.user.id),
        metadata={"user_id": str(request.user.id), "billing_plan": plan},
        subscription_data={
            "metadata": {"user_id": str(request.user.id), "billing_plan": plan},
        },
    )
    return session


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
    cancel_at_period_end = bool(stripe_object_get(subscription, "cancel_at_period_end", False))
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


def handle_checkout_completed(session, event_id=""):
    from django.contrib.auth import get_user_model

    user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
    if not user_id:
        return None

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return None

    subscription = session.get("subscription")
    subscription_id = stripe_object_get(subscription, "id") if isinstance(subscription, dict) else subscription

    record = get_or_create_subscription_record(user)
    record.stripe_customer_id = session.get("customer") or record.stripe_customer_id
    record.stripe_subscription_id = subscription_id or record.stripe_subscription_id
    if event_id:
        record.last_webhook_event_id = event_id
    record.save(
        update_fields=[
            "stripe_customer_id",
            "stripe_subscription_id",
            "last_webhook_event_id",
            "updated_at",
        ]
    )

    if isinstance(subscription, dict):
        return sync_subscription_object(subscription, event_id=event_id)

    if record.stripe_subscription_id:
        stripe = get_stripe()
        subscription = stripe.Subscription.retrieve(record.stripe_subscription_id)
        return sync_subscription_object(subscription, event_id=event_id)

    return record


def mark_invoice_payment_failed(invoice, event_id=""):
    customer_id = invoice.get("customer")
    record = PremiumSubscription.objects.select_related("user").filter(stripe_customer_id=customer_id).first()
    if record is None:
        return None
    record.last_payment_failed_at = timezone.now()
    if event_id:
        record.last_webhook_event_id = event_id
    record.save(update_fields=["last_payment_failed_at", "last_webhook_event_id", "updated_at"])
    email_sent = send_payment_failed_email(record.user)
    create_premium_audit_log(
        record.user,
        action="payment_failed",
        source="stripe",
        reason="Invoice payment failed",
        stripe_event_id=event_id,
        metadata={
            "invoice_id": invoice.get("id", ""),
            "email_sent": email_sent,
        },
    )
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


def mark_refund_or_dispute(data_object, *, event_type, event_id=""):
    customer_id = stripe_object_get(data_object, "customer")
    charge_id = stripe_object_get(data_object, "charge") or stripe_object_get(data_object, "id", "")
    charge_obj = None
    if not customer_id and charge_id:
        try:
            stripe = get_stripe()
            charge_obj = stripe.Charge.retrieve(charge_id)
            customer_id = stripe_object_get(charge_obj, "customer", "")
        except Exception:
            customer_id = ""

    record = PremiumSubscription.objects.select_related("user").filter(stripe_customer_id=customer_id).first()
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
    ):
        record.subscription_status = "active"
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
        fail_silently=True,
    )
    return bool(sent_count)
