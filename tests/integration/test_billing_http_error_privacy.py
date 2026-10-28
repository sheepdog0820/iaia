"""Billing HTTP failures use a real SDK and the production log formatter offline."""

import hashlib
import hmac
import json
import logging
import os
import time
from io import StringIO
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PremiumSubscription, StripeWebhookEvent
from tableno.error_reporting import SafeRequestFormatter
from tests.unit.test_stripe_client_isolation import FixtureTransport, RealStripeClient

PRIVATE_MARKER = "synthetic-billing-response-person@example.test"


@override_settings(
    STRIPE_SECRET_KEY="rk_test_unusable-http-log-fixture",  # nosec B106
    STRIPE_API_VERSION="2026-09-30.endive",
    STRIPE_CHECKOUT_ENABLED=True,
    STRIPE_PREMIUM_PRICE_ID="price_http_fixture",
    STRIPE_WEBHOOK_SECRET="synthetic-http-webhook-fixture",  # nosec B106
)
class BillingHttpErrorPrivacyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="http-log-fixture")
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_http_fixture")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.transport = FixtureTransport()
        self.logs = StringIO()
        logger = logging.getLogger("tableno.billing")
        level = logger.level
        logger.setLevel(logging.ERROR)
        handler = logging.StreamHandler(self.logs)
        handler.setFormatter(SafeRequestFormatter("%(message)s"))
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        self.addCleanup(logger.setLevel, level)
        for patcher in (
            patch.object(stripe, "log", None),
            patch.object(stripe._util, "STRIPE_LOG", None),
            patch.dict(os.environ, {"STRIPE_LOG": ""}),
            patch(
                "stripe.StripeClient",
                side_effect=lambda *args, **kwargs: RealStripeClient(
                    *args, **kwargs, http_client=self.transport, max_network_retries=0
                ),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def fail_with_sdk_response(self, route):
        self.transport.status = 500
        self.transport.responses = [{"error": {"type": "api_error", "message": PRIVATE_MARKER}}]
        response = self.client.post(reverse(route), {}, format="json")
        self.assertEqual(response.status_code, 503, response.data)
        self.assertNotIn(PRIVATE_MARKER, str(response.data))
        self.assertTrue(self.transport.calls)
        self.assertNotIn(PRIVATE_MARKER, self.logs.getvalue())
        self.assertNotIn("Traceback", self.logs.getvalue())
        self.assertIn("failed", self.logs.getvalue())

    def test_checkout_sdk_failure_omits_payload_from_console_and_response(self):
        self.fail_with_sdk_response("billing-checkout-session")

    def test_portal_sdk_failure_omits_payload_from_console_and_response(self):
        self.fail_with_sdk_response("billing-portal-session")

    def test_unexpected_failures_do_not_log_exception_values(self):
        for route, function in (
            ("billing-checkout-session", "create_checkout_session"),
            ("billing-portal-session", "create_portal_session"),
        ):
            with (
                self.subTest(route=route),
                patch("accounts.views.billing_views." + function, side_effect=RuntimeError(PRIVATE_MARKER)),
            ):
                response = self.client.post(reverse(route), {}, format="json")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(PRIVATE_MARKER, str(response.data))
                self.assertNotIn(PRIVATE_MARKER, self.logs.getvalue())

    def test_verbose_sdk_flags_fail_before_factory_without_changing_global_settings(self):
        for source in ("module", "cached_environment", "environment"):
            for level in ("debug", "info"):
                for route in ("billing-checkout-session", "billing-portal-session", "billing-webhook"):
                    with self.subTest(source=source, level=level, route=route):
                        module_level = level if source == "module" else None
                        cached_level = level if source == "cached_environment" else None
                        env_level = level if source == "environment" else ""
                        with (
                            patch.object(stripe, "log", module_level),
                            patch.object(stripe._util, "STRIPE_LOG", cached_level),
                            patch.dict(os.environ, {"STRIPE_LOG": env_level}),
                            patch("stripe.StripeClient", side_effect=RuntimeError(PRIVATE_MARKER)) as factory,
                        ):
                            headers = (
                                {"HTTP_STRIPE_SIGNATURE": "synthetic-signature"} if route == "billing-webhook" else {}
                            )
                            response = self.client.post(reverse(route), {}, format="json", **headers)
                            self.assertEqual(response.status_code, 503)
                            factory.assert_not_called()
                            self.assertIn("詳細ログ", response.data["error"])
                            self.assertEqual(stripe.log, module_level)
                            self.assertEqual(stripe._util.STRIPE_LOG, cached_level)
                            self.assertEqual(os.environ["STRIPE_LOG"], env_level)
        self.assertEqual(self.transport.calls, [])

    def test_signed_webhook_does_not_store_raw_error_and_remains_retryable(self):
        payload = json.dumps(
            {
                "id": "evt_http_privacy_fixture",
                "object": "event",
                "api_version": "2026-09-30.endive",
                "type": "customer.subscription.updated",
                "data": {"object": {"id": "sub_http_fixture", "customer": "cus_http_fixture"}},
            }
        ).encode()
        timestamp = int(time.time())
        digest = hmac.new(
            b"synthetic-http-webhook-fixture", str(timestamp).encode() + b"." + payload, hashlib.sha256
        ).hexdigest()
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                self.transport.status = 500
                self.transport.responses = [{"error": {"type": "api_error", "message": PRIVATE_MARKER}}]
                response = self.client.post(
                    reverse("billing-webhook"),
                    payload,
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={digest}",
                )
                self.assertEqual(response.status_code, 500, response.data)
                self.assertNotIn(PRIVATE_MARKER, str(response.data))
                event = StripeWebhookEvent.objects.get(event_id="evt_http_privacy_fixture")
                self.assertEqual(event.processing_status, StripeWebhookEvent.STATUS_FAILED)
                self.assertNotIn(PRIVATE_MARKER, event.error_message)
                self.assertIn("確認", event.error_message)
        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(StripeWebhookEvent.objects.filter(event_id="evt_http_privacy_fixture").count(), 1)
