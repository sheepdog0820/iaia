from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.billing import handle_checkout_completed
from accounts.models import PremiumSubscription


class StripeCheckoutOrderingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="checkout-order", is_premium=True)
        self.record = PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_order",
            stripe_subscription_id="sub_new",
            subscription_status="active",
            access_source="stripe",
        )
        self.stripe = Mock()
        self.stripe.Subscription.retrieve.return_value = {
            "id": "sub_old",
            "customer": "cus_order",
            "status": "canceled",
        }
        self.session = {
            "client_reference_id": str(self.user.pk),
            "customer": "cus_order",
            "subscription": "sub_old",
        }

    def deliver(self):
        with patch("accounts.billing.get_stripe", return_value=self.stripe):
            return handle_checkout_completed(self.session, event_id="evt_old_checkout")

    def test_old_checkout_cannot_replace_current_subscription(self):
        self.deliver()
        self.record.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.record.stripe_subscription_id, "sub_new")
        self.assertTrue(self.user.is_premium)

    def test_expanded_old_snapshot_is_retrieved_again(self):
        self.record.stripe_subscription_id = "sub_old"
        self.record.save()
        self.session["subscription"] = {"id": "sub_old", "customer": "cus_order", "status": "active"}
        self.deliver()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.stripe.Subscription.retrieve.assert_called_once_with("sub_old")

    def test_customer_mismatch_cannot_reassign_account(self):
        self.session["customer"] = "cus_other"
        with self.assertRaises(ValueError):
            self.deliver()
        self.record.refresh_from_db()
        self.assertEqual(self.record.stripe_customer_id, "cus_order")

    def test_remote_failure_preserves_link_and_retries(self):
        self.stripe.Subscription.retrieve.side_effect = TimeoutError("temporary lookup failure")
        with self.assertRaises(TimeoutError):
            self.deliver()
        self.record.refresh_from_db()
        self.assertEqual(self.record.stripe_subscription_id, "sub_new")
        self.stripe.Subscription.retrieve.side_effect = None
        self.deliver()
        self.record.refresh_from_db()
        self.assertEqual(self.record.stripe_subscription_id, "sub_new")

    def test_invalid_subscription_references_roll_back(self):
        for key, value in (("id", "sub_other"), ("customer", "cus_other")):
            with self.subTest(key=key):
                self.stripe.Subscription.retrieve.return_value = {
                    "id": "sub_old",
                    "customer": "cus_order",
                    "status": "active",
                    key: value,
                }
                with self.assertRaises(ValueError):
                    self.deliver()
                self.record.refresh_from_db()
                self.assertEqual(self.record.stripe_subscription_id, "sub_new")

    def test_missing_reference_is_rejected(self):
        for key in ("customer", "subscription"):
            with self.subTest(key=key):
                original = self.session.pop(key)
                with self.assertRaises(ValueError):
                    self.deliver()
                self.session[key] = original

    def test_unlinked_or_deleted_user_is_ignored(self):
        self.session["client_reference_id"] = ""
        self.assertIsNone(self.deliver())
        self.session["client_reference_id"] = str(self.user.pk + 10000)
        self.assertIsNone(self.deliver())
        self.stripe.Subscription.retrieve.assert_not_called()

    def test_metadata_user_can_link_new_subscription(self):
        self.session["client_reference_id"] = ""
        self.session["metadata"] = {"user_id": str(self.user.pk)}
        self.session["subscription"] = {"id": "sub_fresh"}
        self.stripe.Subscription.retrieve.return_value = {
            "id": "sub_fresh",
            "customer": "cus_order",
            "status": "active",
        }
        self.deliver()
        self.record.refresh_from_db()
        self.assertEqual(self.record.stripe_subscription_id, "sub_fresh")
