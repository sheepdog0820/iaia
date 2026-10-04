"""Application flows through real StripeClient serialization; no external I/O."""

from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.billing_deletion import delete_account_after_billing_check
from accounts.models import PremiumSubscription, StripeBillingRequest
from tests.unit.test_stripe_client_isolation import FixtureTransport, RealStripeClient


def listing(path, data=()):
    return {"object": "list", "url": path, "has_more": False, "data": list(data)}


@override_settings(
    # Mocked credential confined to FixtureTransport, not a real Stripe key.
    STRIPE_SECRET_KEY="sk_test_client_transport_fixture",  # nosec B106
    STRIPE_API_VERSION="2026-02-25.clover",
    STRIPE_CHECKOUT_ENABLED=True,
    STRIPE_PREMIUM_PRICE_ID="price_fixture_month",
    STRIPE_PREMIUM_YEARLY_PRICE_ID="price_fixture_year",
    STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_fixture",
    ENVIRONMENT="development",
)
class StripeClientTransportTests(TestCase):
    def setUp(self):
        self.transport = FixtureTransport()
        patcher = patch(
            "stripe.StripeClient",
            side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=self.transport),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user(username="client-transport", email="fixture@example.test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_checkout_customer_and_retry_intents_reach_real_sdk_with_same_headers(self):
        self.transport.responses = [
            {"id": "cus_fixture", "object": "customer"},
            listing("/v1/subscriptions"),
            listing("/v1/checkout/sessions"),
            listing("/v1/subscriptions"),
            {
                "id": "cs_fixture",
                "object": "checkout.session",
                "status": "open",
                "url": "https://example.test/checkout",
            },
        ]
        response = self.client.post(reverse("billing-checkout-session"), {"plan": "yearly"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["url"], "https://example.test/checkout")
        record = PremiumSubscription.objects.get(user=self.user)
        customer_intent = StripeBillingRequest.objects.get(subscription=record, operation="customer")
        checkout_intent = StripeBillingRequest.objects.get(subscription=record, operation="checkout")
        self.assertEqual(record.stripe_customer_id, "cus_fixture")
        self.assertEqual(customer_intent.resource_id, "cus_fixture")
        self.assertEqual(checkout_intent.resource_id, "cs_fixture")
        self.assertEqual(self.transport.calls[0][2]["Idempotency-Key"], str(customer_intent.idempotency_key))
        _, _, headers, body = self.transport.calls[-1]
        self.assertEqual(headers["Idempotency-Key"], str(checkout_intent.idempotency_key))
        self.assertEqual(parse_qs(body)["line_items[0][price]"], ["price_fixture_year"])
        self.assertEqual(parse_qs(body)["subscription_data[metadata][user_id]"], [str(self.user.pk)])
        for _, _, headers, _ in self.transport.calls:
            self.assertEqual(headers["Authorization"], "Bearer sk_test_client_transport_fixture")
            self.assertEqual(headers["Stripe-Version"], "2026-02-25.clover")
        self.transport.responses = [
            listing("/v1/subscriptions"),
            {
                "id": "cs_fixture",
                "object": "checkout.session",
                "status": "open",
                "url": "https://example.test/checkout",
            },
        ]
        repeated = self.client.post(reverse("billing-checkout-session"), {"plan": "yearly"}, format="json")
        self.assertEqual(repeated.status_code, 200, repeated.data)
        post_paths = [urlsplit(url).path for method, url, _, _ in self.transport.calls if method == "post"]
        self.assertEqual(post_paths, ["/v1/customers", "/v1/checkout/sessions"])
        self.assertEqual(
            StripeBillingRequest.objects.get(pk=checkout_intent.pk).idempotency_key, checkout_intent.idempotency_key
        )

    def test_sdk_authentication_failure_keeps_customer_retry_intent_and_returns_503(self):
        self.transport.status = 401
        self.transport.responses = [{"error": {"type": "authentication_error", "message": "isolated failure"}}]
        response = self.client.post(reverse("billing-checkout-session"), {}, format="json")
        self.assertEqual(response.status_code, 503)
        attempt = StripeBillingRequest.objects.get(subscription__user=self.user, operation="customer")
        self.assertEqual(attempt.resource_id, "")
        self.assertEqual(self.transport.calls[0][2]["Idempotency-Key"], str(attempt.idempotency_key))
        self.assertNotIn("sk_test_client_transport_fixture", str(response.data))
        self.transport.status = 200
        self.user.email = "changed@example.test"
        self.user.save(update_fields=["email"])
        self.transport.responses = [
            {"id": "cus_recovered", "object": "customer"},
            listing("/v1/subscriptions"),
            listing("/v1/checkout/sessions"),
            listing("/v1/subscriptions"),
            {
                "id": "cs_recovered",
                "object": "checkout.session",
                "status": "open",
                "url": "https://example.test/recovered",
            },
        ]
        response = self.client.post(reverse("billing-checkout-session"), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.transport.calls[1][2]["Idempotency-Key"], str(attempt.idempotency_key))
        self.assertEqual(parse_qs(self.transport.calls[1][3])["email"], ["fixture@example.test"])
        self.assertEqual(self.transport.calls[0][3], self.transport.calls[1][3])

    def test_portal_parameters_are_serialized_by_real_sdk(self):
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_fixture")
        self.transport.responses = [
            {"id": "bps_fixture", "object": "billing_portal.session", "url": "https://example.test/portal"}
        ]
        response = self.client.post(reverse("billing-portal-session"), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["url"], "https://example.test/portal")
        method, url, _, body = self.transport.calls[0]
        self.assertEqual((method, urlsplit(url).path), ("post", "/v1/billing_portal/sessions"))
        self.assertEqual(parse_qs(body)["configuration"], ["bpc_fixture"])
        self.assertEqual(parse_qs(body)["customer"], ["cus_fixture"])

    def test_deletion_expires_open_session_and_checks_remote_contracts(self):
        user_id = self.user.pk
        PremiumSubscription.objects.create(
            user=self.user, stripe_customer_id="cus_fixture", subscription_status="canceled"
        )
        session = {"id": "cs_fixture", "object": "checkout.session", "customer": "cus_fixture", "status": "open"}
        self.transport.responses = [
            listing("/v1/checkout/sessions", [session]),
            {**session, "status": "expired"},
            listing(
                "/v1/subscriptions",
                [{"id": "sub_fixture", "object": "subscription", "customer": "cus_fixture", "status": "canceled"}],
            ),
        ]
        delete_account_after_billing_check(self.user)
        self.assertFalse(get_user_model().objects.filter(pk=user_id).exists())
        self.assertEqual(
            [urlsplit(url).path for _, url, _, _ in self.transport.calls],
            [
                "/v1/checkout/sessions",
                "/v1/checkout/sessions/cs_fixture/expire",
                "/v1/subscriptions",
            ],
        )
        self.assertEqual(parse_qs(urlsplit(self.transport.calls[-1][1]).query)["status"], ["all"])

    @override_settings(PUBLIC_SITE_URL="https://example.test", STRIPE_PREMIUM_YEARLY_PRICE_ID="")
    def test_read_only_remote_check_uses_real_sdk_services(self):
        self.transport.responses = [
            {
                "id": "price_fixture_month",
                "object": "price",
                "active": True,
                "type": "recurring",
                "livemode": False,
                "recurring": {"interval": "month"},
            },
            listing(
                "/v1/billing_portal/configurations",
                [
                    {
                        "id": "bpc_fixture",
                        "object": "billing_portal.configuration",
                        "active": True,
                        "livemode": False,
                        "features": {
                            name: {"enabled": True}
                            for name in ("payment_method_update", "subscription_cancel", "invoice_history")
                        },
                    }
                ],
            ),
            listing(
                "/v1/webhook_endpoints",
                [
                    {
                        "id": "we_fixture",
                        "object": "webhook_endpoint",
                        "url": "https://example.test/api/billing/webhook/",
                        "livemode": False,
                        "status": "enabled",
                        "enabled_events": ["*"],
                    }
                ],
            ),
        ]
        output = StringIO()
        call_command("billing_stripe_remote_check", stdout=output)
        self.assertIn("billing_stripe_remote_check=ok", output.getvalue())
        self.assertEqual([method for method, _, _, _ in self.transport.calls], ["get", "get", "get"])

    def test_development_price_command_uses_real_sdk_parameter_dictionaries(self):
        self.transport.responses = [
            {"id": "prod_fixture", "object": "product", "livemode": False},
            {"id": "price_month", "object": "price", "livemode": False},
            {"id": "price_year", "object": "price", "livemode": False},
        ]
        output = StringIO()
        call_command("create_stripe_development_prices", stdout=output)
        self.assertIn("stripe_development_prices=ok", output.getvalue())
        bodies = [parse_qs(body) for _, _, _, body in self.transport.calls]
        self.assertEqual(bodies[1]["recurring[interval]"], ["month"])
        self.assertEqual(bodies[1]["unit_amount"], ["480"])
        self.assertEqual(bodies[2]["recurring[interval]"], ["year"])
        self.assertEqual(bodies[2]["unit_amount"], ["4800"])
