"""Endive requests and signed snapshot events through the real SDK, without I/O."""

import hashlib
import hmac
import json
import time
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.billing import get_stripe
from accounts.management.commands.billing_preflight import REQUIRED_WEBHOOK_EVENTS
from accounts.management.commands.billing_stripe_remote_check import validate_webhook_endpoints
from accounts.models import PremiumSubscription, StripeBillingRequest, StripeInvoiceState, StripeWebhookEvent
from tests.integration.test_stripe_client_transport import listing
from tests.unit.test_stripe_client_isolation import FixtureTransport, RealStripeClient

ENDIVE = "2026-09-30.endive"


class StripeApiConfigurationTests(SimpleTestCase):
    def test_other_destination_does_not_affect_target_version(self):
        url = "https://example.test/api/billing/webhook/"
        endpoint = {"url": url, "status": "enabled", "enabled_events": ["*"], "api_version": ENDIVE}
        self.assertEqual(
            validate_webhook_endpoints(
                {"data": [{**endpoint, "url": "https://other.example.test/", "api_version": None}, endpoint]},
                url,
                expected_api_version=ENDIVE,
            ),
            [],
        )

    def test_helper_can_check_events_without_version_but_command_requires_pin(self):
        url = "https://example.test/api/billing/webhook/"
        endpoint = {"url": url, "status": "enabled", "enabled_events": ["*"]}
        self.assertEqual(validate_webhook_endpoints({"data": [endpoint]}, url), [])

    def test_duplicate_enabled_endpoints_must_all_use_pinned_version(self):
        url = "https://example.test/api/billing/webhook/"
        endpoint = {"url": url, "status": "enabled", "enabled_events": ["*"], "api_version": ENDIVE}
        errors = validate_webhook_endpoints(
            {"data": [endpoint, {**endpoint, "api_version": "2026-02-25.clover"}]},
            url,
            expected_api_version=ENDIVE,
        )
        self.assertTrue(errors)
        self.assertIn("webhook endpoint API version mismatch", errors[0])

    def test_disabled_duplicate_does_not_emit_mismatched_version(self):
        url = "https://example.test/api/billing/webhook/"
        endpoint = {"url": url, "status": "enabled", "enabled_events": ["*"], "api_version": ENDIVE}
        errors = validate_webhook_endpoints(
            {"data": [endpoint, {**endpoint, "status": "disabled", "api_version": "2026-02-25.clover"}]},
            url,
            expected_api_version=ENDIVE,
        )
        self.assertEqual(errors, [])

    def test_application_declares_endive_as_default(self):
        self.assertEqual(getattr(settings, "STRIPE_API_VERSION", None), ENDIVE)

    @override_settings(STRIPE_SECRET_KEY="synthetic-api-upgrade")  # nosec B106
    def test_default_client_sends_explicit_endive_header(self):
        transport = FixtureTransport()
        transport.responses = [{"id": "cus_version", "object": "customer"}]
        with patch(
            "stripe.StripeClient",
            side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=transport),
        ):
            get_stripe().v1.customers.retrieve("cus_version")
        self.assertEqual(transport.calls[0][2]["Stripe-Version"], ENDIVE)

    def test_required_events_include_pause_resume_and_paid_invoice(self):
        self.assertTrue(
            {"customer.subscription.paused", "customer.subscription.resumed", "invoice.paid"}
            <= set(REQUIRED_WEBHOOK_EVENTS)
        )

    @override_settings(STRIPE_SECRET_KEY="synthetic-api-upgrade", STRIPE_API_VERSION="")  # nosec B106
    def test_blank_api_pin_fails_without_using_sdk_or_account_default(self):
        with patch("stripe.StripeClient") as factory:
            with self.assertRaisesMessage(ImproperlyConfigured, "STRIPE_API_VERSION is required"):
                get_stripe()
        factory.assert_not_called()

    def test_remote_gate_requires_pinned_webhook_version_even_for_wildcard_events(self):
        url = "https://example.test/api/billing/webhook/"
        endpoint = {"url": url, "status": "enabled", "enabled_events": ["*"], "api_version": ENDIVE}
        self.assertEqual(validate_webhook_endpoints({"data": [endpoint]}, url, expected_api_version=ENDIVE), [])
        for version in (None, "2026-02-25.clover", "2026-09-30.preview"):
            with self.subTest(version=version):
                errors = validate_webhook_endpoints(
                    {"data": [{**endpoint, "api_version": version}]}, url, expected_api_version=ENDIVE
                )
                self.assertTrue(errors)
                self.assertIn("webhook endpoint API version mismatch", errors[0])


