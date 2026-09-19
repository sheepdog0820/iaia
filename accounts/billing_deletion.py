from django.db import transaction

from accounts.billing import get_or_create_subscription_record, get_stripe, stripe_object_get, stripe_reference_id
from accounts.models import PremiumSubscription, StripeBillingRequest

ENDED = {"canceled", "incomplete_expired"}
CONTRACT_REMAINS = "Stripeの契約が終了していません。課金管理ページで解約し、契約終了後にアカウントを削除してください。"
UNCONFIRMED = "購入状態を確認できないため削除を中止しました。時間をおいて再試行するか、お問い合わせください。"


class BillingDeletionBlocked(ValueError):
    pass


def check_customer(resource, customer_id):
    if stripe_reference_id(stripe_object_get(resource, "customer")) != customer_id:
        raise BillingDeletionBlocked(UNCONFIRMED)


def check_ended(subscription, customer_id):
    check_customer(subscription, customer_id)
    if stripe_object_get(subscription, "status") not in ENDED:
        raise BillingDeletionBlocked(CONTRACT_REMAINS)


def close_checkout(stripe, session, customer_id):
    check_customer(session, customer_id)
    session_id = stripe_object_get(session, "id")
    if not session_id:
        raise BillingDeletionBlocked(UNCONFIRMED)
    status = stripe_object_get(session, "status")
    if status == "open":
        expired = stripe.checkout.Session.expire(session_id)
        check_customer(expired, customer_id)
        if stripe_object_get(expired, "id") != session_id or stripe_object_get(expired, "status") != "expired":
            raise BillingDeletionBlocked(UNCONFIRMED)
    elif status == "complete":
        subscription_id = stripe_reference_id(stripe_object_get(session, "subscription"))
        if not subscription_id:
            raise BillingDeletionBlocked(UNCONFIRMED)
        check_subscription(stripe, subscription_id, customer_id)
    elif status != "expired":
        raise BillingDeletionBlocked(UNCONFIRMED)


def check_subscription(stripe, subscription_id, customer_id):
    current = stripe.Subscription.retrieve(subscription_id)
    if stripe_object_get(current, "id") != subscription_id:
        raise BillingDeletionBlocked(UNCONFIRMED)
    check_ended(current, customer_id)


@transaction.atomic
def delete_account_after_billing_check(user):
    # Use the same row as Checkout creation, including accounts with no billing
    # history. Keep it locked through deletion so a waiting purchase cannot write.
    record = get_or_create_subscription_record(user)
    record = PremiumSubscription.objects.select_for_update().get(pk=record.pk)
    if record.subscription_status not in ENDED and (
        record.stripe_subscription_id
        or (record.stripe_customer_id and record.subscription_status in record.ACTIVE_STATUSES)
    ):
        raise BillingDeletionBlocked(CONTRACT_REMAINS)
    attempts = list(StripeBillingRequest.objects.filter(subscription=record))
    if any(not attempt.resource_id for attempt in attempts):
        # A lost response may hide a remote creation. Preserve the retry key.
        raise BillingDeletionBlocked(UNCONFIRMED)
    customer_id = record.stripe_customer_id
    if not customer_id and (record.stripe_subscription_id or attempts):
        raise BillingDeletionBlocked(UNCONFIRMED)
    if customer_id:
        try:
            stripe = get_stripe()
            for attempt in attempts:
                if attempt.operation == "checkout":
                    session = stripe.checkout.Session.retrieve(attempt.resource_id)
                    if stripe_object_get(session, "id") != attempt.resource_id:
                        raise BillingDeletionBlocked(UNCONFIRMED)
                    close_checkout(stripe, session, customer_id)
            # Include sessions created before durable request tracking existed.
            sessions = stripe.checkout.Session.list(customer=customer_id, status="open", limit=100)
            for session in sessions.auto_paging_iter():
                close_checkout(stripe, session, customer_id)
            if record.stripe_subscription_id:
                check_subscription(stripe, record.stripe_subscription_id, customer_id)
            # Check after expiration: payment may have completed before we got
            # the lock, while its webhook is still waiting for this same row.
            subscriptions = stripe.Subscription.list(customer=customer_id, status="all", limit=100)
            for subscription in subscriptions.auto_paging_iter():
                check_ended(subscription, customer_id)
        except BillingDeletionBlocked:
            raise
        except Exception as exc:
            raise BillingDeletionBlocked(UNCONFIRMED) from exc
    user.delete()
