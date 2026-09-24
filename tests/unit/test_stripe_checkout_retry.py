from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from accounts.billing import create_checkout_session, get_or_create_stripe_customer
from accounts.models import PremiumSubscription, StripeBillingRequest


@override_settings(STRIPE_PREMIUM_PRICE_ID="price_month", STRIPE_PREMIUM_YEARLY_PRICE_ID="price_year")
class StripeCheckoutRetryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="checkout-retry")
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_retry")
        self.request = RequestFactory().post("/api/billing/checkout/")
        self.request.user = self.user
        self.stripe = Mock()
        self.stripe.Subscription.list.return_value.auto_paging_iter.return_value = iter([])
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = iter([])
        self.session = SimpleNamespace(id="cs_retry", status="open", url="https://checkout.stripe.test/retry")
        self.stripe.checkout.Session.create.return_value = self.session
        self.stripe.checkout.Session.retrieve.return_value = self.session
        self.patch = patch("accounts.billing.get_stripe", return_value=self.stripe)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_double_click_reuses_open_session(self):
        first = create_checkout_session(self.request)
        second = create_checkout_session(self.request)
        self.assertEqual(first.id, second.id)
        self.stripe.checkout.Session.create.assert_called_once()

    def test_uncertain_response_retries_same_key_and_parameters(self):
        self.stripe.checkout.Session.create.side_effect = [TimeoutError("response lost"), self.session]
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request)
        create_checkout_session(self.request)
        calls = self.stripe.checkout.Session.create.call_args_list
        self.assertTrue(calls[0].kwargs.get("idempotency_key"))
        self.assertEqual(calls[0], calls[1])

    def test_remote_subscription_blocks_purchase_before_webhook(self):
        self.stripe.Subscription.list.return_value.auto_paging_iter.return_value = iter(
            [SimpleNamespace(status="past_due")]
        )
        with self.assertRaisesRegex(ValueError, "契約"):
            create_checkout_session(self.request)
        self.stripe.checkout.Session.create.assert_not_called()

    def test_plan_change_expires_previous_checkout_before_creating_new_one(self):
        create_checkout_session(self.request)
        self.stripe.checkout.Session.create.return_value = SimpleNamespace(
            id="cs_year", status="open", url="https://checkout.stripe.test/year"
        )
        create_checkout_session(self.request, "yearly")
        self.stripe.checkout.Session.expire.assert_called_once_with("cs_retry")
        calls = self.stripe.checkout.Session.create.call_args_list
        self.assertNotEqual(calls[0].kwargs["idempotency_key"], calls[1].kwargs["idempotency_key"])
        self.assertEqual(calls[1].kwargs["line_items"], [{"price": "price_year", "quantity": 1}])

    def test_failed_expiration_does_not_create_another_checkout(self):
        create_checkout_session(self.request)
        self.stripe.checkout.Session.expire.side_effect = TimeoutError("expiration uncertain")
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request, "yearly")
        self.stripe.checkout.Session.create.assert_called_once()

    def test_expired_checkout_allows_new_attempt(self):
        create_checkout_session(self.request)
        self.stripe.checkout.Session.retrieve.return_value = SimpleNamespace(id="cs_retry", status="expired")
        create_checkout_session(self.request)
        calls = self.stripe.checkout.Session.create.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0].kwargs["idempotency_key"], calls[1].kwargs["idempotency_key"])

    def test_completed_checkout_is_not_reused_as_a_new_purchase(self):
        create_checkout_session(self.request)
        self.stripe.checkout.Session.retrieve.return_value = SimpleNamespace(
            id="cs_retry", status="complete", subscription="sub_retry"
        )
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(status="active")
        with self.assertRaisesRegex(ValueError, "契約"):
            create_checkout_session(self.request)
        self.stripe.checkout.Session.create.assert_called_once()

    def test_completed_then_canceled_subscription_allows_new_purchase(self):
        create_checkout_session(self.request)
        self.stripe.checkout.Session.retrieve.return_value = SimpleNamespace(
            id="cs_retry", status="complete", subscription="sub_retry"
        )
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(status="canceled")
        create_checkout_session(self.request)
        self.assertEqual(self.stripe.checkout.Session.create.call_count, 2)

    def test_old_unresolved_request_is_not_recreated_after_key_retention(self):
        self.stripe.checkout.Session.create.side_effect = TimeoutError("response lost")
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request)
        StripeBillingRequest.objects.update(created_at=timezone.now() - timedelta(hours=24))
        with self.assertRaisesRegex(ValueError, "お問い合わせ"):
            create_checkout_session(self.request)
        self.stripe.checkout.Session.create.assert_called_once()

    def test_stripe_read_failure_stops_purchase(self):
        self.stripe.Subscription.list.side_effect = TimeoutError("unavailable")
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request)
        self.stripe.checkout.Session.create.assert_not_called()

    def test_customer_retry_keeps_key_and_original_profile(self):
        PremiumSubscription.objects.update(stripe_customer_id="")
        self.stripe.Customer.create.side_effect = [TimeoutError("response lost"), SimpleNamespace(id="cus_recovered")]
        with self.assertRaises(TimeoutError):
            get_or_create_stripe_customer(self.user)
        self.user.email = "changed@example.invalid"
        record = get_or_create_stripe_customer(self.user)
        self.assertEqual(record.stripe_customer_id, "cus_recovered")
        calls = self.stripe.Customer.create.call_args_list
        self.assertTrue(calls[0].kwargs["idempotency_key"])
        self.assertEqual(calls[0], calls[1])
        get_or_create_stripe_customer(self.user)
        self.assertEqual(self.stripe.Customer.create.call_count, 2)

    def test_legacy_open_checkout_must_expire_before_purchase(self):
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = iter(
            [SimpleNamespace(id="cs_old")]
        )
        self.stripe.checkout.Session.expire.side_effect = TimeoutError("expiration uncertain")
        with self.assertRaises(TimeoutError):
            create_checkout_session(self.request)
        self.stripe.checkout.Session.expire.assert_called_once_with("cs_old")
        self.stripe.checkout.Session.create.assert_not_called()


from datetime import timedelta
