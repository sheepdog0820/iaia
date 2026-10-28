import json
from datetime import timedelta
from unittest.mock import Mock, patch

import boto3
from botocore.awsrequest import AWSResponse
from botocore.config import Config
from botocore.exceptions import ReadTimeoutError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.background_removal_tasks import cleanup_background_removal_jobs, process_background_removal_job
from accounts.models import BackgroundRemovalJob
from tests.integration.test_background_dispatch_integrity import DispatchFixtureMixin


@override_settings(
    BACKGROUND_REMOVAL_TASK_DEFINITION="synthetic-worker:1",
    BACKGROUND_REMOVAL_SUBNETS=["synthetic-subnet"],
    BACKGROUND_REMOVAL_SECURITY_GROUPS=["synthetic-group"],
)
class BackgroundRetryOutcomeTests(DispatchFixtureMixin, TestCase):
    @staticmethod
    def sdk_response(http_status, code):
        raw = Mock()
        raw.stream.return_value = [json.dumps({"__type": code, "message": "synthetic-private-detail"}).encode()]
        return AWSResponse(
            "https://synthetic.invalid/", http_status, {"content-type": "application/x-amz-json-1.1"}, raw
        )

    def launch(self, *, code="InvalidParameterException", http_status=400, first="timeout", mode="standard"):
        ecs = boto3.client(
            "ecs",
            region_name="ap-northeast-1",
            aws_access_key_id="synthetic-unused-access-key",
            aws_secret_access_key="synthetic-unused-secret-key",  # nosec B106 # Synthetic signing only; _send replaced.
            config=Config(retries={"mode": mode, "total_max_attempts": 2}),
        )
        self.addCleanup(ecs.close)
        metadata = []
        before = []

        def record_response(parsed, **kwargs):
            metadata.append(parsed["ResponseMetadata"].copy())

        ecs.meta.events.register("after-call.ecs.RunTask", record_response)
        refused = self.sdk_response(http_status, code)
        attempts = [refused]
        if first == "timeout":
            attempts.insert(0, ReadTimeoutError(endpoint_url="synthetic-private-detail"))
        elif first == "server":
            attempts.insert(0, self.sdk_response(500, "ServerException"))
        responses = iter(attempts)

        def send_response(request):
            if not before:
                job = BackgroundRemovalJob.objects.get()
                before.append((job.updated_at, job.source_image.name))
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return response

        with (
            patch("boto3.client", return_value=ecs),
            patch.object(ecs._endpoint, "_send", side_effect=send_response) as send,
            patch("botocore.endpoint.time.sleep"),
            self.assertLogs("accounts.views.character_image_views", level="WARNING") as logs,
        ):
            response = self.post_image()
        self.assertNotIn("synthetic-private-detail", "\n".join(logs.output))
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(metadata[0]["RetryAttempts"], 0 if first == "none" else 1)
        self.assertEqual(send.call_count, 1 if first == "none" else 2)
        bodies = [json.loads(call.args[0].body) for call in send.call_args_list]
        self.assertTrue(all(body == bodies[0] for body in bodies))
        self.assertEqual(bodies[0]["clientToken"], str(job.pk))
        return response, job, before[0]

    def assert_pending_input(self, response, job, before):
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.PENDING)
        self.assertEqual(response.data["job_id"], str(job.pk))
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertEqual((job.updated_at, job.source_image.name), before)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        self.assertEqual(job.error_message, "")
        self.assertEqual(job.task_arn, "")

    def test_timeout_then_validation_error_keeps_pending_input(self):
        self.assert_pending_input(*self.launch())

    def test_server_error_then_access_denied_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(first="server", code="AccessDeniedException", http_status=403))

    def test_timeout_then_missing_resource_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(code="ClusterNotFoundException", http_status=400))

    def test_legacy_retry_then_validation_error_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(mode="legacy"))

    def test_single_validation_error_still_fails_and_removes_input(self):
        response, job, before = self.launch(first="none")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)
        self.assertFalse(job.source_image.storage.exists(before[1]))

    def test_single_access_denied_still_fails_and_removes_input(self):
        response, job, before = self.launch(first="none", code="AccessDeniedException", http_status=403)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)
        self.assertFalse(job.source_image.storage.exists(before[1]))

    @patch("accounts.background_removal_tasks.remove_background")
    def test_retried_rejection_keeps_duplicate_guard_and_late_worker_result(self, inference):
        response, job, before = self.launch()
        self.assert_pending_input(response, job, before)
        with patch("boto3.client") as boto_client:
            self.assertEqual(self.post_image().status_code, 409)
        boto_client.assert_not_called()
        self.assertEqual(BackgroundRemovalJob.objects.count(), 1)
        inference.return_value = self.image_bytes()
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertFalse(processed.source_image)
        result = self.client.get(response.data["status_url"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, self.image_bytes())
        self.assertIn("no-store", result["Cache-Control"])

    @patch("accounts.background_removal_tasks.remove_background")
    def test_unconfirmed_retried_rejection_expires_without_late_inference(self, inference):
        response, job, before = self.launch()
        self.assert_pending_input(response, job, before)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(cleanup_background_removal_jobs()["timed_out_jobs"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image.storage.exists(before[1]))
        process_background_removal_job(job.pk)
        inference.assert_not_called()
