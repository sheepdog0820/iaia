"""SDK payloads never reach the configured stream, file, or root handlers."""

import logging
import sys
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from unittest.mock import patch

from botocore.credentials import RefreshableCredentials
from botocore.exceptions import MetadataRetrievalError
from django.test import SimpleTestCase

from tableno.error_reporting import SafeRequestFormatter
from tests.unit import test_production_settings as production_probes

PAYLOAD = "synthetic-sdk-response-body-not-for-logs"


def refresh_credentials(mandatory=True):
    """Real SDK refresh logic, synthetic callback only; no AWS/network requests."""

    def fail_refresh():
        try:
            raise ValueError(PAYLOAD)
        except ValueError as exc:
            raise MetadataRetrievalError(error_msg=PAYLOAD) from exc

    credentials = RefreshableCredentials.create_from_metadata(
        metadata={  # Offline-only, unusable values; no client or network.
            "access_key": "synthetic-access",
            "secret_key": "synthetic-secret",  # nosec B105
            "token": "synthetic-token",  # nosec B105
            "expiry_time": (datetime.now(timezone.utc) + timedelta(minutes=8 if mandatory else 12)).isoformat(),
        },
        refresh_using=fail_refresh,
        method="synthetic-container",
    )
    try:
        credentials.get_frozen_credentials()
    except MetadataRetrievalError:
        return "raised"
    return "retained"


