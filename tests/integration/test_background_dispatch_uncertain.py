import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import Mock, patch

import boto3
from botocore.awsrequest import AWSResponse
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    EndpointConnectionError,
    NoCredentialsError,
    ParamValidationError,
    ReadTimeoutError,
    ResponseStreamingError,
)
from botocore.parsers import ResponseParserError
from django.core.files.base import ContentFile
from django.db import OperationalError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.background_removal_tasks import (
    cleanup_background_removal_jobs,
    process_background_removal_job,
    start_background_removal_task,
)
from accounts.models import BackgroundRemovalJob
from tests.integration import test_background_dispatch_integrity as dispatch_tests


def client_error(code, http_status=None):
    response = {"Error": {"Code": code, "Message": "synthetic-private-backend-detail"}}
    if http_status is not None:
        response["ResponseMetadata"] = {"HTTPStatusCode": http_status}
    return ClientError(response, "RunTask")


@override_settings(
    BACKGROUND_REMOVAL_TASK_DEFINITION="synthetic-worker:1",
    BACKGROUND_REMOVAL_SUBNETS=["synthetic-subnet"],
    BACKGROUND_REMOVAL_SECURITY_GROUPS=["synthetic-group"],
)
class BackgroundUncertainDispatchTests(dispatch_tests.DispatchFixtureMixin, TestCase):
    def clear_jobs(self):
        for job in BackgroundRemovalJob.objects.all():
            job.source_image.delete()
            job.delete()

    @patch("boto3.client")
    def test_transport_server_and_conflict_errors_keep_pending_source_and_timestamp(self, boto_client):
        errors = [
            ReadTimeoutError(endpoint_url="synthetic-private-backend-detail"),
            ConnectionClosedError(endpoint_url="synthetic-private-backend-detail"),
            EndpointConnectionError(endpoint_url="synthetic-private-backend-detail"),
            ResponseStreamingError(error="synthetic-private-backend-detail"),
            ResponseParserError("synthetic-private-backend-detail"),
            client_error("ServerException", 500),
            client_error("UnknownServiceError", 502),
            client_error("ServerException"),
            client_error("ConflictException", 400),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__, code=getattr(error, "response", {})):
                self.clear_jobs()
                before = []

                def lose_response(**kwargs):
                    job = BackgroundRemovalJob.objects.get()
                    before.append((job.updated_at, job.source_image.name))
                    raise error

                boto_client.return_value.run_task.side_effect = lose_response
                with self.assertLogs("accounts.views.character_image_views", level="WARNING") as logs:
                    response = self.post_image()
                job = BackgroundRemovalJob.objects.get()
                self.assertEqual(response.status_code, 202)
                self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.PENDING)
                self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
                self.assertEqual(job.updated_at, before[0][0])
                self.assertEqual(job.source_image.name, before[0][1])
                self.assertTrue(job.source_image.storage.exists(job.source_image.name))
                self.assertEqual(job.error_message, "")
                self.assertEqual(job.task_arn, "")
                self.assertNotIn("synthetic-private-backend-detail", "\n".join(logs.output))
                self.assertIn(str(job.pk), "\n".join(logs.output))
                polled = self.client.get(response.data["status_url"])
                self.assertEqual(polled.status_code, 202)
                self.assertIn("no-store", polled["Cache-Control"])

    @patch("accounts.background_removal_tasks.remove_background")
    @patch("boto3.client")
    def test_worker_can_finish_after_lost_launch_response_and_duplicate_post_is_refused(self, boto_client, inference):
        boto_client.return_value.run_task.side_effect = ReadTimeoutError(endpoint_url="synthetic-endpoint")
        response = self.post_image()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.post_image().status_code, 409)
        self.assertEqual(BackgroundRemovalJob.objects.count(), 1)
        self.assertEqual(boto_client.return_value.run_task.call_count, 1)
        inference.return_value = self.image_bytes()
        job = process_background_removal_job(response.data["job_id"])
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertFalse(job.source_image)
        result = self.client.get(response.data["status_url"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, self.image_bytes())
        self.assertIn("no-store", result["Cache-Control"])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(response.data["status_url"]).status_code, 401)

    @patch("boto3.client")
    def test_unconfirmed_launch_expires_without_extending_timeout(self, boto_client):
        boto_client.return_value.run_task.side_effect = ReadTimeoutError(endpoint_url="synthetic-endpoint")
        response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get()
        source_name = job.source_image.name
        expired_at = timezone.now() - timedelta(minutes=2)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=expired_at)
        summary = cleanup_background_removal_jobs()
        self.assertEqual(summary["timed_out_jobs"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image.storage.exists(source_name))
        with patch("accounts.background_removal_tasks.remove_background") as inference:
            process_background_removal_job(job.pk)
        inference.assert_not_called()

    @patch("boto3.client")
    def test_definite_configuration_permission_and_validation_errors_still_fail_and_clean_source(self, boto_client):
        for error in [
            NoCredentialsError(),
            ParamValidationError(report="synthetic"),
            client_error("AccessDenied", 403),
        ]:
            with self.subTest(error=type(error).__name__):
                source_names = []

                def refused(**kwargs):
                    source_names.append(BackgroundRemovalJob.objects.get().source_image.name)
                    raise error

                boto_client.return_value.run_task.side_effect = refused
                response = self.post_image()
                self.assertEqual(response.status_code, 503)
                job = BackgroundRemovalJob.objects.get()
                self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
                self.assertFalse(job.source_image.storage.exists(source_names[0]))
                job.delete()

    @patch("boto3.client")
    def test_no_tasks_with_explicit_failure_is_definite(self, boto_client):
        boto_client.return_value.run_task.return_value = {"tasks": [], "failures": [{"reason": "RESOURCE:MEMORY"}]}
        response = self.post_image()
        self.assertEqual(response.status_code, 503)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)

    @patch("boto3.client")
    def test_incomplete_success_response_must_not_destroy_pending_source(self, boto_client):
        for ecs_response in [{}, {"tasks": [{"lastStatus": "PENDING"}]}, {"tasks": [{"taskArn": ""}]}]:
            with self.subTest(response=ecs_response):
                self.clear_jobs()
                boto_client.return_value.run_task.return_value = ecs_response
                response = self.post_image()
                self.assertEqual(response.status_code, 202)
                job = BackgroundRemovalJob.objects.get()
                self.assertTrue(job.source_image.storage.exists(job.source_image.name))
                self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)

    @patch("boto3.client")
    def test_accepted_task_is_not_discarded_when_failures_also_present(self, boto_client):
        boto_client.return_value.run_task.return_value = {
            "tasks": [{"taskArn": "synthetic-task-arn"}],
            "failures": [{"reason": "synthetic-other-task-failure"}],
        }
        response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.task_arn, "synthetic-task-arn")
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    @patch("boto3.client")
    def test_database_metadata_failure_after_acceptance_keeps_pending_source(self, boto_client):
        boto_client.return_value.run_task.return_value = {"tasks": [{"taskArn": "synthetic-task-arn"}]}
        save = BackgroundRemovalJob.save

        def fail_metadata(instance, *args, **kwargs):
            if kwargs.get("update_fields") == ["task_arn"]:
                raise OperationalError("synthetic-private-backend-detail")
            return save(instance, *args, **kwargs)

        with patch.object(BackgroundRemovalJob, "save", fail_metadata):
            response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    @patch("boto3.client")
    def test_same_job_uses_stable_token_while_distinct_jobs_use_distinct_tokens(self, boto_client):
        boto_client.return_value.run_task.return_value = {"tasks": [{"taskArn": "synthetic-task-arn"}]}
        job = self.create_job()
        start_background_removal_task(job)
        first = boto_client.return_value.run_task.call_args.kwargs
        start_background_removal_task(job)
        self.assertEqual(first, boto_client.return_value.run_task.call_args.kwargs)
        self.assertEqual(first["clientToken"], str(job.pk))
        other = self.create_job()
        start_background_removal_task(other)
        self.assertNotEqual(first["clientToken"], boto_client.return_value.run_task.call_args.kwargs["clientToken"])

    @patch("boto3.client")
    def test_uncertain_launch_uses_latest_running_failed_or_deleted_state(self, boto_client):
        for current_status, expected_http in [("running", 202), ("failed", 503), ("deleted", 404)]:
            with self.subTest(status=current_status):
                self.clear_jobs()
                snapshot = []

                def lose_response(**kwargs):
                    current = BackgroundRemovalJob.objects.get()
                    if current_status == "deleted":
                        current.delete()
                    else:
                        current.status = current_status
                        current.error_message = "隔離検証用の確定した失敗" if current_status == "failed" else ""
                        current.save(update_fields=["status", "error_message", "updated_at"])
                        snapshot.append((current.updated_at, current.error_message, current.source_image.name))
                    raise ReadTimeoutError(endpoint_url="synthetic-endpoint")

                boto_client.return_value.run_task.side_effect = lose_response
                response = self.post_image()
                self.assertEqual(response.status_code, expected_http)
                if current_status == "deleted":
                    self.assertFalse(BackgroundRemovalJob.objects.exists())
                else:
                    current = BackgroundRemovalJob.objects.get()
                    self.assertEqual(current.status, current_status)
                    self.assertEqual(
                        (current.updated_at, current.error_message, current.source_image.name), snapshot[0]
                    )
                    self.assertTrue(current.source_image.storage.exists(current.source_image.name))

    def sdk_client(self):
        ecs = boto3.client(
            "ecs",
            region_name="ap-northeast-1",
            aws_access_key_id="synthetic-unused-access-key",
            aws_secret_access_key="synthetic-unused-secret-key",
            config=Config(retries={"mode": "standard", "total_max_attempts": 2}),
        )
        self.addCleanup(ecs.close)
        return ecs

    @staticmethod
    def sdk_response(status_code, body):
        raw = Mock()
        raw.stream.return_value = [json.dumps(body).encode("utf-8")]
        return AWSResponse(
            "https://synthetic.invalid/", status_code, {"content-type": "application/x-amz-json-1.1"}, raw
        )

    def test_actual_sdk_retry_reuses_job_token_and_recovers_accepted_task(self):
        ecs = self.sdk_client()
        success = self.sdk_response(200, {"tasks": [{"taskArn": "synthetic-task-arn"}]})
        with (
            patch("boto3.client", return_value=ecs),
            patch.object(
                ecs._endpoint, "_send", side_effect=[ReadTimeoutError(endpoint_url="synthetic"), success]
            ) as send,
            patch("botocore.endpoint.time.sleep"),
        ):
            response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.task_arn, "synthetic-task-arn")
        self.assertEqual(send.call_count, 2)
        for call in send.call_args_list:
            self.assertEqual(json.loads(call.args[0].body)["clientToken"], str(job.pk))

    def test_actual_sdk_exhausted_retries_keep_source_without_application_relaunch(self):
        ecs = self.sdk_client()
        with (
            patch("boto3.client", return_value=ecs),
            patch.object(ecs._endpoint, "_send", side_effect=ReadTimeoutError(endpoint_url="synthetic")) as send,
            patch("botocore.endpoint.time.sleep"),
        ):
            response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        self.assertEqual(send.call_count, 2)
        for call in send.call_args_list:
            self.assertEqual(json.loads(call.args[0].body)["clientToken"], str(job.pk))

    def test_actual_sdk_definite_client_error_is_not_retried_and_cleans_source(self):
        ecs = self.sdk_client()
        refused = self.sdk_response(400, {"__type": "InvalidParameterException", "message": "synthetic-private-detail"})
        with (
            patch("boto3.client", return_value=ecs),
            patch.object(ecs._endpoint, "_send", return_value=refused) as send,
        ):
            response = self.post_image()
        self.assertEqual(response.status_code, 503)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)
        send.assert_called_once()


