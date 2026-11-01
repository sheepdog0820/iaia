"""Effective Portal configuration regressions; Stripe responses are synthetic."""

import copy
import json
from io import StringIO
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import stripe
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.billing_stripe_remote_check import validate_portal_configurations


def configuration(identifier="bpc_default", *, default=True, active=True, live=False, **feature_flags):
    features = {key: {"enabled": True} for key in ("payment_method_update", "subscription_cancel", "invoice_history")}
    for key, enabled in feature_flags.items():
        features[key] = {"enabled": enabled}
    return {"id": identifier, "is_default": default, "active": active, "livemode": live, "features": features}


class PortalConfigurationSelectionTests(SimpleTestCase):
    def validate(self, *rows, mode=False, identifier="", has_more=False):
        return validate_portal_configurations(
            {"data": list(rows), "has_more": has_more}, expected_livemode=mode, expected_configuration_id=identifier
        )

    def test_default_configuration_with_all_features_passes(self):
        self.assertEqual(self.validate(configuration()), [])

    def test_nondefault_configuration_cannot_replace_missing_default(self):
        self.assertTrue(self.validate(configuration(default=False)))

    def test_nondefault_features_cannot_hide_a_broken_default(self):
        errors = self.validate(configuration(subscription_cancel=False), configuration("bpc_other", default=False))
        self.assertTrue(any("subscription cancellation" in message for message in errors))

    def test_features_split_across_configurations_do_not_add_up(self):
        errors = self.validate(
            configuration(payment_method_update=False),
            configuration("bpc_other", default=False, subscription_cancel=False, invoice_history=False),
        )
        self.assertTrue(any("payment method update" in message for message in errors))

    def test_nondefault_test_mode_cannot_hide_live_default(self):
        errors = self.validate(configuration(live=True), configuration("bpc_other", default=False, live=False))
        self.assertTrue(any("livemode mismatch" in message for message in errors))

    def test_default_must_be_unique(self):
        self.assertTrue(self.validate(configuration(), configuration("bpc_other")))

    def test_default_must_have_an_identifier(self):
        for identifier in (None, "", 1):
            with self.subTest(identifier=identifier):
                self.assertTrue(self.validate(configuration(identifier)))

    def test_explicit_id_can_select_a_nondefault_configuration(self):
        self.assertEqual(
            self.validate(
                configuration(active=False), configuration("bpc_selected", default=False), identifier="bpc_selected"
            ),
            [],
        )

    def test_explicit_id_must_exist_and_be_unique(self):
        self.assertTrue(self.validate(configuration(), identifier="bpc_missing"))
        self.assertTrue(
            self.validate(
                configuration("bpc_selected"), configuration("bpc_selected", default=False), identifier="bpc_selected"
            )
        )

    def test_selected_configuration_must_be_active_boolean_true(self):
        for active in (False, None, 1, "true"):
            for identifier in ("", "bpc_default"):
                with self.subTest(active=active, identifier=identifier):
                    self.assertTrue(self.validate(configuration(active=active), identifier=identifier))

    def test_selected_mode_must_be_known_boolean_and_match(self):
        for mode in (None, 0, 1, "false"):
            with self.subTest(mode=mode):
                self.assertTrue(self.validate(configuration(live=mode)))
        self.assertEqual(self.validate(configuration(live=True), mode=True), [])
        self.assertEqual(self.validate(configuration(live=None), mode=None), [])

    def test_default_flag_must_be_boolean_true(self):
        for flag in (None, False, 1, "true"):
            with self.subTest(flag=flag):
                self.assertTrue(self.validate(configuration(default=flag)))

    def test_features_require_boolean_true_and_missing_features_fail(self):
        for flag in (False, None, 1, "false"):
            with self.subTest(flag=flag):
                self.assertTrue(self.validate(configuration(subscription_cancel=flag)))
        for missing in (None, {}):
            selected = configuration()
            selected["features"] = missing
            self.assertEqual(len(self.validate(selected)), 3)

    def test_incomplete_list_cannot_prove_selection(self):
        for has_more in (True, None, "false"):
            with self.subTest(has_more=has_more):
                self.assertTrue(self.validate(configuration(), has_more=has_more))

    def test_sdk_objects_follow_the_same_selection_rules(self):
        payload = stripe.StripeObject.construct_from({"data": [configuration()], "has_more": False}, None)
        self.assertEqual(validate_portal_configurations(payload, expected_livemode=False), [])

    def test_validation_does_not_mutate_the_response(self):
        rows = [configuration(subscription_cancel=False), configuration("bpc_other", default=False)]
        original = copy.deepcopy(rows)
        self.validate(*rows)
        self.assertEqual(rows, original)


