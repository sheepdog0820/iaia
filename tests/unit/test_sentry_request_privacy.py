"""Capture actual Django exception envelopes offline, without real HTTP delivery."""

import json
import logging
from copy import deepcopy
from unittest import TestCase

from django.http import HttpResponse
from django.urls import path

from tests.unit import test_production_settings as production_probes
from tests.unit import test_sentry_sdk_privacy as sdk_probes

MARKER = "synthetic-http-private-body-and-url"


def synthetic_http_error(request, token):
    raise ValueError(request.POST["private_note"])


def synthetic_server_error(request):
    return HttpResponse("検証用エラー", status=500)


urlpatterns = [path("synthetic/<str:token>/", synthetic_http_error, name="synthetic-private-view")]
handler500 = synthetic_server_error


def offline_http_capture(mode="http"):
    import logging
    import sys
    from types import SimpleNamespace
    from unittest.mock import patch

    import django
    import sentry_sdk
    from django.test import Client, override_settings
    from sentry_sdk.transport import Transport

    envelopes = []

    class OfflineTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    original_init = sentry_sdk.init

    def offline_init(**kwargs):
        kwargs.update(
            transport=OfflineTransport,
            enable_logs=True,
            traces_sample_rate=0,
            auto_session_tracking=False,
            send_client_reports=False,
        )
        return original_init(**kwargs)

    with patch("sentry_sdk.init", side_effect=offline_init):
        from tableno import settings_production  # noqa: F401

    django.setup()
    client = sentry_sdk.get_client()
    TestCase().assertTrue(client.is_active())
    with (
        override_settings(
            ROOT_URLCONF=__name__,
            MIDDLEWARE=[],
            ALLOWED_HOSTS=["testserver"],
            DEBUG=False,
            SECURE_SSL_REDIRECT=False,
            ADMINS=[],
        ),
        sentry_sdk.isolation_scope() as scope,
    ):
        status = None
        if mode == "breadcrumb":
            logging.getLogger("django.security.csrf").warning(MARKER)
            sentry_sdk.capture_message("ordinary-followup")
        elif mode in {"http", "request_record"}:
            scope.set_context("synthetic_private", {"memo": MARKER})
            scope.set_extra("synthetic_private", MARKER)
            if mode == "http":
                response = Client(raise_request_exception=False).post(
                    f"/synthetic/{MARKER}/?private_query={MARKER}", {"private_note": MARKER}
                )
                status = response.status_code
            else:
                request = SimpleNamespace(
                    method="POST", resolver_match=SimpleNamespace(view_name="synthetic-private-view")
                )
                try:
                    raise ValueError(MARKER)
                except ValueError:
                    logging.getLogger("tableno.request_fixture").error(
                        MARKER, exc_info=sys.exc_info(), extra={"request": request, "private_note": MARKER}
                    )
        else:
            raise AssertionError("Unknown offline mode")
    client.flush(timeout=2)
    items = [
        {"type": item.type, "payload": json.loads(item.get_bytes())}
        for envelope in envelopes
        for item in envelope.items
        if item.type in {"event", "log"}
    ]
    return {"status": status, "items": items}


class SentryRequestPrivacyTests(TestCase):
    def test_actual_django_handler_omits_body_url_exception_and_private_scope(self):
        payload = self.probe("http")
        self.assertEqual(payload["status"], 500)
        events = [item["payload"] for item in payload["items"] if item["type"] == "event"]
        self.assertEqual(len(events), 1)
        self.assertNotIn(MARKER, json.dumps(payload))
        self.assertEqual(events[0]["logger"], "django.request")
        self.assertIn("exception_type=ValueError", events[0]["logentry"]["formatted"])
        self.assertIn("synthetic_http_error", events[0]["logentry"]["formatted"])
        exception = events[0]["exception"]["values"][0]
        self.assertEqual(exception["type"], "ValueError")
        self.assertEqual(exception["mechanism"], {"type": "django", "handled": False})

    def test_request_record_from_app_logger_and_logs_omit_extra_payloads(self):
        payload = self.probe("request_record")
        self.assertNotIn(MARKER, json.dumps(payload))
        events = [item["payload"] for item in payload["items"] if item["type"] == "event"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["logger"], "tableno.request_fixture")
        self.assertIn("route=synthetic-private-view", events[0]["logentry"]["formatted"])
        self.assertIn("exception_type=ValueError", events[0]["logentry"]["formatted"])
        logs = [log for item in payload["items"] if item["type"] == "log" for log in item["payload"]["items"]]
        self.assertTrue(logs)
        self.assertEqual(logs[-1]["attributes"]["logger.name"]["value"], "tableno.request_fixture")

    def test_security_breadcrumb_and_logs_are_safe_on_later_ordinary_event(self):
        payload = self.probe("breadcrumb")
        self.assertNotIn(MARKER, json.dumps(payload))
        event = next(item["payload"] for item in payload["items"] if item["type"] == "event")
        self.assertEqual(event["message"], "ordinary-followup")
        crumb = next(c for c in event["breadcrumbs"]["values"] if c.get("category") == "django.security.csrf")
        self.assertIn("exception_type=none", crumb["message"])
        self.assertTrue(any(item["type"] == "log" for item in payload["items"]))

    def probe(self, mode):
        expression = f"""
import json
from tests.unit.test_sentry_request_privacy import offline_http_capture
print(json.dumps(offline_http_capture({mode!r})))
"""
        return production_probes.ProductionSettingsTests().run_settings_probe(
            {"SENTRY_DSN": "https://synthetic-public@example.test/1", "AWS_SECRETS_JSON": "", "AWS_SECRETS_FILE": ""},
            expression=expression,
        )

    def test_actual_security_logger_envelopes_keep_diagnostics_without_payloads(self):
        for name in ("django.security.DisallowedHost", "django.security.csrf"):
            with self.subTest(logger=name):
                payload = sdk_probes.SentrySDKPrivacyTests().probe("sdk:" + name)
                events = [item["payload"] for item in payload["items"] if item["type"] == "event"]
                self.assertEqual(len(events), 1)
                self.assertNotIn(sdk_probes.MARKER, json.dumps(payload))
                self.assertIn("exception_type=ValueError", events[0]["logentry"]["formatted"])
                self.assertIn("offline_capture", events[0]["logentry"]["formatted"])
                self.assertEqual(events[0]["exception"]["values"][0]["mechanism"], {"type": "logging", "handled": True})