class SDKLoggingPrivacyTests(SimpleTestCase):
    def test_formatter_redacts_sdk_messages_args_and_chained_exceptions(self):
        try:
            raise ValueError(PAYLOAD)
        except ValueError:
            exception_info = sys.exc_info()
        for name in ("botocore", "botocore.credentials", "boto3", "boto3.resources.action"):
            with self.subTest(logger=name):
                record = logging.LogRecord(name, logging.WARNING, __file__, 1, "Request %s", (PAYLOAD,), exception_info)
                record.exc_text = PAYLOAD
                record.stack_info = PAYLOAD
                original = record.__dict__.copy()
                output = SafeRequestFormatter("%(levelname)s %(message)s").format(record)
                self.assertNotIn(PAYLOAD, output)
                self.assertIn(f"logger={name}", output)
                self.assertIn("level=WARNING", output)
                self.assertIn("exception_type=ValueError", output)
                self.assertIn("test_formatter_redacts_sdk", output)
                self.assertEqual(record.__dict__, original)

    def test_debug_event_without_exception_omits_request_and_credential_values(self):
        record = logging.LogRecord("botocore.endpoint", logging.DEBUG, __file__, 1, PAYLOAD, (), None)
        output = SafeRequestFormatter("%(message)s").format(record)
        self.assertNotIn(PAYLOAD, output)
        self.assertIn("level=DEBUG", output)
        self.assertIn("exception_type=none", output)

    def test_unrelated_logger_names_keep_their_messages(self):
        for name in ("botocore_other", "boto3_other", "tableno", "daphne.server"):
            with self.subTest(logger=name):
                record = logging.LogRecord(name, logging.INFO, __file__, 1, "Finished %s", (42,), None)
                self.assertEqual(SafeRequestFormatter("%(message)s").format(record), "Finished 42")

    def test_production_stream_and_file_destinations_are_safe_without_email(self):
        for stdout, files in ((True, False), (False, True), (True, True), (False, False)):
            with self.subTest(stdout=stdout, files=files), TemporaryDirectory() as directory:
                payload = self.probe(stdout=stdout, files=files, directory=directory)
                self.assert_safe_probe(payload)
                self.assertEqual(bool(payload["file"]), files)
                self.assertEqual(bool(payload["stream"]), stdout or not files)

    def test_development_logging_cannot_propagate_sdk_payloads_to_root(self):
        self.assert_safe_probe(self.probe(local=True))

    def test_root_verbosity_still_controls_sdk_event_selection(self):
        for local in (False, True):
            for level in (logging.WARNING, logging.INFO, logging.DEBUG):
                with self.subTest(local=local, level=level):
                    payload = self.probe(local=local, level=level)
                    self.assert_safe_probe(payload)
                    self.assertEqual(payload["effective_levels"], [level, level])
                    self.assertEqual("logger=botocore.endpoint" in payload["stream"], level == logging.DEBUG)

    def assert_safe_probe(self, payload):
        for output in (payload["stream"], payload["file"], payload["root"]):
            self.assertNotIn(PAYLOAD, output)
            self.assertNotIn("synthetic-secret", output)
        combined = payload["stream"] + payload["file"]
        self.assertIn("logger=botocore.credentials", combined)
        self.assertIn("level=WARNING", combined)
        self.assertIn("exception_type=MetadataRetrievalError", combined)
        self.assertIn("fail_refresh", combined)
        self.assertIn("logger=boto3.resources", combined)
        self.assertEqual(payload["outcomes"], ["raised", "retained"])
        self.assertEqual(payload["mail_calls"], 0)
        self.assertEqual(payload["propagate"], [False, False])
        self.assertEqual(payload["levels"], [logging.NOTSET, logging.NOTSET])
        self.assertEqual(payload["disabled"], [False, False])
        self.assertIn("ordinary-root-event", payload["root"])
        self.assertNotIn("botocore", payload["root"])
        self.assertNotIn("boto3", payload["root"])

    def probe(self, *, local=False, stdout=True, files=False, directory=None, level=logging.INFO):
        expression = f"""
import contextlib
import io
import json
import logging
import logging.config
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.utils.log import configure_logging
from tests.unit.test_sdk_logging_privacy import PAYLOAD, refresh_credentials

root_output = io.StringIO()
logging.basicConfig(level={level}, stream=root_output, format='%(levelname)s %(message)s')
# Existing descendants must also be reset by dictConfig, not just future loggers.
logging.getLogger('botocore.credentials')
logging.getLogger('boto3.resources')
stream = io.StringIO()
with contextlib.redirect_stderr(stream):
    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
    with patch('tableno.error_reporting.SafeAdminEmailHandler.send_mail') as send_mail:
        outcomes = [refresh_credentials(True), refresh_credentials(False)]
        logging.getLogger('boto3.resources').error(PAYLOAD)
        logging.getLogger('botocore.endpoint').debug('Request %s', {{'Authorization': PAYLOAD}})
        logging.getLogger('ordinary').warning('ordinary-root-event')
    for logger_name in ('botocore', 'boto3'):
        for handler in logging.getLogger(logger_name).handlers:
            handler.flush()
    file_path = Path(settings.LOG_DIR) / 'tableno.log' if {files} else None
    payload = {{
        'stream': stream.getvalue(), 'root': root_output.getvalue(),
        'file': file_path.read_text(encoding='utf-8') if file_path else '',
        'outcomes': outcomes, 'mail_calls': send_mail.call_count,
        'propagate': [logging.getLogger(n).propagate for n in ('botocore', 'boto3')],
        'levels': [logging.getLogger(n).level for n in ('botocore', 'boto3')],
        'effective_levels': [logging.getLogger(n).getEffectiveLevel() for n in ('botocore', 'boto3')],
        'disabled': [logging.getLogger(n).disabled for n in ('botocore', 'boto3')],
    }}
logging.shutdown()
print(json.dumps(payload))
"""
        overrides = {
            "ENV_FILE": "",
            "AWS_SECRETS_JSON": "",
            "AWS_SECRETS_FILE": "",
            "SENTRY_DSN": "",
            "LOG_TO_STDOUT": str(stdout),
            "ENABLE_FILE_LOGGING": str(files),
            "USE_REDIS_CACHE": "False",
            "DB_ENGINE": "sqlite" if local else "postgres",
            "LOG_DIR": directory or "unused-sdk-log-fixture",
            "DJANGO_SETTINGS_MODULE": "tableno.settings" if local else "tableno.settings_production",
        }
        # Reuse the established synthetic settings environment without importing
        # its TestCase into this module (which would duplicate test discovery).
        with patch.dict("os.environ", overrides):
            return production_probes.ProductionSettingsTests().run_settings_probe(overrides, expression=expression)