@override_settings(
    STRIPE_PREMIUM_PRICE_ID="price_fixture",
    STRIPE_PREMIUM_YEARLY_PRICE_ID="",
    STRIPE_PREMIUM_EXPECTED_CURRENCY="jpy",
    STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT="480",
    STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="",
)
class PortalConfigurationCommandTests(SimpleTestCase):
    def setUp(self):
        self.client = Mock()
        self.client.v1.prices.retrieve.return_value = {
            "id": "price_fixture",
            "active": True,
            "type": "recurring",
            "livemode": False,
            "currency": "jpy",
            "unit_amount": 480,
            "recurring": {"interval": "month"},
        }

    def run_command(self, *arguments):
        output = StringIO()
        with (
            patch("accounts.management.commands.billing_stripe_remote_check.get_stripe", return_value=self.client),
            patch("accounts.management.commands.billing_stripe_remote_check.get_expected_livemode", return_value=False),
        ):
            call_command("billing_stripe_remote_check", "--skip-webhook", *arguments, stdout=output)
        return output.getvalue()

    def test_command_requests_default_only(self):
        self.client.v1.billing_portal.configurations.list.return_value = {"data": [configuration()], "has_more": False}
        self.assertIn("billing_stripe_remote_check=ok", self.run_command())
        self.client.v1.billing_portal.configurations.list.assert_called_once_with(
            params={"limit": 100, "is_default": True}
        )
        self.client.v1.billing_portal.configurations.retrieve.assert_not_called()

    @override_settings(STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_selected")
    def test_command_retrieves_explicit_id_without_scanning_first_hundred(self):
        self.client.v1.billing_portal.configurations.retrieve.return_value = configuration(
            "bpc_selected", default=False
        )
        self.assertIn("billing_stripe_remote_check=ok", self.run_command())
        self.client.v1.billing_portal.configurations.retrieve.assert_called_once_with("bpc_selected")
        self.client.v1.billing_portal.configurations.list.assert_not_called()

    def test_broken_effective_default_stops_the_command(self):
        self.client.v1.billing_portal.configurations.list.return_value = {
            "data": [configuration(subscription_cancel=False), configuration("bpc_other", default=False)],
            "has_more": False,
        }
        with self.assertRaisesMessage(CommandError, "subscription cancellation"):
            self.run_command()
        self.client.v1.webhook_endpoints.list.assert_not_called()

    def test_skip_portal_does_not_read_portal_resources(self):
        self.assertIn("SKIP stripe customer portal", self.run_command("--skip-portal"))
        self.client.v1.billing_portal.configurations.list.assert_not_called()
        self.client.v1.billing_portal.configurations.retrieve.assert_not_called()

    @override_settings(STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_selected")
    def test_retrieve_failure_is_sanitized(self):
        self.client.v1.billing_portal.configurations.retrieve.side_effect = stripe.InvalidRequestError(
            "private-provider-detail", "configuration", http_status=404
        )
        with self.assertRaises(CommandError) as context:
            self.run_command()
        self.assertNotIn("private-provider-detail", str(context.exception))
        self.assertNotIn("private-provider-detail", str(context.exception.__cause__))
        self.assertIn("HTTP 404", str(context.exception))

    def wire_client(self, portal_response):
        transport = Mock()
        transport.name = "synthetic-no-network"
        price = {**self.client.v1.prices.retrieve.return_value, "object": "price"}
        transport.request_with_retries.side_effect = [
            (json.dumps(price), 200, {}),
            (json.dumps(portal_response), 200, {}),
        ]
        self.client = stripe.StripeClient(
            "synthetic-value-not-a-Stripe-key",
            http_client=transport,
            stripe_version="2026-09-30.endive",
        )
        return transport

    def test_fixed_sdk_serializes_default_filter_without_real_network(self):
        response = {"object": "list", "data": [configuration()], "has_more": False}
        transport = self.wire_client(response)
        self.assertIn("billing_stripe_remote_check=ok", self.run_command())
        self.assertEqual(transport.request_with_retries.call_count, 2)
        calls = transport.request_with_retries.call_args_list
        self.assertTrue(all(call.args[0] == "get" for call in calls))
        target = urlsplit(calls[1].args[1])
        self.assertEqual(target.path, "/v1/billing_portal/configurations")
        self.assertEqual(parse_qs(target.query), {"limit": ["100"], "is_default": ["true"]})

    @override_settings(STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID="bpc_selected")
    def test_fixed_sdk_retrieves_explicit_resource_without_real_network(self):
        response = {**configuration("bpc_selected", default=False), "object": "billing_portal.configuration"}
        transport = self.wire_client(response)
        self.assertIn("billing_stripe_remote_check=ok", self.run_command())
        calls = transport.request_with_retries.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call.args[0] == "get" for call in calls))
        target = urlsplit(calls[1].args[1])
        self.assertEqual(target.path, "/v1/billing_portal/configurations/bpc_selected")
        self.assertEqual(target.query, "")
