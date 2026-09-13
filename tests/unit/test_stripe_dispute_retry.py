from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import PremiumAuditLog, PremiumSubscription, StripeWebhookEvent


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_isolated_test", STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=True)
class StripeDisputeRetryTests(TestCase):
    def test_charge_lookup_failure_remains_retryable(self):
        user = get_user_model().objects.create_user(username="dispute-retry", is_premium=True)
        PremiumSubscription.objects.create(
            user=user,
            stripe_customer_id="cus_retry",
            stripe_subscription_id="sub_retry",
            subscription_status="active",
            access_source="stripe",
        )
        stripe = Mock()
        stripe.Webhook.construct_event.return_value = {
            "id": "evt_dispute_retry",
            "type": "charge.dispute.created",
            "data": {"object": {"id": "dp_retry", "charge": "ch_retry", "status": "needs_response"}},
        }
        stripe.Charge.retrieve.side_effect = TimeoutError("isolated Stripe outage")
        client = APIClient()
        with (
            patch("accounts.views.billing_views.get_stripe", return_value=stripe),
            patch("accounts.billing.get_stripe", return_value=stripe),
        ):
            response = client.post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "failed")
            self.assertFalse(PremiumAuditLog.objects.exists())
            user.refresh_from_db()
            self.assertTrue(user.is_premium)

            stripe.Charge.retrieve.side_effect = None
            stripe.Charge.retrieve.return_value = {"id": "ch_retry", "customer": "cus_retry"}
            response = client.post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "succeeded")
            user.refresh_from_db()
            self.assertFalse(user.is_premium)
            audit_count = PremiumAuditLog.objects.count()

            response = client.post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")
            self.assertTrue(response.json()["duplicate"])
            self.assertEqual(PremiumAuditLog.objects.count(), audit_count)
            self.assertEqual(stripe.Charge.retrieve.call_count, 2)
