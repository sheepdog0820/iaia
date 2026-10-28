"""Actual Sentry envelopes stay offline and omit SDK payloads."""

import json
import logging
from copy import deepcopy
from unittest import TestCase

from tests.unit import test_production_settings as production_probes

MARKER = "synthetic-sdk-private-response-never-send"


def offline_capture(mode):
    import logging
    import sys
    from types import SimpleNamespace
    from unittest.mock import patch

    import sentry_sdk
    from django.conf import settings
    from django.utils.log import configure_logging
    from sentry_sdk.transport import Transport

    envelopes = []

    class OfflineTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    original_init = sentry_sdk.init

    def offline_init(**kwargs):
        kwargs.update(
            transport=OfflineTransport, enable_logs=True, auto_session_tracking=False, send_client_reports=False
        )
        return original_init(**kwargs)

    # Import the actual production settings/init path, changing only transport
    # and enabling Logs for this isolated test. No Sentry/AWS HTTP can occur.
    with patch("sentry_sdk.init", side_effect=offline_init):
        from tableno import settings_production  # noqa: F401

    settings.ADMINS = []
    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
    logging.getLogger().setLevel(logging.INFO)
    client = sentry_sdk.get_client()
    TestCase().assertTrue(client.is_active())
    TestCase().assertIs(client.options["send_default_pii"], False)
    with sentry_sdk.isolation_scope() as scope:
        if mode.startswith("sdk:"):
            name = mode.split(":", 1)[1]
            scope.set_context("synthetic_context", {"memo": MARKER})
            scope.set_extra("synthetic_extra", MARKER)
            scope.set_user({"id": MARKER})
            scope.add_breadcrumb({"category": "synthetic.private", "message": MARKER})
            try:
                raise ValueError(MARKER)
            except ValueError:
                logging.getLogger(name).error("SDK failed: %s", MARKER, exc_info=sys.exc_info(), extra={"memo": MARKER})
        elif mode == "breadcrumb":
            logging.getLogger("botocore.credentials").warning("SDK warning: %s", MARKER, extra={"memo": MARKER})
            sentry_sdk.capture_message("ordinary-followup")
        elif mode == "request_extra":
            request = SimpleNamespace(method="GET", resolver_match=SimpleNamespace(view_name=MARKER))
            logging.getLogger("botocore.credentials").error(MARKER, extra={"request": request, "status_code": MARKER})
        elif mode == "unrelated":
            from sentry_sdk.crons import capture_checkin

            logging.getLogger("botocore_other").error("ordinary-diagnostic", extra={"memo": "ordinary-extra"})
            capture_checkin(monitor_slug="synthetic-offline-only", status="ok")
        else:
            raise AssertionError("Unknown synthetic mode")
    client.flush(timeout=2)
    result = []
    for envelope in envelopes:
        for item in envelope.items:
            if item.type in {"event", "log"}:
                result.append({"type": item.type, "payload": json.loads(item.get_bytes())})
    return {
        "items": result,
        "headers": [envelope.headers for envelope in envelopes],
        "hooks": {
            name: callable(client.options.get(name)) for name in ("before_send", "before_breadcrumb", "before_send_log")
        },
    }


class SentrySDKPrivacyTests(TestCase):
    def test_actual_sdk_error_envelopes_preserve_diagnostics_without_payloads(self):
        for name in ("botocore", "botocore.credentials", "boto3", "boto3.resources.action"):
            with self.subTest(logger=name):
                payload = self.probe("sdk:" + name)
                self.assertNotIn(MARKER, json.dumps(payload))
                events = [item["payload"] for item in payload["items"] if item["type"] == "event"]
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["logger"], name)
                self.assertEqual(events[0]["level"], "error")
                self.assertIn("exception_type=ValueError", events[0]["logentry"]["formatted"])
                self.assertIn("offline_capture", events[0]["logentry"]["formatted"])
                self.assertIn(name, events[0]["fingerprint"])
                self.assertIn("ValueError", " ".join(events[0]["fingerprint"]))
                self.assertTrue(all(payload["hooks"].values()))
                logs = [log for item in payload["items"] if item["type"] == "log" for log in item["payload"]["items"]]
                self.assertTrue(logs)
                self.assertEqual(logs[-1]["level"], "error")
                self.assertEqual(logs[-1]["attributes"]["logger.name"]["value"], name)

    def test_sdk_breadcrumb_is_safe_on_a_later_non_sdk_event(self):
        payload = self.probe("breadcrumb")
        self.assertNotIn(MARKER, json.dumps(payload))
        event = next(item["payload"] for item in payload["items"] if item["type"] == "event")
        crumbs = event["breadcrumbs"]["values"]
        sdk = next(crumb for crumb in crumbs if crumb.get("category") == "botocore.credentials")
        self.assertEqual(sdk["level"], "warning")
        self.assertIn("exception_type=none", sdk["message"])
        self.assertEqual(event["message"], "ordinary-followup")

    def test_sdk_record_request_metadata_cannot_reintroduce_payloads(self):
        payload = self.probe("request_extra")
        self.assertNotIn(MARKER, json.dumps(payload))
        self.assertTrue(payload["items"])

    def test_unrelated_logger_monitoring_is_unchanged(self):
        payload = self.probe("unrelated")
        event = next(item["payload"] for item in payload["items"] if item["type"] == "event")
        self.assertEqual(event["logentry"]["formatted"], "ordinary-diagnostic")
        self.assertEqual(event["extra"]["memo"], "ordinary-extra")
        self.assertEqual(event["logger"], "botocore_other")

    def test_offline_fixture_rejects_unknown_mode(self):
        with self.assertRaisesRegex(AssertionError, "Unknown synthetic mode"):
            self.probe("unknown")

    def probe(self, mode):
        expression = f"""
import json
from tests.unit.test_sentry_sdk_privacy import offline_capture
print(json.dumps(offline_capture({mode!r})))
"""
        return production_probes.ProductionSettingsTests().run_settings_probe(
            {
                "SENTRY_DSN": "https://synthetic-public@example.test/1",
                "ENV_FILE": "",
                "AWS_SECRETS_JSON": "",
                "AWS_SECRETS_FILE": "",
            },
            expression=expression,
        )


