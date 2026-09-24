from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.billing import mark_invoice_payment_failed
from accounts.billing_email import deliver_billing_email, dispatch_billing_emails
from accounts.models import BillingEmailDelivery, PremiumSubscription, StripeInvoiceState


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BillingEmailDeliveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mail-proof", email="mail@example.test")
        self.record = PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_mail")

    def fail_payment(self):
        return mark_invoice_payment_failed({"id": "in_mail", "customer": "cus_mail"}, event_id="evt_mail")

    def test_rollback_never_sends_payment_email(self):
        with patch("accounts.billing.send_mail", return_value=1) as send:
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.fail_payment()
                raise RuntimeError("subsequent webhook write failed")
        send.assert_not_called()
        self.assertFalse(BillingEmailDelivery.objects.exists())

    def test_webhook_processing_only_queues_email(self):
        with patch("accounts.billing.send_mail", return_value=1) as send:
            self.fail_payment()
        send.assert_not_called()
        self.assertEqual(BillingEmailDelivery.objects.get().status, "pending")

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_failed_delivery_survives_and_retry_sends_once(self):
        self.fail_payment()
        delivery = BillingEmailDelivery.objects.get()
        with patch("accounts.billing_email.send_payment_failed_email", side_effect=TimeoutError("secret@example.test")):
            self.assertEqual(deliver_billing_email(delivery.pk), "pending")
        delivery.refresh_from_db()
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.last_error_code, "transport_error")
        with patch("accounts.billing_email.send_payment_failed_email", return_value=True) as send:
            self.assertEqual(dispatch_billing_emails(), {})
            send.assert_not_called()
            BillingEmailDelivery.objects.filter(pk=delivery.pk).update(next_attempt_at=timezone.now())
            self.assertEqual(dispatch_billing_emails(), {"sent": 1})
            self.assertEqual(dispatch_billing_emails(), {})
            self.assertEqual(deliver_billing_email(delivery.pk), "sent")
            send.assert_called_once()
        delivery.refresh_from_db()
        self.assertEqual(delivery.attempts, 2)
        self.assertIsNotNone(delivery.sent_at)
        self.assertTrue(delivery.audit.metadata["email_sent"])

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_false_result_is_retryable(self):
        self.fail_payment()
        with patch("accounts.billing_email.send_payment_failed_email", return_value=False):
            self.assertEqual(dispatch_billing_emails(), {"pending": 1})
        self.assertEqual(BillingEmailDelivery.objects.get().last_error_code, "not_accepted")

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_recovered_invoice_is_not_sent_even_with_other_failure(self):
        self.fail_payment()
        StripeInvoiceState.objects.create(
            subscription=self.record, invoice_id="in_mail", status="paid", payment_failed=False
        )
        with patch("accounts.billing_email.send_payment_failed_email") as send:
            self.assertEqual(dispatch_billing_emails(), {"canceled": 1})
        send.assert_not_called()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_recovery_cancels_queued_warning(self):
        self.fail_payment()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(last_payment_failed_at=None)
        with patch("accounts.billing_email.send_payment_failed_email") as send:
            self.assertEqual(dispatch_billing_emails(), {"canceled": 1})
        send.assert_not_called()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_new_failure_supersedes_old_pending_warning(self):
        self.fail_payment()
        self.fail_payment()
        with patch("accounts.billing_email.send_payment_failed_email", return_value=True) as send:
            self.assertEqual(dispatch_billing_emails(), {"canceled": 1, "sent": 1})
        send.assert_called_once()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=False)
    def test_disabled_delivery_keeps_pending_without_sending(self):
        self.fail_payment()
        with patch("accounts.billing_email.send_payment_failed_email") as send:
            self.assertEqual(dispatch_billing_emails(), {"disabled": 1})
            self.assertEqual(deliver_billing_email(BillingEmailDelivery.objects.get().pk), "disabled")
        send.assert_not_called()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_deleted_delivery_is_safe(self):
        self.assertEqual(deliver_billing_email(99999), "missing")

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_account_deleted_between_discovery_and_lock_is_safe(self):
        self.fail_payment()
        delivery_id = BillingEmailDelivery.objects.get().pk
        real_select = PremiumSubscription.objects.select_for_update

        def delete_before_lock(*args, **kwargs):
            self.record.delete()
            return real_select(*args, **kwargs)

        with patch.object(PremiumSubscription.objects, "select_for_update", side_effect=delete_before_lock):
            with patch("accounts.billing_email.send_payment_failed_email") as send:
                self.assertEqual(deliver_billing_email(delivery_id), "missing")
        send.assert_not_called()

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_audit_failure_rolls_back_queued_email(self):
        with patch("accounts.billing.create_premium_audit_log", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.fail_payment()
        self.record.refresh_from_db()
        self.assertIsNone(self.record.last_payment_failed_at)
        self.assertFalse(BillingEmailDelivery.objects.exists())

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_command_and_task_use_persisted_queue(self):
        from accounts.tasks import dispatch_billing_emails as task

        self.fail_payment()
        output = StringIO()
        with patch("accounts.billing_email.send_payment_failed_email", return_value=True) as send:
            call_command("dispatch_billing_emails", stdout=output)
            self.assertEqual(task.run(), {})
        send.assert_called_once()
        self.assertIn("'sent': 1", output.getvalue())

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
    def test_status_command_is_read_only(self):
        self.fail_payment()
        output = StringIO()
        with patch("accounts.billing_email.send_payment_failed_email") as send:
            call_command("dispatch_billing_emails", status=True, stdout=output)
        send.assert_not_called()
        self.assertIn("'pending': 1", output.getvalue())
        self.assertNotIn(self.user.email, output.getvalue())