@override_settings(
    STRIPE_SECRET_KEY="synthetic-api-upgrade",  # nosec B106
    STRIPE_API_VERSION=ENDIVE,
    STRIPE_CHECKOUT_ENABLED=True,
    STRIPE_PREMIUM_PRICE_ID="price_month",
    STRIPE_PREMIUM_YEARLY_PRICE_ID="price_year",
    STRIPE_WEBHOOK_SECRET="synthetic-webhook-upgrade",  # nosec B106
)
class StripeEndiveIntegrationTests(TestCase):
    def setUp(self):
        self.transport = FixtureTransport()
        patcher = patch(
            "stripe.StripeClient",
            side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=self.transport),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user(username="api-upgrade", email="fixture@example.test")
        self.record = PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_upgrade")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.session = {
            "id": "cs_upgrade",
            "object": "checkout.session",
            "status": "open",
            "url": "https://example.test/pay",
        }

    def checkout(self, plan="monthly"):
        return self.client.post(reverse("billing-checkout-session"), {"plan": plan}, format="json")

    def create_session(self):
        self.transport.responses = [
            listing("/v1/subscriptions"),
            listing("/v1/checkout/sessions"),
            listing("/v1/subscriptions"),
            self.session,
        ]
        response = self.checkout()
        self.assertEqual(response.status_code, 200, response.data)
        return StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")

    def test_new_identifier_is_saved_and_serialized_once(self):
        attempt = self.create_session()
        identifier = attempt.parameters.get("integration_identifier", "")
        self.assertRegex(identifier, r"^tableno_checkout_[a-zA-Z]{8}$")
        body = parse_qs(self.transport.calls[-1][3])
        self.assertEqual(body["integration_identifier"], [identifier])
        self.assertEqual(self.transport.calls[-1][2]["Stripe-Version"], ENDIVE)
        self.assertNotIn("payment_method_types", body)

    def test_repeat_reuses_session_without_generating_identifier_or_expiring(self):
        attempt = self.create_session()
        before = dict(attempt.parameters)
        self.transport.responses = [listing("/v1/subscriptions"), self.session]
        response = self.checkout()
        self.assertEqual(response.status_code, 200, response.data)
        attempt.refresh_from_db()
        self.assertEqual(attempt.parameters, before)
        self.assertEqual([method for method, _, _, _ in self.transport.calls].count("post"), 1)

    def test_uncertain_write_resends_same_identifier_body_and_key(self):
        self.transport.status = 500
        self.transport.responses = [
            listing("/v1/subscriptions"),
            listing("/v1/checkout/sessions"),
            listing("/v1/subscriptions"),
            {"error": {"type": "api_error", "message": "synthetic lost response"}},
        ]
        # Only Checkout fails; successful read responses retain their HTTP status.
        original_request = self.transport.request

        def request(method, *args, **kwargs):
            self.transport.status = 500 if method == "post" else 200
            return original_request(method, *args, **kwargs)

        with patch.object(self.transport, "request", side_effect=request):
            response = self.checkout()
        self.assertEqual(response.status_code, 503)
        attempt = StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")
        self.assertRegex(attempt.parameters.get("integration_identifier", ""), r"_[a-zA-Z]{8}$")
        first = self.transport.calls[-1]
        self.transport.status = 200
        self.transport.responses = [listing("/v1/subscriptions"), self.session]
        response = self.checkout()
        self.assertEqual(response.status_code, 200, response.data)
        second = self.transport.calls[-1]
        self.assertEqual(first[3], second[3])
        self.assertEqual(first[2]["Idempotency-Key"], second[2]["Idempotency-Key"])

    def test_plan_change_expires_then_uses_new_identifier_and_key(self):
        first = self.create_session()
        self.transport.responses = [
            listing("/v1/subscriptions"),
            self.session,
            {**self.session, "status": "expired"},
            listing("/v1/subscriptions"),
            {**self.session, "id": "cs_year"},
        ]
        response = self.checkout("yearly")
        self.assertEqual(response.status_code, 200, response.data)
        second = StripeBillingRequest.objects.get(subscription=self.record, operation="checkout")
        self.assertNotEqual(first.idempotency_key, second.idempotency_key)
        self.assertNotEqual(first.parameters["integration_identifier"], second.parameters["integration_identifier"])
        self.assertEqual(second.parameters["line_items"], [{"price": "price_year", "quantity": 1}])
        self.assertEqual(urlsplit(self.transport.calls[-3][1]).path, "/v1/checkout/sessions/cs_upgrade/expire")

    def test_legacy_uncertain_intent_is_not_rewritten_after_upgrade(self):
        attempt = self.create_session()
        parameters = {key: value for key, value in attempt.parameters.items() if key != "integration_identifier"}
        StripeBillingRequest.objects.filter(pk=attempt.pk).update(parameters=parameters, resource_id="")
        self.transport.responses = [listing("/v1/subscriptions"), self.session]
        response = self.checkout()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("integration_identifier", parse_qs(self.transport.calls[-1][3]))
        self.assertEqual(self.transport.calls[-1][2]["Idempotency-Key"], str(attempt.idempotency_key))
        attempt.refresh_from_db()
        self.assertEqual(attempt.parameters, parameters)
        self.assertEqual([method for method, _, _, _ in self.transport.calls].count("post"), 2)

    @override_settings(STRIPE_API_VERSION="2026-02-25.clover")
    def test_explicit_legacy_pin_does_not_send_unsupported_tracking_parameter(self):
        attempt = self.create_session()
        self.assertNotIn("integration_identifier", attempt.parameters)
        self.assertEqual(self.transport.calls[-1][2]["Stripe-Version"], "2026-02-25.clover")

    @override_settings(STRIPE_API_VERSION="2026-03-25.dahlia")
    def test_first_supported_api_version_includes_persisted_identifier(self):
        attempt = self.create_session()
        self.assertRegex(attempt.parameters["integration_identifier"], r"^tableno_checkout_[a-zA-Z]{8}$")
        self.assertEqual(self.transport.calls[-1][2]["Stripe-Version"], "2026-03-25.dahlia")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_api_upgrade_fixture",  # nosec B106
        ENVIRONMENT="development",
        PUBLIC_SITE_URL="https://example.test",
        STRIPE_PREMIUM_YEARLY_PRICE_ID="",
    )
    def test_real_sdk_remote_command_rejects_stale_webhook_pin_without_writing(self):
        self.transport.responses = [
            {
                "id": "price_month",
                "object": "price",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "month"},
            },
            listing(
                "/v1/webhook_endpoints",
                [
                    {
                        "id": "we_upgrade",
                        "object": "webhook_endpoint",
                        "url": "https://example.test/api/billing/webhook/",
                        "livemode": False,
                        "status": "enabled",
                        "enabled_events": ["*"],
                        "api_version": "2026-02-25.clover",
                    }
                ],
            ),
        ]
        with self.assertRaisesMessage(CommandError, "webhook endpoint API version mismatch"):
            call_command("billing_stripe_remote_check", skip_portal=True, stdout=StringIO())
        self.assertEqual([method for method, _, _, _ in self.transport.calls], ["get", "get"])
        self.assertTrue(all(headers["Stripe-Version"] == ENDIVE for _, _, headers, _ in self.transport.calls))

    def signed_event(self, event_type, snapshot, event_id="evt_upgrade"):
        payload = json.dumps(
            {
                "id": event_id,
                "object": "event",
                "api_version": ENDIVE,
                "type": event_type,
                "data": {"object": snapshot},
            }
        ).encode()
        timestamp = int(time.time())
        digest = hmac.new(
            settings.STRIPE_WEBHOOK_SECRET.encode(), str(timestamp).encode() + b"." + payload, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse("billing-webhook"),
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={digest}",
        )

    def subscription(self, status):
        return {
            "id": "sub_upgrade",
            "object": "subscription",
            "customer": "cus_upgrade",
            "status": status,
            "status_details": {"paused": {"reason": "manual"}} if status == "paused" else None,
            "items": {
                "object": "list",
                "data": [
                    {
                        "id": "si_upgrade",
                        "object": "subscription_item",
                        "current_period_end": 1800000000,
                        "price": {"id": "price_month", "object": "price", "recurring": {"interval": "month"}},
                    }
                ],
            },
        }

    def test_signed_pause_revokes_and_resume_restores_using_current_subscription(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        PremiumSubscription.objects.filter(pk=self.record.pk).update(
            access_source="stripe", stripe_subscription_id="sub_upgrade", subscription_status="active"
        )
        for event_type, current_status, expected in (
            ("customer.subscription.paused", "paused", False),
            ("customer.subscription.resumed", "active", True),
        ):
            self.transport.responses = [self.subscription(current_status)]
            response = self.signed_event(event_type, self.subscription(current_status), f"evt_{current_status}")
            self.assertEqual(response.status_code, 200, response.data)
            self.user.refresh_from_db()
            self.record.refresh_from_db()
            self.assertEqual(self.user.is_premium, expected)
            self.assertEqual(self.record.subscription_status, current_status)
            self.assertEqual(int(self.record.current_period_end.timestamp()), 1800000000)
        self.assertEqual(StripeWebhookEvent.objects.filter(processing_status="succeeded").count(), 2)

    def test_delayed_resume_does_not_grant_current_paused_contract(self):
        self.transport.responses = [self.subscription("paused")]
        response = self.signed_event("customer.subscription.resumed", self.subscription("active"))
        self.assertEqual(response.status_code, 200, response.data)
        self.record.refresh_from_db()
        self.assertEqual(self.record.subscription_status, "paused")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

    def test_signed_invoice_paid_clears_only_verified_current_invoice_failure(self):
        failed_at = timezone.now()
        PremiumSubscription.objects.filter(pk=self.record.pk).update(last_payment_failed_at=failed_at)
        invoice_state = StripeInvoiceState.objects.create(
            subscription=self.record, invoice_id="in_upgrade", status="open", payment_failed=True
        )
        invoice = {
            "id": "in_upgrade",
            "object": "invoice",
            "customer": "cus_upgrade",
            "status": "paid",
            "parent": {"type": "subscription_details", "subscription_details": {"subscription": "sub_upgrade"}},
        }
        self.transport.responses = [invoice]
        response = self.signed_event("invoice.paid", invoice)
        self.assertEqual(response.status_code, 200, response.data)
        self.record.refresh_from_db()
        invoice_state.refresh_from_db()
        self.assertIsNone(self.record.last_payment_failed_at)
        self.assertFalse(invoice_state.payment_failed)
        # A duplicate signed event does not fetch or mutate the current state again.
        duplicate = self.signed_event("invoice.paid", invoice)
        self.assertEqual(duplicate.status_code, 200, duplicate.data)
        self.assertTrue(duplicate.data["duplicate"])
        self.assertEqual(len(self.transport.calls), 1)
