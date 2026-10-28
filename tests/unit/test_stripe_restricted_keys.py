"""Unusable key fixtures; real SDK requests only use an in-memory transport."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.billing_preflight import Command as PreflightCommand
from accounts.management.commands.billing_stripe_remote_check import get_expected_livemode
from tests.integration.test_stripe_client_transport import listing
from tests.unit.test_stripe_client_isolation import FixtureTransport, RealStripeClient


def fixture_key(prefix):
    return prefix + "unusable_restricted_key_fixture"


class StripeRestrictedKeyTests(SimpleTestCase):
    def test_classifier_accepts_both_server_key_families(self):
        from tableno.stripe_keys import stripe_server_key_livemode

        for prefix, expected in (("sk_test_", False), ("rk_test_", False), ("sk_live_", True), ("rk_live_", True)):
            with self.subTest(prefix=prefix):
                self.assertIs(stripe_server_key_livemode(fixture_key(prefix)), expected)

    def test_classifier_rejects_non_server_bare_and_whitespace_values(self):
        from tableno.stripe_keys import stripe_server_key_livemode

        for value in (
            None,
            123,
            "",
            "sk_test_",
            "rk_test_",
            "rk_live_",
            "sk_live_",
            "pk_test_fixture",
            "sk_org_fixture",
            "unknown",
            " rk_test_fixture",
            "rk_test_fixture\n",
            "rk_test_two words",
        ):
            with self.subTest(value=value):
                self.assertIsNone(stripe_server_key_livemode(value))

    def test_preflight_accepts_correct_mode_for_both_server_key_families(self):
        for prefix, environment in (
            ("rk_test_", "staging"),
            ("sk_test_", "development"),
            ("rk_live_", "production"),
            ("sk_live_", "production"),
        ):
            with (
                self.subTest(prefix=prefix),
                override_settings(STRIPE_SECRET_KEY=fixture_key(prefix), ENVIRONMENT=environment),
            ):
                self.assertEqual(PreflightCommand()._stripe_secret_key_check(), ("STRIPE_SECRET_KEY", True, ""))

    def test_preflight_rejects_mode_mismatch_and_unknown_values_without_disclosure(self):
        for prefix, environment in (
            ("rk_test_", "production"),
            ("sk_test_", "production"),
            ("rk_live_", "staging"),
            ("sk_live_", "development"),
            ("pk_test_", "development"),
            ("sk_org_", "production"),
        ):
            value = fixture_key(prefix)
            with self.subTest(prefix=prefix), override_settings(STRIPE_SECRET_KEY=value, ENVIRONMENT=environment):
                name, ok, message = PreflightCommand()._stripe_secret_key_check()
                self.assertEqual(name, "STRIPE_SECRET_KEY")
                self.assertFalse(ok)
                self.assertNotIn(value, message)

    def test_remote_check_mode_supports_restricted_keys(self):
        for prefix, environment, expected in (("rk_test_", "staging", False), ("rk_live_", "production", True)):
            with (
                self.subTest(prefix=prefix),
                override_settings(STRIPE_SECRET_KEY=fixture_key(prefix), ENVIRONMENT=environment),
            ):
                self.assertIs(get_expected_livemode(), expected)

    def test_remote_check_rejects_wrong_modes_before_instantiating_sdk(self):
        for prefix, environment in (
            ("rk_test_", "production"),
            ("rk_live_", "staging"),
            ("pk_test_", "staging"),
            ("sk_org_", "production"),
        ):
            value = fixture_key(prefix)
            output = StringIO()
            with (
                self.subTest(prefix=prefix),
                override_settings(
                    STRIPE_SECRET_KEY=value, ENVIRONMENT=environment, STRIPE_PREMIUM_PRICE_ID="price_fixture"
                ),
                patch("accounts.management.commands.billing_stripe_remote_check.get_stripe") as factory,
            ):
                with self.assertRaises(CommandError) as raised:
                    call_command("billing_stripe_remote_check", stdout=output)
                factory.assert_not_called()
                self.assertNotIn(value, output.getvalue() + str(raised.exception))

    def test_remote_check_real_sdk_uses_restricted_key_and_only_gets(self):
        for prefix, environment, mode in (("rk_test_", "staging", False), ("rk_live_", "production", True)):
            transport = FixtureTransport()
            transport.responses = [
                {
                    "id": "price_fixture",
                    "object": "price",
                    "active": True,
                    "type": "recurring",
                    "livemode": mode,
                    "recurring": {"interval": "month"},
                },
                listing(
                    "/v1/billing_portal/configurations",
                    [
                        {
                            "id": "bpc_fixture",
                            "object": "billing_portal.configuration",
                            "active": True,
                            "livemode": mode,
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
                            "livemode": mode,
                            "status": "enabled",
                            "api_version": settings.STRIPE_API_VERSION,
                            "enabled_events": ["*"],
                        }
                    ],
                ),
            ]
            value = fixture_key(prefix)
            output = StringIO()
            with (
                self.subTest(prefix=prefix),
                override_settings(
                    STRIPE_SECRET_KEY=value,
                    ENVIRONMENT=environment,
                    STRIPE_PREMIUM_PRICE_ID="price_fixture",
                    STRIPE_PREMIUM_YEARLY_PRICE_ID="",
                    STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_fixture",
                    PUBLIC_SITE_URL="https://example.test",
                    STRIPE_PREMIUM_EXPECTED_CURRENCY="",
                    STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="",
                ),
                patch(
                    "stripe.StripeClient",
                    side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=transport),
                ),
            ):
                call_command("billing_stripe_remote_check", stdout=output)
            self.assertIn("billing_stripe_remote_check=ok", output.getvalue())
            self.assertNotIn(value, output.getvalue())
            self.assertEqual(
                [urlsplit(url).path for _, url, _, _ in transport.calls],
                ["/v1/prices/price_fixture", "/v1/billing_portal/configurations", "/v1/webhook_endpoints"],
            )
            for method, _, headers, _ in transport.calls:
                self.assertEqual(method, "get")
                self.assertEqual(headers["Authorization"], "Bearer " + value)
                self.assertEqual(headers["Stripe-Version"], settings.STRIPE_API_VERSION)

    def write_development_env(self, directory, secret, extra=""):
        root = Path(directory)
        (root / ".gitignore").write_text(".env.development\n", encoding="utf-8")
        path = root / ".env.development"
        path.write_text(
            "\n".join(
                (
                    "APP_ENV=local",
                    "ENVIRONMENT=development",
                    "STRIPE_PREMIUM_EXPECTED_CURRENCY=jpy",
                    "STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT=480",
                    "STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT=4800",
                    "STRIPE_CHECKOUT_ENABLED=false",
                    "PUBLIC_SITE_URL=http://localhost:8000",
                    "STRIPE_SECRET_KEY=" + secret,
                    "STRIPE_PUBLISHABLE_KEY=pk_test_fixture",
                    "STRIPE_WEBHOOK_SECRET=whsec_fixture",
                    "STRIPE_PREMIUM_PRICE_ID=price_month_fixture",
                    "STRIPE_PREMIUM_YEARLY_PRICE_ID=price_year_fixture",
                    extra,
                    "",
                )
            ),
            encoding="utf-8",
        )
        return root, path

    def test_remote_check_permission_denial_never_reports_success(self):
        transport = FixtureTransport()
        transport.status = 403
        transport.responses = [{"error": {"type": "invalid_request_error", "message": "synthetic permission denied"}}]
        output = StringIO()
        value = fixture_key("rk_test_")
        with (
            override_settings(STRIPE_SECRET_KEY=value, ENVIRONMENT="staging", STRIPE_PREMIUM_PRICE_ID="price_fixture"),
            patch(
                "stripe.StripeClient",
                side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=transport),
            ),
        ):
            with self.assertRaises(stripe.PermissionError):
                call_command("billing_stripe_remote_check", stdout=output)
        self.assertNotIn("billing_stripe_remote_check=ok", output.getvalue())
        self.assertEqual(len(transport.calls), 1)

    def test_development_env_rejects_unknown_server_key_without_disclosure(self):
        value = fixture_key("pk_test_")
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, value)
            with override_settings(BASE_DIR=root), self.assertRaises(CommandError) as raised:
                call_command("billing_development_check", "--env-file", str(path), stdout=output)
        self.assertIn("サーバーキーを設定してください。", str(raised.exception))
        self.assertNotIn(value, output.getvalue() + str(raised.exception))

    def test_development_env_accepts_restricted_test_key(self):
        value = fixture_key("rk_test_")
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, value)
            with override_settings(BASE_DIR=root):
                call_command("billing_development_check", "--env-file", str(path), "--require-stripe", stdout=output)
        self.assertIn("billing_development_check=ok", output.getvalue())
        self.assertNotIn(value, output.getvalue())

    def test_development_env_rejects_live_publishable_key(self):
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, fixture_key("rk_test_"))
            path.write_text(
                path.read_text(encoding="utf-8").replace("pk_test_fixture", "pk_live_unusable_fixture"),
                encoding="utf-8",
            )
            with override_settings(BASE_DIR=root), self.assertRaises(CommandError):
                call_command("billing_development_check", "--env-file", str(path), stdout=output)
        self.assertIn("STRIPE_PUBLISHABLE_KEY must not use a live Stripe key", output.getvalue())

    def test_development_env_rejects_invalid_publishable_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, fixture_key("rk_test_"))
            path.write_text(
                path.read_text(encoding="utf-8").replace("pk_test_fixture", "invalid_public_fixture"), encoding="utf-8"
            )
            with (
                override_settings(BASE_DIR=root),
                self.assertRaisesMessage(CommandError, "STRIPE_PUBLISHABLE_KEY must start with pk_test_"),
            ):
                call_command("billing_development_check", "--env-file", str(path), stdout=StringIO())

    def test_development_env_rejects_restricted_live_key_without_disclosure(self):
        value = fixture_key("rk_live_")
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, value)
            with override_settings(BASE_DIR=root), self.assertRaises(CommandError) as raised:
                call_command("billing_development_check", "--env-file", str(path), stdout=output)
        self.assertNotIn(value, output.getvalue() + str(raised.exception))

    def test_development_env_rejects_live_restricted_prefix_in_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            root, path = self.write_development_env(directory, fixture_key("rk_test_"), "# " + fixture_key("rk_live_"))
            with override_settings(BASE_DIR=root), self.assertRaises(CommandError):
                call_command("billing_development_check", "--env-file", str(path), stdout=StringIO())

    def test_price_creation_accepts_restricted_test_key_via_real_sdk(self):
        transport = FixtureTransport()
        transport.responses = [
            {"id": "prod_fixture", "object": "product", "livemode": False},
            {"id": "price_month_fixture", "object": "price", "livemode": False},
            {"id": "price_year_fixture", "object": "price", "livemode": False},
        ]
        value = fixture_key("rk_test_")
        output = StringIO()
        with (
            override_settings(STRIPE_SECRET_KEY=value, ENVIRONMENT="development"),
            patch(
                "stripe.StripeClient",
                side_effect=lambda *args, **kwargs: RealStripeClient(*args, **kwargs, http_client=transport),
            ),
        ):
            call_command("create_stripe_development_prices", stdout=output)
        self.assertIn("stripe_development_prices=ok", output.getvalue())
        self.assertNotIn(value, output.getvalue())
        self.assertEqual([method for method, _, _, _ in transport.calls], ["post", "post", "post"])
        self.assertTrue(all(headers["Authorization"] == "Bearer " + value for _, _, headers, _ in transport.calls))

    def test_price_creation_rejects_restricted_live_and_production_before_sdk(self):
        for prefix, environment in (
            ("rk_live_", "development"),
            ("rk_test_", "production"),
            ("pk_test_", "development"),
        ):
            value = fixture_key(prefix)
            with (
                self.subTest(prefix=prefix),
                override_settings(STRIPE_SECRET_KEY=value, ENVIRONMENT=environment),
                patch("accounts.management.commands.create_stripe_development_prices.get_stripe") as factory,
            ):
                with self.assertRaises(CommandError) as raised:
                    call_command("create_stripe_development_prices", stdout=StringIO())
                factory.assert_not_called()
                self.assertNotIn(value, str(raised.exception))