class SentrySDKHookTests(TestCase):
    def test_no_record_hints_still_omit_sdk_event_and_breadcrumb_payloads(self):
        from tableno.error_reporting import safe_sentry_breadcrumb, safe_sentry_event

        event = {"logger": "boto3", "message": MARKER, "extra": {"memo": MARKER}, "level": "error"}
        crumb = {"category": "botocore", "message": MARKER, "data": {"memo": MARKER}, "level": "warning"}
        for hint in (
            None,
            {},
            {"log_record": "not-a-record"},
            {"log_record": logging.makeLogRecord({"name": "other"})},
        ):
            with self.subTest(hint=hint):
                original = deepcopy((event, crumb))
                result = (safe_sentry_event(event, hint), safe_sentry_breadcrumb(crumb, hint))
                self.assertNotIn(MARKER, json.dumps(result))
                self.assertEqual((event, crumb), original)
                self.assertIn("payload omitted", result[0]["logentry"]["formatted"])
                self.assertIn("payload omitted", result[1]["message"])

    def test_unrelated_and_missing_logger_metadata_preserve_identity(self):
        from tableno.error_reporting import safe_sentry_breadcrumb, safe_sentry_event, safe_sentry_log

        for name in (None, "", 42, "botocore_other", "boto3_other", "ordinary"):
            with self.subTest(logger=name):
                event = {"logger": name, "message": MARKER}
                crumb = {"category": name, "message": MARKER}
                log = {"attributes": {"logger.name": name}, "body": MARKER}
                self.assertIs(safe_sentry_event(event, {}), event)
                self.assertIs(safe_sentry_breadcrumb(crumb, {}), crumb)
                self.assertIs(safe_sentry_log(log, {}), log)
        for log in ({}, {"attributes": None}):
            self.assertIs(safe_sentry_log(log, {}), log)

    def test_log_hook_omits_extra_and_preserves_original_and_metadata(self):
        from tableno.error_reporting import safe_sentry_log

        log = {
            "body": MARKER,
            "attributes": {"logger.name": "botocore", "code.line.number": 42, "memo": MARKER},
            "severity_text": "warn",
            "severity_number": 13,
            "time_unix_nano": 42,
        }
        original = deepcopy(log)
        safe = safe_sentry_log(log, {})
        self.assertNotIn(MARKER, json.dumps(safe))
        self.assertEqual(log, original)
        self.assertEqual(safe["severity_text"], "warn")
        self.assertEqual(safe["attributes"], {"logger.name": "botocore", "code.line.number": 42})

    def test_record_hint_diagnostics_do_not_mutate_sdk_request_metadata(self):
        from tableno.error_reporting import safe_sentry_breadcrumb, safe_sentry_event, sdk_error_summary

        record = logging.makeLogRecord({"name": "botocore.credentials", "msg": MARKER, "request": MARKER})
        original = record.__dict__.copy()
        event = safe_sentry_event({"message": MARKER}, {"log_record": record})
        crumb = safe_sentry_breadcrumb({"message": MARKER}, {"log_record": record})
        self.assertNotIn(MARKER, json.dumps((event, crumb, sdk_error_summary(record))))
        self.assertEqual(record.__dict__, original)
