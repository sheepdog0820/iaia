from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import PremiumSubscription, StripeWebhookEvent


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_isolated_test")
class StripeSubscriptionEventOrderingTests(TestCase):
    def test_old_cancellation_does_not_replace_new_subscription(self):
        user = get_user_model().objects.create_user(username="resubscribed", is_premium=True)
        record = PremiumSubscription.objects.create(
            user=user,
            stripe_customer_id="cus_resubscribed",
            stripe_subscription_id="sub_new",
            subscription_status="active",
            access_source="stripe",
        )
        old = {"id": "sub_old", "customer": "cus_resubscribed", "status": "canceled"}
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "id": "evt_old_cancellation",
            "type": "customer.subscription.deleted",
            "data": {"object": old},
        }
        stripe.Subscription.retrieve.return_value = SimpleNamespace(**old)
        with patch("accounts.views.billing_views.get_stripe", return_value=stripe):
            response = APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(user.is_premium)
        self.assertEqual(record.stripe_subscription_id, "sub_new")

    def test_delayed_active_event_uses_current_canceled_subscription(self):
        user = get_user_model().objects.create_user(username="ordered-subscription")
        PremiumSubscription.objects.create(
            user=user,
            stripe_customer_id="cus_ordered",
            stripe_subscription_id="sub_ordered",
            subscription_status="canceled",
            access_source="stripe",
        )
        snapshot = {"id": "sub_ordered", "customer": "cus_ordered", "status": "active"}
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "id": "evt_delayed_active",
            "type": "customer.subscription.updated",
            "data": {"object": snapshot},
        }
        stripe.Subscription.retrieve.return_value = SimpleNamespace(**{**snapshot, "status": "canceled"})
        with patch("accounts.views.billing_views.get_stripe", return_value=stripe):
            response = APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_premium)
        self.assertEqual(PremiumSubscription.objects.get().subscription_status, "canceled")
        stripe.Subscription.retrieve.assert_called_once_with("sub_ordered")

    def test_current_subscription_lookup_failure_remains_retryable(self):
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "id": "evt_ordered_lookup_failure",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_ordered", "customer": "cus_ordered", "status": "active"}},
        }
        stripe.Subscription.retrieve.side_effect = TimeoutError("isolated lookup failure")
        with patch("accounts.views.billing_views.get_stripe", return_value=stripe):
            response = APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "failed")
