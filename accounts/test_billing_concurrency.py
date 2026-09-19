from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import RequestFactory, TransactionTestCase, override_settings, skipUnlessDBFeature

from accounts.billing import (
    create_checkout_session,
    handle_checkout_completed,
    mark_refund_or_dispute,
    reconcile_dispute_event,
    reconcile_invoice_payment,
)
from accounts.models import PremiumAuditLog, PremiumSubscription, StripeBillingRequest, StripeInvoiceState


@override_settings(STRIPE_PREMIUM_PRICE_ID="price_concurrency")
@skipUnlessDBFeature("has_select_for_update")
class BillingCheckoutConcurrencyTests(TransactionTestCase):
    def test_deletion_lock_prevents_waiting_checkout_creation(self):
        from accounts.billing_deletion import delete_account_after_billing_check

        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_parallel")
        deletion_checking = Event()
        purchase_started = Event()

        def list_sessions(**kwargs):
            deletion_checking.set()
            if not purchase_started.wait(timeout=10):
                raise TimeoutError("purchase did not start")
            return Mock(auto_paging_iter=Mock(return_value=[]))

        self.stripe.checkout.Session.list.side_effect = list_sessions

        def remove_account():
            close_old_connections()
            try:
                delete_account_after_billing_check(get_user_model().objects.get(pk=self.user.pk))
            finally:
                connections.close_all()

        def purchase_after_check_starts():
            close_old_connections()
            try:
                if not deletion_checking.wait(timeout=10):
                    raise TimeoutError("deletion did not start")
                request = RequestFactory().post("/api/billing/checkout-session/")
                request.user = get_user_model().objects.get(pk=self.user.pk)
                purchase_started.set()
                try:
                    create_checkout_session(request)
                except (PremiumSubscription.DoesNotExist, get_user_model().DoesNotExist):
                    return
                self.fail("Checkout must not be created after account deletion")
            finally:
                connections.close_all()

        with (
            patch("accounts.billing.get_stripe", return_value=self.stripe),
            patch("accounts.billing_deletion.get_stripe", return_value=self.stripe),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            deletion = pool.submit(remove_account)
            purchase = pool.submit(purchase_after_check_starts)
            deletion.result(timeout=15)
            purchase.result(timeout=15)
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.stripe.checkout.Session.create.assert_not_called()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_parallel_billing_email_workers_send_once(self):
        from accounts.billing import mark_invoice_payment_failed
        from accounts.billing_email import dispatch_billing_emails
        from accounts.models import BillingEmailDelivery

        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_parallel")
        mark_invoice_payment_failed({"id": "in_parallel", "customer": "cus_parallel"}, event_id="evt_email")
        barrier = Barrier(2)

        def dispatch():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return dispatch_billing_emails()
            finally:
                connections.close_all()

        with patch("accounts.billing_email.send_payment_failed_email", return_value=True) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(dispatch) for _ in range(2)]
                for future in futures:
                    future.result(timeout=15)
        send.assert_called_once()
        delivery = BillingEmailDelivery.objects.get()
        self.assertEqual(delivery.status, "sent")
        self.assertEqual(delivery.attempts, 1)

    def test_parallel_checkout_completion_grants_access_once(self):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_parallel")
        self.stripe.Subscription.retrieve.return_value = {
            "id": "sub_parallel",
            "customer": "cus_parallel",
            "status": "active",
        }
        barrier = Barrier(2)

        def deliver(event_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                handle_checkout_completed(
                    {
                        "client_reference_id": str(self.user.pk),
                        "customer": "cus_parallel",
                        "subscription": "sub_parallel",
                    },
                    event_id=event_id,
                )
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=self.stripe), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(deliver, event_id) for event_id in ("evt_checkout_a", "evt_checkout_b")]
            for future in futures:
                future.result(timeout=15)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.filter(action="granted").count(), 1)

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

    def test_parallel_invoices_preserve_another_invoices_failure(self):
        record = PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_parallel")
        barrier = Barrier(2)
        self.stripe.Invoice.retrieve.side_effect = lambda invoice_id: SimpleNamespace(
            id=invoice_id, customer="cus_parallel", status="open" if invoice_id == "in_failed" else "paid"
        )

        def deliver(invoice_id, event_type):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                reconcile_invoice_payment(
                    {"id": invoice_id, "customer": "cus_parallel"},
                    event_type=event_type,
                    event_id=f"evt_{invoice_id}",
                )
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=self.stripe), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(deliver, "in_failed", "invoice.payment_failed"),
                pool.submit(deliver, "in_paid", "invoice.payment_succeeded"),
            ]
            for future in futures:
                future.result(timeout=15)
        record.refresh_from_db()
        self.assertIsNotNone(record.last_payment_failed_at)
        self.assertEqual(StripeInvoiceState.objects.filter(payment_failed=True).count(), 1)
        self.assertEqual(StripeInvoiceState.objects.count(), 2)

    def test_parallel_dispute_wins_restore_once_after_both_holds_are_resolved(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_parallel",
            stripe_subscription_id="sub_parallel",
            subscription_status="active",
            access_source="stripe",
        )
        for dispute_id in ("dp_a", "dp_b"):
            mark_refund_or_dispute(
                {"id": dispute_id, "customer": "cus_parallel", "status": "needs_response"},
                event_type="charge.dispute.created",
                event_id=f"evt_created_{dispute_id}",
            )
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_parallel", customer="cus_parallel", status="active"
        )
        barrier = Barrier(2)

        def close_dispute(dispute_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                mark_refund_or_dispute(
                    {"id": dispute_id, "customer": "cus_parallel", "status": "won"},
                    event_type="charge.dispute.closed",
                    event_id=f"evt_won_{dispute_id}",
                )
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=self.stripe), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(close_dispute, dispute_id) for dispute_id in ("dp_a", "dp_b")]
            for future in futures:
                future.result(timeout=15)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.filter(action="restored").count(), 1)
        self.stripe.Subscription.retrieve.assert_called_once()

    def test_parallel_old_and_new_dispute_events_use_current_state(self):
        PremiumSubscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_parallel",
            stripe_subscription_id="sub_parallel",
            subscription_status="active",
            access_source="stripe",
        )
        mark_refund_or_dispute(
            {"id": "dp_parallel", "customer": "cus_parallel", "status": "needs_response"},
            event_type="charge.dispute.created",
            event_id="evt_initial",
        )
        self.stripe.Charge.retrieve.return_value = SimpleNamespace(id="ch_parallel", customer="cus_parallel")
        self.stripe.Dispute.retrieve.return_value = SimpleNamespace(
            id="dp_parallel", charge="ch_parallel", status="won"
        )
        self.stripe.Subscription.retrieve.return_value = SimpleNamespace(
            id="sub_parallel", customer="cus_parallel", status="active"
        )
        barrier = Barrier(2)

        def deliver(event_type):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                reconcile_dispute_event(
                    {"id": "dp_parallel", "charge": "ch_parallel"},
                    event_type=event_type,
                    event_id=event_type,
                )
            finally:
                connections.close_all()

        with patch("accounts.billing.get_stripe", return_value=self.stripe), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(deliver, kind) for kind in ("charge.dispute.created", "charge.dispute.closed")]
            for future in futures:
                future.result(timeout=15)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertEqual(PremiumAuditLog.objects.filter(action="restored").count(), 1)