class SentryRequestHookTests(TestCase):
    def test_request_exception_keeps_only_safe_type_and_handled_state(self):
        from tableno.error_reporting import safe_sentry_event

        record = logging.makeLogRecord(
            {
                "name": "tableno.request_fixture",
                "msg": MARKER,
                "request": None,
                "exc_info": (ValueError, ValueError(MARKER), None),
            }
        )
        cases = [
            (None, {"type": "logging", "handled": True}),
            ({"type": "django", "handled": True, "data": MARKER}, {"type": "django", "handled": True}),
            ({"type": "django", "handled": MARKER}, {"type": "django", "handled": False}),
            ({"type": "logging", "handled": False}, {"type": "logging", "handled": False}),
            ({"type": MARKER, "handled": False}, {"type": "logging", "handled": True}),
        ]
        for mechanism, expected in cases:
            with self.subTest(mechanism=mechanism):
                event = {"exception": {"values": [{"value": MARKER, "mechanism": mechanism}]}}
                original = deepcopy(event)
                original_record = record.__dict__.copy()
                safe = safe_sentry_event(event, {"log_record": record})
                self.assertNotIn(MARKER, json.dumps(safe))
                self.assertEqual(safe["exception"]["values"], [{"type": "ValueError", "mechanism": expected}])
                self.assertEqual(event, original)
                self.assertEqual(record.__dict__, original_record)

    def test_missing_record_hints_still_remove_request_and_django_exception_data(self):
        from tableno.error_reporting import safe_sentry_event

        events = [
            {"logger": "django.request", "message": MARKER, "level": "warning"},
            {"request": {"data": MARKER}, "extra": {"memo": MARKER}},
            {"exception": {"values": [{"value": MARKER, "mechanism": {"type": "django"}}]}},
        ]
        for event in events:
            for hint in (None, {}, {"log_record": "invalid"}, {"log_record": logging.makeLogRecord({"name": "other"})}):
                with self.subTest(event=event, hint=hint):
                    original = deepcopy(event)
                    safe = safe_sentry_event(event, hint)
                    self.assertNotIn(MARKER, json.dumps(safe))
                    self.assertEqual(event, original)
                    if event.get("level") == "warning" and not isinstance(
                        (hint or {}).get("log_record"), logging.LogRecord
                    ):
                        self.assertIn("level=WARNING", safe["logentry"]["formatted"])

    def test_security_breadcrumb_without_log_record_hint_omits_data(self):
        from tableno.error_reporting import safe_sentry_breadcrumb

        crumb = {"category": "django.security.csrf", "message": MARKER, "data": {"memo": MARKER}, "level": "warning"}
        original = deepcopy(crumb)
        safe = safe_sentry_breadcrumb(crumb, None)
        self.assertNotIn(MARKER, json.dumps(safe))
        self.assertEqual(crumb, original)
        self.assertEqual(safe["category"], "django.security.csrf")
        self.assertIn("level=WARNING", safe["message"])

    def test_unrelated_exception_metadata_preserves_original_event(self):
        from tableno.error_reporting import safe_sentry_event

        for values in (None, [], [None], [{"mechanism": None}], [{"mechanism": {"type": "logging"}}]):
            with self.subTest(values=values):
                event = {"logger": "ordinary", "message": MARKER, "exception": {"values": values}}
                self.assertIs(safe_sentry_event(event, None), event)
