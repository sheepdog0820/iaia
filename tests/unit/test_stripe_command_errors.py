"""Unusable credentials and in-memory responses only; no Stripe network requests."""

import json
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from io import StringIO
from threading import Barrier
from unittest.mock import patch

import stripe
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.billing_verification_record import Command as RecordCommand
from tests.unit.test_stripe_client_isolation import FixtureTransport, RealStripeClient

PRIVATE_MARKER = "synthetic-private-payload-person@example.test"


class ErrorTransport(FixtureTransport):
    def request(self, method, url, headers, post_data=None, *, _usage=None):
        self.calls.append((method, url, dict(headers), post_data))
        response, status = self.responses.pop(0)
        return json.dumps(response), status, {"request-id": PRIVATE_MARKER}


@override_settings(
    STRIPE_SECRET_KEY="rk_test_unusable-command-fixture",  # nosec B106
    STRIPE_API_VERSION="2026-09-30.endive",
    STRIPE_PREMIUM_PRICE_ID="price_fixture",
    STRIPE_PREMIUM_YEARLY_PRICE_ID="",
    ENVIRONMENT="development",
)
class StripeCommandErrorTests(SimpleTestCase):
    def setUp(self):
        self.transport = ErrorTransport()
        self.logs = StringIO()
        self.logger = logging.getLogger("stripe")
        self.old_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(self.logs)
        self.logger.addHandler(handler)
        self.addCleanup(self.logger.removeHandler, handler)
        self.addCleanup(self.logger.setLevel, self.old_level)
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

    def error_response(self, status):
        return {"error": {"type": "invalid_request_error", "message": PRIVATE_MARKER}}, status

    def run_failed(self, command, *args):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stderr(stderr), self.assertRaises(CommandError) as caught:
            call_command(command, *args, stdout=stdout, stderr=stderr)
        rendered = "".join(traceback.format_exception(caught.exception))
        combined = stdout.getvalue() + stderr.getvalue() + rendered + self.logs.getvalue()
        self.assertNotIn(PRIVATE_MARKER, combined)
        self.assertNotIn("rk_test_unusable-command-fixture", combined)
        self.assertNotIn("=ok", stdout.getvalue())
        return str(caught.exception)

    def test_remote_authentication_and_permission_errors_do_not_disclose_payload(self):
        for status, label in ((401, "認証"), (403, "権限")):
            with self.subTest(status=status):
                self.logs.truncate(0)
                self.logs.seek(0)
                self.transport.responses = [self.error_response(status)]
                message = self.run_failed("billing_stripe_remote_check", "--skip-portal", "--skip-webhook")
                self.assertIn(label, message)
                self.assertIn(f"HTTP {status}", message)
        self.assertEqual(len(self.transport.calls), 2)

    def test_price_creation_failure_does_not_disclose_payload_or_report_success(self):
        successes = [
            ({"id": "prod_fixture", "object": "product", "livemode": False}, 200),
            ({"id": "price_month", "object": "price", "livemode": False}, 200),
        ]
        for completed in range(3):
            with self.subTest(completed=completed):
                self.transport.calls.clear()
                self.transport.responses = successes[:completed] + [self.error_response(403)]
                message = self.run_failed("create_stripe_development_prices")
                self.assertIn("権限", message)
                self.assertIn("確認", message)
                self.assertEqual(len(self.transport.calls), completed + 1)

    def test_live_product_cleanup_failure_is_not_reported_as_disabled(self):
        self.transport.responses = [
            ({"id": "prod_unexpected_live", "object": "product", "livemode": True}, 200),
            self.error_response(403),
        ]
        message = self.run_failed("create_stripe_development_prices")
        self.assertNotIn("disabled Product", message)
        self.assertIn("確認", message)
        self.assertEqual(len(self.transport.calls), 2)
        self.assertTrue(all("/prices" not in call[1] for call in self.transport.calls))

    def test_verification_record_does_not_store_raw_sdk_exception(self):
        self.transport.responses = [self.error_response(401)]
        result = RecordCommand()._run_command("billing_stripe_remote_check", "--skip-portal", "--skip-webhook")
        self.assertEqual(result["status"], "NG")
        self.assertIn("認証", result["summary"])
        self.assertNotIn(PRIVATE_MARKER, json.dumps(result))
        self.assertNotIn(PRIVATE_MARKER, self.logs.getvalue())

    def test_unexpected_record_exception_is_not_persisted(self):
        with patch(
            "accounts.management.commands.billing_verification_record.call_command",
            side_effect=RuntimeError(PRIVATE_MARKER),
        ):
            result = RecordCommand()._run_command("billing_webhook_smoke")
        self.assertEqual(result["status"], "NG")
        self.assertNotIn(PRIVATE_MARKER, json.dumps(result))
        self.assertIn("予期しない", result["summary"])

    def test_sdk_console_logging_is_rejected_before_client_creation(self):
        for source in ("module", "cached_environment", "environment"):
            for level in ("debug", "info"):
                for command in ("billing_stripe_remote_check", "create_stripe_development_prices"):
                    with self.subTest(source=source, level=level, command=command):
                        module_level = level if source == "module" else None
                        cached_level = level if source == "cached_environment" else None
                        env_level = level if source == "environment" else ""
                        with (
                            patch.object(stripe, "log", module_level),
                            patch.object(stripe._util, "STRIPE_LOG", cached_level),
                            patch.dict(os.environ, {"STRIPE_LOG": env_level}),
                            patch("stripe.StripeClient") as factory,
                        ):
                            message = self.run_failed(command)
                            factory.assert_not_called()
                            self.assertIn("詳細ログ", message)
                            self.assertEqual(stripe.log, module_level)
                            self.assertEqual(stripe._util.STRIPE_LOG, cached_level)
        self.assertEqual(self.transport.calls, [])

    def test_original_stripe_error_keeps_its_private_details_in_memory(self):
        original = stripe.AuthenticationError(PRIVATE_MARKER, http_status=401)
        with patch("accounts.management.commands.billing_stripe_remote_check.get_stripe", side_effect=original):
            message = self.run_failed("billing_stripe_remote_check")
        self.assertIn("認証", message)
        self.assertEqual(str(original), PRIVATE_MARKER)

    def test_unexpected_command_failure_is_safe_including_traceback(self):
        with patch(
            "accounts.management.commands.billing_stripe_remote_check.get_stripe",
            side_effect=RuntimeError(PRIVATE_MARKER),
        ):
            message = self.run_failed("billing_stripe_remote_check")
        self.assertIn("予期しない", message)

    def test_chained_validation_exception_does_not_render_raw_cause(self):
        def failure():
            try:
                raise stripe.APIError(PRIVATE_MARKER)
            except stripe.StripeError as cause:
                raise CommandError("合成された設定エラー") from cause

        with patch("accounts.management.commands.billing_stripe_remote_check.get_stripe", side_effect=failure):
            message = self.run_failed("billing_stripe_remote_check")
        self.assertEqual(message, "合成された設定エラー")


