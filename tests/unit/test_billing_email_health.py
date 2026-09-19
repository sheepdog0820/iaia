import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import BillingEmailDelivery, PremiumAuditLog, PremiumSubscription


@override_settings(BILLING_EMAIL_DELIVERY_ENABLED=True)
class BillingEmailHealthTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        user = get_user_model().objects.create_user(username="queue-health", email="private@example.test")
        self.subscription = PremiumSubscription.objects.create(user=user)
        audit = PremiumAuditLog.objects.create(user=user, action="payment_failed", source="stripe")
        self.delivery = BillingEmailDelivery.objects.create(
            subscription=self.subscription,
            audit=audit,
            invoice_id="in_private",
            created_at=self.now - timedelta(seconds=601),
            next_attempt_at=self.now + timedelta(seconds=60),
        )

    def run_check(self, unhealthy=False, threshold=600):
        output = StringIO()
        before = list(BillingEmailDelivery.objects.values())
        with patch("django.utils.timezone.now", return_value=self.now), patch("accounts.billing.send_mail") as send:
            if unhealthy:
                with self.assertRaises(CommandError):
                    call_command("check_billing_email_queue", max_pending_age_seconds=threshold, stdout=output)
            else:
                call_command("check_billing_email_queue", max_pending_age_seconds=threshold, stdout=output)
        send.assert_not_called()
        self.assertEqual(before, list(BillingEmailDelivery.objects.values()))
        self.assertNotIn("private", output.getvalue())
        return json.loads(output.getvalue())

    def test_future_retry_does_not_hide_old_pending_delivery(self):
        result = self.run_check(unhealthy=True)
        self.assertFalse(result["healthy"])
        self.assertEqual(result["overdue"], 1)
        self.assertEqual(result["due"], 0)
        self.assertEqual(result["oldest_pending_age_seconds"], 601)

    def test_exact_threshold_is_overdue(self):
        BillingEmailDelivery.objects.update(created_at=self.now - timedelta(seconds=600))
        self.assertEqual(self.run_check(unhealthy=True)["overdue"], 1)

    def test_recent_due_delivery_is_healthy(self):
        BillingEmailDelivery.objects.update(created_at=self.now - timedelta(seconds=599), next_attempt_at=self.now)
        result = self.run_check()
        self.assertTrue(result["healthy"])
        self.assertEqual(result["due"], 1)
        self.assertEqual(result["overdue"], 0)

    def test_terminal_deliveries_are_not_backlog(self):
        for status in ("sent", "canceled"):
            BillingEmailDelivery.objects.update(status=status)
            result = self.run_check()
            self.assertEqual(result["pending"], 0)
            self.assertIsNone(result["oldest_pending_age_seconds"])

    @override_settings(BILLING_EMAIL_DELIVERY_ENABLED=False)
    def test_disabled_delivery_is_unhealthy_even_with_empty_queue(self):
        BillingEmailDelivery.objects.all().delete()
        self.assertFalse(self.run_check(unhealthy=True)["enabled"])

    def test_positive_threshold_is_required(self):
        for threshold in (0, -1):
            with self.subTest(threshold=threshold), self.assertNumQueries(0), self.assertRaises(CommandError):
                call_command("check_billing_email_queue", max_pending_age_seconds=threshold, stdout=StringIO())

    def test_future_creation_does_not_produce_negative_age(self):
        BillingEmailDelivery.objects.update(created_at=self.now + timedelta(seconds=1))
        self.assertEqual(self.run_check()["oldest_pending_age_seconds"], 0)