@skipUnless(connection.vendor == "postgresql", "Actual PostgreSQL row-lock inspection required")
@override_settings(
    BACKGROUND_REMOVAL_TASK_DEFINITION="synthetic-worker:1",
    BACKGROUND_REMOVAL_SUBNETS=["synthetic-subnet"],
    BACKGROUND_REMOVAL_SECURITY_GROUPS=["synthetic-group"],
)
class BackgroundUncertainDispatchLockTests(dispatch_tests.DispatchFixtureMixin, TransactionTestCase):
    assert_blocked_by_current_transaction = (
        dispatch_tests.BackgroundDispatchLockTests.assert_blocked_by_current_transaction
    )

    def post_in_database_thread(self):
        close_old_connections()
        try:
            return self.post_image()
        finally:
            connections.close_all()

    @patch("boto3.client")
    def test_uncertain_response_waits_for_latest_terminal_state(self, boto_client):
        entered, fail = Event(), Event()
        claimed = []

        def lose_response(**kwargs):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                claimed.append((BackgroundRemovalJob.objects.get().pk, cursor.fetchone()[0]))
            entered.set()
            self.assertTrue(fail.wait(10))
            raise ReadTimeoutError(endpoint_url="synthetic-endpoint")

        boto_client.return_value.run_task.side_effect = lose_response
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.post_in_database_thread)
            try:
                self.assertTrue(entered.wait(5))
                job_id, web_pid = claimed[0]
                with transaction.atomic():
                    current = BackgroundRemovalJob.objects.select_for_update().get(pk=job_id)
                    current.status = BackgroundRemovalJob.Status.COMPLETED
                    current.result_image.save("synthetic-output.png", ContentFile(self.image_bytes()), save=False)
                    current.save(update_fields=["status", "result_image", "updated_at"])
                    completed_at = current.updated_at
                    fail.set()
                    self.assert_blocked_by_current_transaction(web_pid)
                response = future.result(timeout=5)
            finally:
                fail.set()
        current.refresh_from_db()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(current.updated_at, completed_at)
        self.assertTrue(current.result_image.storage.exists(current.result_image.name))
