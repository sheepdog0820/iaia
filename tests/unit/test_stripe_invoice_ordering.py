from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    BillingEmailDelivery,
    PremiumAuditLog,
    PremiumSubscription,
    StripeInvoiceState,
    StripeWebhookEvent,
)


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StripeInvoiceOrderingTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="invoice-order", email="invoice@example.invalid")
        self.record = PremiumSubscription.objects.create(user=user, stripe_customer_id="cus_order")
        self.stripe = Mock()

    def deliver(self, event_id, event_type, invoice_id, current_status):
        self.stripe.Webhook.construct_event.return_value = {
            "id": event_id,
            "type": event_type,
            "data": {"object": {"id": invoice_id, "customer": "cus_order"}},
        }
        self.stripe.Invoice.retrieve.return_value = SimpleNamespace(
            id=invoice_id, customer="cus_order", status=current_status
        )
        with (
            patch("accounts.views.billing_views.get_stripe", return_value=self.stripe),
            patch("accounts.billing.get_stripe", return_value=self.stripe),
        ):
            return APIClient().post("/api/billing/webhook/", {}, format="json", HTTP_STRIPE_SIGNATURE="test")

    def test_delayed_failure_after_payment_does_not_warn_or_email(self):
        self.assertEqual(self.deliver("evt_late", "invoice.payment_failed", "in_paid", "paid").status_code, 200)
        self.record.refresh_from_db()
        self.assertIsNone(self.record.last_payment_failed_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_other_invoice_success_does_not_clear_outstanding_failure(self):
        self.deliver("evt_fail_b", "invoice.payment_failed", "in_b", "open")
        self.deliver("evt_paid_a", "invoice.payment_succeeded", "in_a", "paid")
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.last_payment_failed_at)
        self.assertEqual(BillingEmailDelivery.objects.count(), 1)
        self.deliver("evt_paid_b", "invoice.payment_succeeded", "in_b", "paid")
        self.record.refresh_from_db()
        self.assertIsNone(self.record.last_payment_failed_at)

    def test_distinct_failure_events_for_one_invoice_send_one_warning(self):
        self.deliver("evt_fail_1", "invoice.payment_failed", "in_b", "open")
        self.deliver("evt_fail_2", "invoice.payment_failed", "in_b", "open")
        self.assertEqual(BillingEmailDelivery.objects.count(), 1)

    def test_lookup_failure_remains_retryable(self):
        self.stripe.Invoice.retrieve.side_effect = TimeoutError("temporary read failure")
        response = self.deliver("evt_retry", "invoice.payment_failed", "in_b", "open")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(StripeWebhookEvent.objects.get().processing_status, "failed")
        self.stripe.Invoice.retrieve.side_effect = None
        self.assertEqual(self.deliver("evt_retry", "invoice.payment_failed", "in_b", "open").status_code, 200)

    def test_legacy_failure_is_seeded_without_being_cleared_by_other_invoice(self):
        self.record.last_payment_failed_at = timezone.now()
        self.record.save()
        PremiumAuditLog.objects.create(
            user=self.record.user, source="stripe", action="payment_failed", metadata={"invoice_id": "in_old"}
        )
        self.stripe.Invoice.retrieve.side_effect = lambda invoice_id: SimpleNamespace(
            id=invoice_id, customer="cus_order", status="open" if invoice_id == "in_old" else "paid"
        )
        self.assertEqual(self.deliver("evt_new_paid", "invoice.payment_succeeded", "in_new", "paid").status_code, 200)
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.last_payment_failed_at)
        self.assertTrue(StripeInvoiceState.objects.get(invoice_id="in_old").payment_failed)
        self.assertEqual(len(mail.outbox), 0)

    def test_unattributable_legacy_warning_is_preserved_for_investigation(self):
        self.record.last_payment_failed_at = timezone.now()
        self.record.save()
        self.assertEqual(self.deliver("evt_unknown", "invoice.payment_succeeded", "in_new", "paid").status_code, 500)
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.last_payment_failed_at)
        self.assertFalse(StripeInvoiceState.objects.exists())

    def test_history_recovers_warning_previously_cleared_by_another_invoice(self):
        PremiumAuditLog.objects.create(
            user=self.record.user, source="stripe", action="payment_failed", metadata={"invoice_id": "in_old"}
        )
        self.stripe.Invoice.retrieve.side_effect = lambda invoice_id: SimpleNamespace(
            id=invoice_id, customer="cus_order", status="open" if invoice_id == "in_old" else "paid"
        )
        self.assertEqual(self.deliver("evt_reconcile", "invoice.payment_succeeded", "in_new", "paid").status_code, 200)
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.last_payment_failed_at)

    def test_unlinked_customer_is_ignored_without_invoice_access(self):
        self.record.delete()
        self.assertEqual(self.deliver("evt_unlinked", "invoice.payment_failed", "in_unknown", "open").status_code, 200)
        self.stripe.Invoice.retrieve.assert_not_called()

    def test_wrong_customer_or_unexpected_invoice_status_never_changes_state(self):
        for index, (customer, status) in enumerate((("cus_other", "paid"), ("cus_order", "draft"))):
            with self.subTest(customer=customer, status=status):
                self.stripe.Invoice.retrieve.side_effect = lambda invoice_id: SimpleNamespace(
                    id=invoice_id, customer=customer, status=status
                )
                self.assertEqual(
                    self.deliver(f"evt_invalid_{index}", "invoice.payment_failed", "in_bad", status).status_code, 500
                )
                self.assertFalse(StripeInvoiceState.objects.exists())

    def test_multiple_outstanding_failures_require_each_invoice_to_be_resolved(self):
        self.deliver("evt_fa", "invoice.payment_failed", "in_a", "open")
        self.deliver("evt_fb", "invoice.payment_failed", "in_b", "uncollectible")
        self.deliver("evt_pa", "invoice.payment_succeeded", "in_a", "paid")
        self.record.refresh_from_db()
        self.assertIsNotNone(self.record.last_payment_failed_at)
        self.deliver("evt_vb", "invoice.payment_failed", "in_b", "void")
        self.record.refresh_from_db()
        self.assertIsNone(self.record.last_payment_failed_at)
        self.assertEqual(BillingEmailDelivery.objects.count(), 2)
