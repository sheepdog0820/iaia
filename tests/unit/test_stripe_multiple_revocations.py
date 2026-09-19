from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.billing import mark_refund_or_dispute, sync_subscription_object
from accounts.models import PremiumAuditLog, PremiumSubscription


class StripeMultipleRevocationsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="multiple-disputes", is_premium=True)
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_multi",
            stripe_subscription_id="sub_multi",
            subscription_status="active",
            access_source="stripe",
        )
        stripe = Mock()
        stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_multi", customer="cus_multi", status="active"
        )
        self.patch = patch("accounts.billing.get_stripe", return_value=stripe)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.sequence = 0

    def event(self, object_id, event_type, status=""):
        self.sequence += 1
        mark_refund_or_dispute(
            {"id": object_id, "customer": "cus_multi", "status": status},
            event_type=event_type,
            event_id=f"evt_multi_{self.sequence}",
        )
        self.user.refresh_from_db()

    def test_winning_one_dispute_keeps_other_open_dispute_revoked(self):
        self.event("dp_a", "charge.dispute.created", "needs_response")
        self.event("dp_b", "charge.dispute.created", "needs_response")
        self.event("dp_a", "charge.dispute.closed", "won")
        self.assertFalse(self.user.is_premium)
        self.assertFalse(PremiumAuditLog.objects.filter(action="restored").exists())
        self.event("dp_b", "charge.dispute.closed", "won")
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.filter(action="restored").count(), 1)

    def test_dispute_win_does_not_clear_an_earlier_refund(self):
        self.event("ch_refund", "charge.refunded")
        self.event("dp_b", "charge.dispute.created", "needs_response")
        self.event("dp_b", "charge.dispute.closed", "won")
        self.assertFalse(self.user.is_premium)

    def test_other_lost_dispute_remains_revoked(self):
        self.event("dp_a", "charge.dispute.closed", "lost")
        self.event("dp_b", "charge.dispute.created", "needs_response")
        self.event("dp_b", "charge.dispute.closed", "won")
        self.assertFalse(self.user.is_premium)

    def test_previous_refund_resolved_before_access_regrant_does_not_block_forever(self):
        self.event("ch_old_refund", "charge.refunded")
        record = PremiumSubscription.objects.get(user=self.user)
        record.revoked_at = None
        record.revoked_reason = ""
        record.save(update_fields=["revoked_at", "revoked_reason"])
        sync_subscription_object({"id": "sub_multi", "customer": "cus_multi", "status": "active"})
        self.event("dp_new", "charge.dispute.created", "needs_response")
        self.event("dp_new", "charge.dispute.closed", "won")
        self.assertTrue(self.user.is_premium)

    def test_non_revoking_refund_does_not_prevent_dispute_restoration(self):
        with override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False):
            self.event("ch_informational", "charge.refunded")
        self.event("dp_new", "charge.dispute.created", "needs_response")
        self.event("dp_new", "charge.dispute.closed", "won")
        self.assertTrue(self.user.is_premium)

    def test_incomplete_old_dispute_history_does_not_authorize_restoration(self):
        PremiumAuditLog.objects.create(user=self.user, source="stripe", action="disputed", metadata={})
        self.event("dp_new", "charge.dispute.created", "needs_response")
        self.event("dp_new", "charge.dispute.closed", "won")
        self.assertFalse(self.user.is_premium)

    def test_win_without_dispute_id_does_not_authorize_restoration(self):
        self.event("dp_a", "charge.dispute.created", "needs_response")
        self.event("", "charge.dispute.closed", "won")
        self.assertFalse(self.user.is_premium)

    def test_non_revoking_dispute_history_is_informational(self):
        with override_settings(STRIPE_REVOKE_ON_REFUND_OR_DISPUTE=False):
            self.event("dp_information", "charge.dispute.created", "needs_response")
            self.event("", "charge.dispute.created", "needs_response")
        self.event("dp_new", "charge.dispute.created", "needs_response")
        self.event("dp_new", "charge.dispute.closed", "won")
        self.assertTrue(self.user.is_premium)
