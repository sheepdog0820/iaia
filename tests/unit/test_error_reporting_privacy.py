import logging
import sys
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.core import mail
from django.test import RequestFactory, SimpleTestCase, override_settings

from tableno.error_reporting import SafeAdminEmailHandler as AdminEmailHandler
from tableno.error_reporting import SafeRequestFormatter


@override_settings(
    DEBUG=False,
    ADMINS=[("Test", "admin@example.test")],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ErrorReportingPrivacyTests(SimpleTestCase):
    def test_request_log_omits_payload_and_cached_traceback(self):
        record = self.make_record()
        record.exc_text = "fixture-cached-traceback-secret"
        record.stack_info = "fixture-stack-secret"
        original = record.__dict__.copy()
        output = SafeRequestFormatter("%(levelname)s %(message)s").format(record)
        self.assertNotIn("fixture-", output)
        self.assertIn("ValueError", output)
        self.assertIn("group-invite-link-landing", output)
        self.assertIn("make_record", output)
        self.assertEqual(record.__dict__, original)

    def test_ordinary_log_retains_diagnostic_message(self):
        record = logging.LogRecord("tableno", logging.INFO, __file__, 1, "Job finished: %s", (42,), None)
        output = SafeRequestFormatter("%(levelname)s %(message)s").format(record)
        self.assertEqual(output, "INFO Job finished: 42")

    def test_stream_and_file_handlers_both_omit_request_payload(self):
        record = self.make_record()
        original = record.__dict__.copy()
        stream = StringIO()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "errors.log"
            handlers = [logging.StreamHandler(stream), logging.FileHandler(path, encoding="utf-8")]
            try:
                for handler in handlers:
                    handler.setFormatter(SafeRequestFormatter("{levelname} {message}", style="{"))
                    handler.handle(record)
                    handler.flush()
                for output in (stream.getvalue(), path.read_text(encoding="utf-8")):
                    self.assertNotIn("fixture-", output)
                    self.assertIn("ValueError", output)
                    self.assertIn("status=500", output)
            finally:
                for handler in handlers:
                    handler.close()
        self.assertEqual(record.__dict__, original)

    def make_record(self, with_exception=True):
        request = RequestFactory().post(
            "/group-invitations/fixture-path-secret/?next=fixture-query-secret",
            {"memo": "fixture-post-secret"},
            HTTP_AUTHORIZATION="Bearer fixture-header-secret",
            HTTP_COOKIE="sessionid=fixture-cookie-secret",
        )
        request.resolver_match = SimpleNamespace(view_name="group-invite-link-landing")
        exception_info = None
        if with_exception:
            try:
                raise ValueError("fixture-exception-secret")
            except ValueError:
                exception_info = sys.exc_info()
        record = logging.LogRecord(
            "django.request", logging.ERROR, __file__, 1, "Internal Server Error: %s", (request.path,), exception_info
        )
        record.request = request
        record.status_code = 500
        return record

    def test_email_omits_request_values_but_preserves_error_location(self):
        record = self.make_record()
        AdminEmailHandler(include_html=True).emit(record)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        content = message.message().as_string()
        self.assertNotIn("fixture-", content)
        self.assertIn("ValueError", message.body)
        self.assertIn("test_error_reporting_privacy.py", message.body)
        self.assertIn("make_record", message.body)
        self.assertIn("group-invite-link-landing", message.body)
        self.assertIn("500", message.body)
        self.assertEqual(record.args, (record.request.path,))
        self.assertIn("fixture-path-secret", record.request.path)

    def test_event_without_exception_does_not_echo_message(self):
        record = self.make_record(with_exception=False)
        AdminEmailHandler().emit(record)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("fixture-", mail.outbox[0].message().as_string())
        self.assertIn("django.request", mail.outbox[0].body)

    @override_settings(ADMINS=[])
    def test_no_admin_recipient_sends_nothing(self):
        AdminEmailHandler().emit(self.make_record())
        self.assertEqual(mail.outbox, [])

    def test_missing_request_metadata_has_safe_diagnostics(self):
        record = self.make_record(with_exception=False)
        del record.request
        record.status_code = "fixture-status-secret"
        AdminEmailHandler().emit(record)
        body = mail.outbox[0].body
        self.assertNotIn("fixture-", body)
        self.assertIn("route=unresolved", body)
        self.assertIn("method=unknown", body)
        self.assertIn("status=unknown", body)
