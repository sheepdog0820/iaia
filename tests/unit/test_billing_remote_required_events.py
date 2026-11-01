"""Required event reads must survive an explicit skip of endpoint inspection."""

from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import Mock, patch

import stripe
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.billing_stripe_remote_check import RECENT_OPERATIONAL_EVENT_TYPES


@override_settings(
    STRIPE_PREMIUM_PRICE_ID="price_fixture",
    STRIPE_PREMIUM_YEARLY_PRICE_ID="",
    STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
    STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
    PUBLIC_SITE_URL="https://example.test",
)
class RequiredRecentEventsTests(SimpleTestCase):
    def setUp(self):
        self.client = Mock()
        self.output = StringIO()
        self.now = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
        self.client.v1.prices.retrieve.return_value = {
            "id": "price_fixture",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "currency": "jpy",
            "unit_amount": 480,
            "recurring": {"interval": "month"},
        }
        self.events = [
            {
                "id": f"evt_synthetic_{i}",
                "type": kind,
                "livemode": False,
                "data": {"object": {"cancel_at_period_end": kind == "customer.subscription.updated"}},
            }
            for i, kind in enumerate(RECENT_OPERATIONAL_EVENT_TYPES)
        ]
        self.client.v1.events.list.return_value = {"data": self.events}

    def run_command(self, *arguments):
        with (
            patch("accounts.management.commands.billing_stripe_remote_check.get_stripe", return_value=self.client),
            patch("accounts.management.commands.billing_stripe_remote_check.get_expected_livemode", return_value=False),
            patch("accounts.management.commands.billing_stripe_remote_check.timezone.now", return_value=self.now),
        ):
            call_command("billing_stripe_remote_check", "--skip-portal", *arguments, stdout=self.output)
        return self.output.getvalue()

    def test_missing_required_events_fail_even_when_endpoint_check_is_skipped(self):
        self.client.v1.events.list.return_value = {"data": []}
        with self.assertRaisesMessage(CommandError, "missing recent events"):
            self.run_command("--skip-webhook", "--require-recent-events")
        self.assertNotIn("billing_stripe_remote_check=ok", self.output.getvalue())

    def test_valid_events_are_fetched_and_reported_when_endpoint_is_skipped(self):
        output = self.run_command("--skip-webhook", "--require-recent-events", "--recent-hours", "12")
        self.client.v1.events.list.assert_called_once_with(
            params={
                "limit": 100,
                "created": {"gte": int((self.now - timedelta(hours=12)).timestamp())},
                "types": list(RECENT_OPERATIONAL_EVENT_TYPES),
            }
        )
        self.client.v1.webhook_endpoints.list.assert_not_called()
        self.assertIn("recent_event_ids:", output)
        self.assertIn("recent_cancel_at_period_end_event_ids: evt_synthetic_", output)
        self.assertIn("billing_stripe_remote_check=ok", output)

    def test_mode_mismatch_is_not_hidden_by_endpoint_skip(self):
        self.events[0]["livemode"] = True
        with self.assertRaisesMessage(CommandError, "recent event livemode mismatch"):
            self.run_command("--skip-webhook", "--require-recent-events")

    def test_provider_failure_is_sanitized_without_a_success_marker(self):
        self.client.v1.events.list.side_effect = stripe.APIConnectionError("private-provider-detail")
        with self.assertRaises(CommandError) as context:
            self.run_command("--skip-webhook", "--require-recent-events")
        self.assertNotIn("private-provider-detail", str(context.exception))
        self.assertNotIn("billing_stripe_remote_check=ok", self.output.getvalue())

    def test_events_are_not_read_when_not_required(self):
        self.assertIn("billing_stripe_remote_check=ok", self.run_command("--skip-webhook"))
        self.client.v1.events.list.assert_not_called()

    def test_endpoint_and_event_checks_both_run_when_neither_is_skipped(self):
        self.client.v1.webhook_endpoints.list.return_value = {
            "data": [
                {
                    "url": "https://example.test/api/billing/webhook/",
                    "livemode": False,
                    "status": "enabled",
                    "api_version": settings.STRIPE_API_VERSION,
                    "enabled_events": list(RECENT_OPERATIONAL_EVENT_TYPES),
                }
            ]
        }
        self.assertIn("billing_stripe_remote_check=ok", self.run_command("--require-recent-events"))
        self.client.v1.webhook_endpoints.list.assert_called_once()
        self.client.v1.events.list.assert_called_once()