class StripeCommandSafetyScopeTests(SimpleTestCase):
    def test_filter_is_context_local_and_restored_after_exception(self):
        from accounts.management.stripe_safety import safe_stripe_command

        barrier = Barrier(2)

        @safe_stripe_command
        def protected():
            barrier.wait(timeout=10)
            logging.getLogger("stripe").info(PRIVATE_MARKER)
            raise CommandError("合成された設定エラー")

        def unprotected():
            barrier.wait(timeout=10)
            logging.getLogger("stripe").info("unchanged unprotected thread")

        with self.assertLogs("stripe", level="INFO") as logs, ThreadPoolExecutor(max_workers=2) as executor:
            protected_future = executor.submit(protected)
            unprotected_future = executor.submit(unprotected)
            with self.assertRaisesMessage(CommandError, "合成された設定エラー"):
                protected_future.result(timeout=15)
            unprotected_future.result(timeout=15)
        self.assertNotIn(PRIVATE_MARKER, str(logs.output))
        self.assertIn("省略", str(logs.output))
        self.assertIn("unchanged unprotected thread", str(logs.output))
        with self.assertLogs("stripe", level="INFO") as logs:
            logging.getLogger("stripe").info("unchanged outside protected command")
        self.assertIn("unchanged outside protected command", str(logs.output))

    def test_nested_context_restores_outer_protection_and_scrubs_traceback_fields(self):
        from accounts.management.stripe_safety import safe_stripe_command

        @safe_stripe_command
        def inner():
            return "nested fixture"

        @safe_stripe_command
        def outer():
            self.assertEqual(inner(), "nested fixture")
            with self.assertLogs("stripe", level="ERROR") as logs:
                try:
                    raise RuntimeError(PRIVATE_MARKER)
                except RuntimeError:
                    logging.getLogger("stripe").exception("%s", PRIVATE_MARKER, stack_info=True)
            self.assertNotIn(PRIVATE_MARKER, str(logs.output))
            self.assertEqual(logs.records[0].args, ())
            self.assertIsNone(logs.records[0].exc_info)
            self.assertIsNone(logs.records[0].exc_text)
            self.assertIsNone(logs.records[0].stack_info)

        outer()

    def test_error_summary_uses_only_fixed_category_and_valid_numeric_http_status(self):
        from accounts.management.stripe_safety import stripe_error_summary

        for error_type, label in (
            (stripe.AuthenticationError, "認証"),
            (stripe.PermissionError, "権限"),
            (stripe.APIConnectionError, "通信"),
            (stripe.RateLimitError, "制限"),
            (stripe.APIError, "API"),
            (stripe.IdempotencyError, "API"),
        ):
            for status in (None, True, PRIVATE_MARKER, 99, 600, 100, 400, 599):
                with self.subTest(error_type=error_type, status=status):
                    error = error_type(PRIVATE_MARKER)
                    error.http_status = status
                    error.code = PRIVATE_MARKER
                    error.request_id = PRIVATE_MARKER
                    summary = stripe_error_summary(error)
                    self.assertIn(label, summary)
                    self.assertNotIn(PRIVATE_MARKER, summary)
                    if type(status) is int and 100 <= status <= 599:
                        self.assertIn(f"HTTP {status}", summary)
                    else:
                        self.assertNotIn("HTTP", summary)
