from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import PremiumSubscription, StripeWebhookEvent


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_isolated_test")
class StripeDisputeRestorationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dispute-restore")
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_restore",
            stripe_subscription_id="sub_restore",
            subscription_status="revoked",
            access_source="stripe",
            revoked_at=timezone.now(),
            revoked_reason="Stripe charge disputed",
        )
        self.stripe = Mock()
        self.stripe.Webhook.construct_event.return_value = {
            "id": "evt_restore",
            "type": "charge.dispute.closed",
            "data": {"object": {"id": "dp_restore", "customer": "cus_restore", "status": "won"}},
        }

    def deliver(self):
        with (
            patch("accounts.views.billing_views.get_stripe", return_value=self.stripe),
            patch("accounts.billing.get_stripe", return_value=self.stripe),
        ):
            return APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")

    def test_dispute_won_cannot_reactivate_canceled_subscription(self):
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_restore", customer="cus_restore", status="canceled"
        )
        self.assertEqual(self.deliver().status_code, 200)
        self.user.refresh_from_db()
        self.record.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.record.subscription_status, "canceled")

    def test_lookup_failure_retries_without_clearing_revocation(self):
        self.stripe.Subscription.retrieve.side_effect = TimeoutError("current status unavailable")
        self.assertEqual(self.deliver().status_code, 500)
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.revoked_at)
        self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "failed")
        self.stripe.Subscription.retrieve.side_effect = None
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_restore", customer="cus_restore", status="active"
        )
        self.assertEqual(self.deliver().status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_different_customer_response_is_rejected(self):
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_restore", customer="cus_other", status="active"
        )
        self.assertEqual(self.deliver().status_code, 500)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
