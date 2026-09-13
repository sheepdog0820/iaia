from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import RequestFactory, TransactionTestCase, override_settings, skipUnlessDBFeature

from accounts.billing import create_checkout_session
from accounts.models import StripeBillingRequest


@override_settings(STRIPE_PREMIUM_PRICE_ID="price_concurrency")
@skipUnlessDBFeature("has_select_for_update")
class BillingCheckoutConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="parallel-billing")
        self.stripe = Mock()
        self.stripe.Customer.create.return_value = SimpleNamespace(id="cus_parallel")
        self.stripe.Subscription.list.return_value.auto_paging_iter.return_value = []
        self.stripe.checkout.Session.list.return_value.auto_paging_iter.return_value = []
        self.session = SimpleNamespace(id="cs_parallel", status="open", url="https://checkout.stripe.test/parallel")
        self.stripe.checkout.Session.create.return_value = self.session
        self.stripe.checkout.Session.retrieve.return_value = self.session

    def purchase(self, barrier=None):
        close_old_connections()
        try:
            request = RequestFactory().post("/api/billing/checkout/")
            request.user = get_user_model().objects.get(pk=self.user.pk)
            if barrier:
                barrier.wait(timeout=10)
            return create_checkout_session(request).id
        finally:
            connections.close_all()

    def test_parallel_first_purchases_create_one_customer_and_one_checkout(self):
        barrier, entered, release = Barrier(2), Event(), Event()

        def delayed_create(**kwargs):
            entered.set()
            if not release.wait(timeout=10):
                raise TimeoutError("test synchronization timed out")
            return self.session

        self.stripe.checkout.Session.create.side_effect = delayed_create
        with patch("accounts.billing.get_stripe", return_value=self.stripe), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.purchase, barrier) for _ in range(2)]
            try:
                self.assertTrue(entered.wait(timeout=10))
            finally:
                release.set()
            self.assertEqual([future.result(timeout=15) for future in futures], ["cs_parallel", "cs_parallel"])
        self.stripe.Customer.create.assert_called_once()
        self.stripe.checkout.Session.create.assert_called_once()
        self.assertEqual(StripeBillingRequest.objects.count(), 2)

    def test_uncertain_checkout_survives_connection_restart(self):
        self.stripe.checkout.Session.create.side_effect = [TimeoutError("response lost"), self.session]
        with patch("accounts.billing.get_stripe", return_value=self.stripe):
            with self.assertRaises(TimeoutError):
                self.purchase()
            self.assertTrue(StripeBillingRequest.objects.filter(operation="checkout", resource_id="").exists())
            self.assertEqual(self.purchase(), "cs_parallel")
        calls = self.stripe.checkout.Session.create.call_args_list
        self.assertEqual(calls[0], calls[1])
