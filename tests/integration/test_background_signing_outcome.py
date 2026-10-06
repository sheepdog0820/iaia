import json
from datetime import timedelta
from unittest.mock import Mock, patch

import boto3
from botocore.awsrequest import AWSResponse
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError, ReadTimeoutError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.background_removal_tasks import cleanup_background_removal_jobs, process_background_removal_job
from accounts.models import BackgroundRemovalJob
from tests.integration import test_background_retry_outcome as retry_tests
from tests.integration.test_background_dispatch_integrity import DispatchFixtureMixin


@override_settings(
    BACKGROUND_REMOVAL_TASK_DEFINITION="synthetic-worker:1",
    BACKGROUND_REMOVAL_SUBNETS=["synthetic-subnet"],
    BACKGROUND_REMOVAL_SECURITY_GROUPS=["synthetic-group"],
)
class BackgroundSigningOutcomeTests(DispatchFixtureMixin, TestCase):
    def sdk_client(self, mode="standard"):
        ecs = boto3.client(
            "ecs",
            region_name="ap-northeast-1",
            aws_access_key_id="synthetic-unused-access-key",
            aws_secret_access_key="synthetic-unused-secret-key",  # nosec B106 # Synthetic signing only; _send replaced.
            config=Config(retries={"mode": mode, "total_max_attempts": 2}),
        )
        self.addCleanup(ecs.close)
        return ecs

    def launch(self, *, first="timeout", mode="standard", refresh_error=False):
        ecs = self.sdk_client(mode)
        credentials = ecs._request_signer._credentials.get_frozen_credentials()
        interruption = NoCredentialsError()
        if refresh_error == "client":
            interruption = ClientError(
                {
                    "Error": {"Code": "AccessDenied", "Message": "synthetic-private-detail"},
                    "ResponseMetadata": {"HTTPStatusCode": 403, "RetryAttempts": 0},
                },
                "AssumeRole",
            )
        elif refresh_error:
            interruption = RuntimeError("synthetic-private-detail")
        before = []
        signed_bodies = []
        final_response = Mock()

        def signing(request, **kwargs):
            signed_bodies.append(json.loads(request.body))
            if not before:
                job = BackgroundRemovalJob.objects.get()
                before.append((job.updated_at, job.source_image.name))

        ecs.meta.events.register("before-sign.ecs.RunTask", signing)
        ecs.meta.events.register("after-call.ecs.RunTask", final_response)
        handlers_before = list(ecs.meta.events._emitter._handlers.prefix_search("needs-retry.ecs.RunTask"))
        credential_results = [interruption] if first == "none" else [credentials, interruption]
        wire_response = ReadTimeoutError(endpoint_url="synthetic-private-detail")
        if first == "server":
            wire_response = retry_tests.BackgroundRetryOutcomeTests.sdk_response(500, "ServerException")
        elif first == "throttled":
            wire_response = retry_tests.BackgroundRetryOutcomeTests.sdk_response(400, "ThrottlingException")
        elif first == "conflict":
            wire_response = retry_tests.BackgroundRetryOutcomeTests.sdk_response(400, "ConflictException")
            # Exercise the modeled ambiguity path; this is not the SDK's default retry policy.
            ecs.meta.events.register("needs-retry.ecs.RunTask", lambda **kwargs: 0)
            handlers_before = list(ecs.meta.events._emitter._handlers.prefix_search("needs-retry.ecs.RunTask"))
        with (
            patch("boto3.client", return_value=ecs),
            patch.object(ecs._request_signer._credentials, "get_frozen_credentials", side_effect=credential_results),
            patch.object(ecs._endpoint, "_send", side_effect=[wire_response]) as send,
            patch("botocore.endpoint.time.sleep"),
            self.assertLogs("accounts.views.character_image_views", level="WARNING") as logs,
        ):
            response = self.post_image()
        self.assertNotIn("synthetic-private-detail", "\n".join(logs.output))
        final_response.assert_not_called()  # No final response or RetryAttempts metadata exists.
        self.assertEqual(send.call_count, 0 if first == "none" else 1)
        self.assertEqual(len(signed_bodies), 1 if first == "none" else 2)
        self.assertTrue(all(body == signed_bodies[0] for body in signed_bodies))
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(signed_bodies[0]["clientToken"], str(job.pk))
        self.assertEqual(
            list(ecs.meta.events._emitter._handlers.prefix_search("needs-retry.ecs.RunTask")), handlers_before
        )
        return response, job, before[0]

    def launch_explicit_failure(self, *, timeout):
        ecs = self.sdk_client()
        raw = Mock()
        raw.stream.return_value = [
            json.dumps({"tasks": [], "failures": [{"reason": "synthetic-private-detail"}]}).encode()
        ]
        refused = AWSResponse("https://synthetic.invalid/", 200, {"content-type": "application/x-amz-json-1.1"}, raw)
        replies = [ReadTimeoutError(endpoint_url="synthetic-private-detail"), refused] if timeout else [refused]
        job_before = []

        def signing(**kwargs):
            if not job_before:
                job = BackgroundRemovalJob.objects.get()
                job_before.append((job.updated_at, job.source_image.name))

        ecs.meta.events.register("before-sign.ecs.RunTask", signing)
        handlers_before = list(ecs.meta.events._emitter._handlers.prefix_search("needs-retry.ecs.RunTask"))
        with (
            patch("boto3.client", return_value=ecs),
            patch.object(ecs._endpoint, "_send", side_effect=replies) as send,
            patch("botocore.endpoint.time.sleep"),
            self.assertLogs("accounts.views.character_image_views", level="WARNING") as logs,
        ):
            response = self.post_image()
        self.assertNotIn("synthetic-private-detail", "\n".join(logs.output))
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(send.call_count, 2 if timeout else 1)
        bodies = [json.loads(call.args[0].body) for call in send.call_args_list]
        self.assertTrue(all(body == bodies[0] for body in bodies))
        self.assertEqual(bodies[0]["clientToken"], str(job.pk))
        self.assertEqual(
            list(ecs.meta.events._emitter._handlers.prefix_search("needs-retry.ecs.RunTask")), handlers_before
        )
        return response, job, job_before[0]

    def assert_pending_input(self, response, job, before):
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.PENDING)
        self.assertEqual(response.data["job_id"], str(job.pk))
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertEqual((job.updated_at, job.source_image.name), before)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        self.assertEqual(job.error_message, "")
        self.assertEqual(job.task_arn, "")

    def assert_failed_input(self, response, job, before):
        self.assertEqual(response.status_code, 503)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)
        self.assertFalse(job.source_image.storage.exists(before[1]))

    def test_timeout_then_signing_failure_keeps_pending_input(self):
        self.assert_pending_input(*self.launch())

    def test_server_error_then_signing_failure_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(first="server"))

    def test_legacy_timeout_then_signing_failure_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(mode="legacy"))

    def test_timeout_then_credential_refresh_error_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(refresh_error=True))

    def test_timeout_then_credential_client_error_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(refresh_error="client"))

    def test_conflict_then_signing_failure_keeps_pending_input(self):
        self.assert_pending_input(*self.launch(first="conflict"))

    def test_initial_signing_failure_remains_definite_failure(self):
        self.assert_failed_input(*self.launch(first="none"))

    def test_initial_refresh_error_remains_definite_failure(self):
        self.assert_failed_input(*self.launch(first="none", refresh_error=True))

    def test_initial_credential_client_error_remains_definite_failure(self):
        self.assert_failed_input(*self.launch(first="none", refresh_error="client"))

    def test_throttling_then_signing_failure_remains_definite_failure(self):
        self.assert_failed_input(*self.launch(first="throttled"))

    def test_timeout_then_explicit_failure_keeps_pending_input(self):
        self.assert_pending_input(*self.launch_explicit_failure(timeout=True))

    def test_initial_explicit_failure_remains_definite_failure(self):
        self.assert_failed_input(*self.launch_explicit_failure(timeout=False))

    @patch("accounts.background_removal_tasks.remove_background")
    def test_signing_interruption_keeps_duplicate_guard_and_late_worker_result(self, inference):
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
    def test_signing_interruption_expires_without_late_inference(self, inference):
        response, job, before = self.launch()
        self.assert_pending_input(response, job, before)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(cleanup_background_removal_jobs()["timed_out_jobs"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image.storage.exists(before[1]))
        process_background_removal_job(job.pk)
        inference.assert_not_called()
