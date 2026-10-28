"""Real SDK requests against an in-memory transport, never the Stripe service."""

import hashlib
import hmac
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import stripe
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from accounts.billing import execute_stripe_creation, get_stripe

RealStripeClient = stripe.StripeClient


class FixtureTransport(stripe.HTTPClient):
    name = "isolated-fixture"

    def __init__(self):
        super().__init__()
        self.calls = []
        self.responses = []
        self.status = 200

    def request(self, method, url, headers, post_data=None, *, _usage=None):
        self.calls.append((method, url, dict(headers), post_data))
        response = self.responses.pop(0)
        return json.dumps(response), self.status, {}


# Unusable credentials only reach FixtureTransport, never a remote API.
@override_settings(STRIPE_SECRET_KEY="synthetic-client-one", STRIPE_API_VERSION="2026-02-25.clover")  # nosec B106
class StripeClientIsolationTests(SimpleTestCase):
    def setUp(self):
        self.transport = FixtureTransport()
        patcher = patch(
            "stripe.StripeClient",
            side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=self.transport),
        )
        self.factory = patcher.start()
        self.addCleanup(patcher.stop)

    def test_factory_does_not_change_module_configuration(self):
        with patch.object(stripe, "api_key", "synthetic-global"), patch.object(stripe, "api_version", "global-version"):
            client = get_stripe()
            self.assertIsInstance(client, RealStripeClient)
            self.assertEqual(stripe.api_key, "synthetic-global")
            self.assertEqual(stripe.api_version, "global-version")
        self.factory.assert_called_once_with("synthetic-client-one", stripe_version="2026-02-25.clover")

    def test_missing_key_fails_before_client_construction(self):
        # Empty credential is intentional for the configuration-error test.
        with override_settings(STRIPE_SECRET_KEY=""):  # nosec B106
            with self.assertRaisesMessage(ImproperlyConfigured, "STRIPE_SECRET_KEY is required"):
                get_stripe()
        self.factory.assert_not_called()
        self.assertEqual(self.transport.calls, [])

    def test_two_clients_keep_their_own_key_and_version_after_other_factory_calls(self):
        first = get_stripe()
        with override_settings(
            STRIPE_SECRET_KEY="synthetic-client-two", STRIPE_API_VERSION="fixture-version-two"
        ):  # nosec B106
            second = get_stripe()
        self.transport.responses = [{"id": "cus_one", "object": "customer"}, {"id": "cus_two", "object": "customer"}]
        self.assertEqual(first.v1.customers.retrieve("cus_one").id, "cus_one")
        self.assertEqual(second.v1.customers.retrieve("cus_two").id, "cus_two")
        self.assertEqual(self.transport.calls[0][2]["Authorization"], "Bearer synthetic-client-one")
        self.assertEqual(self.transport.calls[0][2]["Stripe-Version"], "2026-02-25.clover")
        self.assertEqual(self.transport.calls[1][2]["Authorization"], "Bearer synthetic-client-two")
        self.assertEqual(self.transport.calls[1][2]["Stripe-Version"], "fixture-version-two")

    def test_creation_keeps_idempotency_in_options_not_business_parameters(self):
        client = get_stripe()
        attempt = SimpleNamespace(
            created_at=timezone.now(),
            idempotency_key=uuid.uuid4(),
            parameters={"customer": "cus_intent", "metadata": {"user_id": "12"}},
        )
        before = json.dumps(attempt.parameters, sort_keys=True)
        self.transport.responses = [{"id": "cs_created", "object": "checkout.session"}]
        result = execute_stripe_creation(attempt, client.v1.checkout.sessions.create)
        self.assertEqual(result.id, "cs_created")
        method, url, headers, body = self.transport.calls[0]
        self.assertEqual((method, urlsplit(url).path), ("post", "/v1/checkout/sessions"))
        self.assertEqual(headers["Idempotency-Key"], str(attempt.idempotency_key))
        self.assertEqual(parse_qs(body)["metadata[user_id]"], ["12"])
        self.assertNotIn("idempotency_key", parse_qs(body))
        self.assertEqual(json.dumps(attempt.parameters, sort_keys=True), before)

    def test_concurrent_requests_keep_separate_client_credentials(self):
        first = get_stripe()
        with override_settings(
            STRIPE_SECRET_KEY="synthetic-client-two", STRIPE_API_VERSION="fixture-version-two"
        ):  # nosec B106
            second = get_stripe()
        self.transport.responses = [{"id": "fixture", "object": "customer"}] * 2
        barrier = Barrier(2)

        def retrieve(client, customer_id):
            barrier.wait(timeout=5)
            return client.v1.customers.retrieve(customer_id).id

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(retrieve, first, "cus_one"), pool.submit(retrieve, second, "cus_two")]
            self.assertEqual([future.result(timeout=5) for future in futures], ["fixture", "fixture"])
        observed = {urlsplit(url).path: headers for _, url, headers, _ in self.transport.calls}
        self.assertEqual(observed["/v1/customers/cus_one"]["Authorization"], "Bearer synthetic-client-one")
        self.assertEqual(observed["/v1/customers/cus_two"]["Authorization"], "Bearer synthetic-client-two")
        self.assertEqual(observed["/v1/customers/cus_one"]["Stripe-Version"], "2026-02-25.clover")
        self.assertEqual(observed["/v1/customers/cus_two"]["Stripe-Version"], "fixture-version-two")

    def test_all_application_resource_services_use_client_headers(self):
        client = get_stripe()
        cases = [
            (client.v1.customers.create, (), {"params": {"email": "fixture@example.test"}}, "post", "/v1/customers"),
            (client.v1.subscriptions.retrieve, ("sub_fixture",), {}, "get", "/v1/subscriptions/sub_fixture"),
            (client.v1.invoices.retrieve, ("in_fixture",), {}, "get", "/v1/invoices/in_fixture"),
            (client.v1.charges.retrieve, ("ch_fixture",), {}, "get", "/v1/charges/ch_fixture"),
            (client.v1.disputes.retrieve, ("dp_fixture",), {}, "get", "/v1/disputes/dp_fixture"),
            (client.v1.prices.retrieve, ("price_fixture",), {}, "get", "/v1/prices/price_fixture"),
            (client.v1.prices.create, (), {"params": {"product": "prod_fixture"}}, "post", "/v1/prices"),
            (client.v1.products.create, (), {"params": {"name": "fixture"}}, "post", "/v1/products"),
            (
                client.v1.products.update,
                ("prod_fixture",),
                {"params": {"active": False}},
                "post",
                "/v1/products/prod_fixture",
            ),
            (client.v1.checkout.sessions.retrieve, ("cs_fixture",), {}, "get", "/v1/checkout/sessions/cs_fixture"),
            (
                client.v1.checkout.sessions.expire,
                ("cs_fixture",),
                {},
                "post",
                "/v1/checkout/sessions/cs_fixture/expire",
            ),
            (
                client.v1.billing_portal.sessions.create,
                (),
                {"params": {"customer": "cus_fixture"}},
                "post",
                "/v1/billing_portal/sessions",
            ),
        ]
        for operation, args, kwargs, method, path in cases:
            with self.subTest(path=path, method=method):
                self.transport.responses.append({"id": "fixture", "object": "customer"})
                operation(*args, **kwargs)
                observed_method, url, headers, _ = self.transport.calls[-1]
                self.assertEqual((observed_method, urlsplit(url).path), (method, path))
                self.assertEqual(headers["Authorization"], "Bearer synthetic-client-one")
                self.assertEqual(headers["Stripe-Version"], "2026-02-25.clover")

    def test_list_filters_and_pagination_remain_bound_to_original_client(self):
        client = get_stripe()
        # Unusable fixture credential only reaches the memory transport.
        with override_settings(STRIPE_SECRET_KEY="synthetic-other"):  # nosec B106
            get_stripe()
        operations = [
            (
                client.v1.subscriptions.list,
                {"customer": "cus_fixture", "status": "all", "limit": 100},
                "/v1/subscriptions",
            ),
            (
                client.v1.checkout.sessions.list,
                {"customer": "cus_fixture", "status": "open", "limit": 100},
                "/v1/checkout/sessions",
            ),
            (client.v1.billing_portal.configurations.list, {"limit": 100}, "/v1/billing_portal/configurations"),
            (client.v1.webhook_endpoints.list, {"limit": 100}, "/v1/webhook_endpoints"),
            (
                client.v1.events.list,
                {"limit": 100, "created": {"gte": 123}, "types": ["invoice.payment_failed"]},
                "/v1/events",
            ),
        ]
        for operation, parameters, path in operations:
            with self.subTest(path=path):
                self.transport.responses += [
                    {"object": "list", "url": path, "has_more": True, "data": [{"id": "first", "object": "customer"}]},
                    {
                        "object": "list",
                        "url": path,
                        "has_more": False,
                        "data": [{"id": "second", "object": "customer"}],
                    },
                ]
                records = operation(params=parameters)
                self.assertEqual([record.id for record in records.auto_paging_iter()], ["first", "second"])
                for _, url, headers, _ in self.transport.calls[-2:]:
                    self.assertEqual(urlsplit(url).path, path)
                    self.assertEqual(headers["Authorization"], "Bearer synthetic-client-one")
                    query = parse_qs(urlsplit(url).query)
                    self.assertEqual(query["limit"], ["100"])
                self.assertEqual(query["starting_after"], ["first"])

    def test_client_webhook_verifies_signature_without_any_http_call(self):
        client = get_stripe()
        payload = json.dumps({"id": "evt_fixture", "object": "event", "type": "invoice.payment_failed"}).encode()
        timestamp = str(int(time.time()))
        # Local HMAC fixture, not a real endpoint signing secret.
        secret = "synthetic-webhook-secret"  # nosec B105
        digest = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
        event = client.construct_event(payload, f"t={timestamp},v1={digest}", secret)
        self.assertEqual(event.to_dict()["id"], "evt_fixture")
        with self.assertRaises(stripe.SignatureVerificationError):
            client.construct_event(payload, f"t={timestamp},v1={'0' * 64}", secret)
        self.assertEqual(self.transport.calls, [])
