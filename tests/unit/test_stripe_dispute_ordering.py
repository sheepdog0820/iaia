from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import PremiumSubscription, StripeWebhookEvent


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_isolated_test")
class StripeDisputeOrderingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dispute-order", is_premium=True)
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_order",
            stripe_subscription_id="sub_order",
            subscription_status="active",
            access_source="stripe",
        )
        self.stripe = Mock()
        self.stripe.Webhook.construct_event.return_value = {
            "id": "evt_old_created",
            "type": "charge.dispute.created",
            "data": {"object": {"id": "dp_order", "charge": "ch_order", "status": "needs_response"}},
        }
        self.stripe.Charge.retrieve.return_value = SimpleNamespace(id="ch_order", customer="cus_order")
        self.stripe.Dispute.retrieve.return_value = SimpleNamespace(id="dp_order", charge="ch_order", status="won")

    def deliver(self):
        with (
            patch("accounts.views.billing_views.get_stripe", return_value=self.stripe),
            patch("accounts.billing.get_stripe", return_value=self.stripe),
        ):
            return APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")

    def test_old_created_event_cannot_revoke_a_won_dispute(self):
        self.assertEqual(self.deliver().status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.stripe.Dispute.retrieve.assert_called_once_with("dp_order")

    def test_latest_dispute_lookup_failure_can_be_retried(self):
        self.stripe.Dispute.retrieve.side_effect = TimeoutError("temporary dispute read failure")
        self.assertEqual(self.deliver().status_code, 500)
        self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "failed")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.stripe.Dispute.retrieve.side_effect = None
        self.assertEqual(self.deliver().status_code, 200)

    def test_dispute_charge_mismatch_is_rejected(self):
        self.stripe.Dispute.retrieve.return_value = SimpleNamespace(id="dp_order", charge="ch_other", status="won")
        self.assertEqual(self.deliver().status_code, 500)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)

    def test_current_lost_state_revokes_despite_old_winning_notification(self):
        self.stripe.Webhook.construct_event.return_value["type"] = "charge.dispute.closed"
        self.stripe.Webhook.construct_event.return_value["data"]["object"]["status"] = "won"
        self.stripe.Dispute.retrieve.return_value = SimpleNamespace(id="dp_order", charge="ch_order", status="lost")
        self.assertEqual(self.deliver().status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_expanded_references_are_checked_without_storing_whole_objects(self):
        self.stripe.Webhook.construct_event.return_value["data"]["object"]["charge"] = {"id": "ch_order"}
        self.stripe.Charge.retrieve.return_value = SimpleNamespace(
            id="ch_order", customer=SimpleNamespace(id="cus_order"), invoice=SimpleNamespace(id="in_order")
        )
        self.stripe.Dispute.retrieve.return_value = SimpleNamespace(
            id="dp_order",
            charge=SimpleNamespace(id="ch_order"),
            status="won",
            payment_intent=SimpleNamespace(id="pi_order"),
        )
        self.assertEqual(self.deliver().status_code, 200)
        from accounts.models import PremiumAuditLog

        metadata = PremiumAuditLog.objects.get(action="disputed").metadata
        self.assertEqual(metadata["invoice_id"], "in_order")
        self.assertEqual(metadata["payment_intent_id"], "pi_order")

    def test_invalid_references_or_status_are_retryable_without_revocation(self):
        variants = ("missing_charge", "wrong_charge", "missing_customer", "unknown_status", "wrong_dispute")
        for variant in variants:
            with self.subTest(variant=variant):
                self.stripe.Webhook.construct_event.return_value["id"] = f"evt_{variant}"
                self.stripe.Webhook.construct_event.return_value["data"]["object"]["charge"] = (
                    "" if variant == "missing_charge" else "ch_order"
                )
                self.stripe.Charge.retrieve.return_value = SimpleNamespace(
                    id="ch_other" if variant == "wrong_charge" else "ch_order",
                    customer="" if variant == "missing_customer" else "cus_order",
                )
                self.stripe.Dispute.retrieve.return_value = SimpleNamespace(
                    id="dp_other" if variant == "wrong_dispute" else "dp_order",
                    charge="ch_order",
                    status="unknown" if variant == "unknown_status" else "won",
                )
                self.assertEqual(self.deliver().status_code, 500)
                self.user.refresh_from_db()
                self.assertTrue(self.user.is_premium)

    def test_unlinked_customer_does_not_read_dispute(self):
        PremiumSubscription.objects.all().delete()
        self.assertEqual(self.deliver().status_code, 200)
        self.stripe.Dispute.retrieve.assert_not_called()
