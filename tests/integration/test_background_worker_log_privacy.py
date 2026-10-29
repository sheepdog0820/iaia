from datetime import timedelta
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from accounts.background_removal_tasks import (
    cleanup_background_removal_jobs,
    clear_background_removal_source,
    process_background_removal_job,
)
from accounts.models import BackgroundRemovalJob
from tableno.error_reporting import SafeRequestFormatter
from tests.integration.test_background_job_finalization_integrity import BackgroundJobFixtureMixin

PRIVATE_DETAIL = "synthetic-private-portrait.png?X-Amz-Signature=synthetic-signature-token"
LOGGER = "accounts.background_removal_tasks"


class BackgroundWorkerLogPrivacyTests(BackgroundJobFixtureMixin, TestCase):
    def assert_private_diagnostic(self, logs, job, error_type):
        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        # A worker has no HTTP request attribute; inspect the actual production formatter.
        rendered = SafeRequestFormatter("%(levelname)s %(name)s %(message)s").format(record)
        self.assertNotIn(PRIVATE_DETAIL, rendered)
        self.assertIsNone(record.exc_info)
        self.assertIsNone(record.exc_text)
        self.assertNotIn(PRIVATE_DETAIL, str(record.__dict__))
        self.assertIn(str(job.pk), rendered)
        self.assertIn(error_type.__name__, rendered)

    def test_source_cleanup_failure_keeps_reference_and_hides_exception_body(self):
        job = self.create_job()
        source_name = job.source_image.name
        with (
            patch.object(job.source_image.storage, "delete", side_effect=OSError(PRIVATE_DETAIL)),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            self.assertFalse(clear_background_removal_source(job))
        self.assertEqual(job.source_image.name, source_name)
        self.assertTrue(job.source_image.storage.exists(source_name))
        self.assert_private_diagnostic(logs, job, OSError)

    def test_retention_failure_keeps_result_and_hides_exception_body(self):
        job = self.create_job(status=BackgroundRemovalJob.Status.COMPLETED)
        job.result_image.save("synthetic-result.png", ContentFile(self.image_bytes()))
        result_name = job.result_image.name
        now = timezone.now()
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=now - timedelta(hours=25))
        with (
            patch.object(job.result_image.storage, "delete", side_effect=OSError(PRIVATE_DETAIL)),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            summary = cleanup_background_removal_jobs(now=now)
        job.refresh_from_db()
        self.assertEqual(summary["failed_jobs"], 1)
        self.assertEqual(summary["deleted_result_images"], 0)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(job.result_image.name, result_name)
        self.assertTrue(job.result_image.storage.exists(result_name))
        self.assert_private_diagnostic(logs, job, OSError)

    def test_inference_failure_keeps_failed_outcome_and_hides_exception_body(self):
        job = self.create_job()
        with (
            patch("accounts.background_removal_tasks.remove_background", side_effect=ValueError(PRIVATE_DETAIL)),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(processed.error_message, "Background removal could not be completed.")
        self.assertFalse(processed.source_image)
        self.assertFalse(processed.result_image)
        self.assert_private_diagnostic(logs, job, ValueError)

    def test_result_write_failure_keeps_failed_outcome_and_hides_exception_body(self):
        job = self.create_job()
        with (
            patch("accounts.background_removal_tasks.remove_background", return_value=self.image_bytes()),
            patch.object(job.result_image.storage, "save", side_effect=OSError(PRIVATE_DETAIL)),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(processed.error_message, "Background removal could not be completed.")
        self.assertFalse(processed.source_image)
        self.assertFalse(processed.result_image)
        self.assert_private_diagnostic(logs, job, OSError)
