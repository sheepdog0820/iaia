from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.background_removal_tasks import process_background_removal_job, start_background_removal_task
from accounts.models import BackgroundRemovalJob
from tests.integration import test_background_job_finalization_integrity as finalization_tests


class DispatchFixtureMixin(finalization_tests.BackgroundJobFixtureMixin):
    def setUp(self):
        super().setUp()
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def post_image(self):
        image = SimpleUploadedFile("synthetic-source.png", self.image_bytes(), content_type="image/png")
        return self.client.post(reverse("character-image-remove-background"), {"image": image}, format="multipart")


class BackgroundDispatchResponseTests(DispatchFixtureMixin, TestCase):
    @patch("accounts.views.character_image_views.start_background_removal_task")
    def test_pending_launch_failure_without_source_remains_a_generic_failure(self, dispatch):
        def failure_after_cleanup(job):
            current = BackgroundRemovalJob.objects.get(pk=job.pk)
            current.source_image.delete()
            raise RuntimeError("synthetic launch failure")

        dispatch.side_effect = failure_after_cleanup
        response = self.post_image()
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "Background removal could not be started.")
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)

    def test_missing_upload_keeps_validation_error(self):
        response = self.client.post(reverse("character-image-remove-background"), {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BackgroundRemovalJob.objects.exists())

    def test_oversized_upload_keeps_validation_error(self):
        image = SimpleUploadedFile("synthetic-large.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")
        response = self.client.post(reverse("character-image-remove-background"), {"image": image}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BackgroundRemovalJob.objects.exists())

    @patch("accounts.views.character_image_views.start_background_removal_task")
    def test_lost_dispatch_response_preserves_running_job_and_source(self, dispatch):
        def started(job):
            BackgroundRemovalJob.objects.filter(pk=job.pk).update(status=BackgroundRemovalJob.Status.RUNNING)
            raise RuntimeError("synthetic lost ECS response")

        dispatch.side_effect = started
        response = self.post_image()
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.RUNNING)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.RUNNING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        self.assertEqual(job.error_message, "")

    @patch("accounts.views.character_image_views.start_background_removal_task")
    @patch("accounts.background_removal_tasks.remove_background")
    def test_lost_dispatch_response_preserves_completed_worker_result(self, inference, dispatch):
        inference.return_value = self.image_bytes()

        def completed(job):
            process_background_removal_job(job.pk)
            raise RuntimeError("synthetic lost ECS response")

        dispatch.side_effect = completed
        response = self.post_image()
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(job.error_message, "")
        self.assertFalse(job.source_image)
        result = self.client.get(response.data["status_url"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, self.image_bytes())
        self.assertIn("no-store", result["Cache-Control"])

    @patch("accounts.views.character_image_views.start_background_removal_task")
    def test_lost_dispatch_response_preserves_existing_failure_reason(self, dispatch):
        def failed(job):
            BackgroundRemovalJob.objects.filter(pk=job.pk).update(
                status=BackgroundRemovalJob.Status.FAILED, error_message="Background removal timed out."
            )
            raise RuntimeError("synthetic lost ECS response")

        dispatch.side_effect = failed
        response = self.post_image()
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "Background removal timed out.")
        self.assertEqual(job.error_message, "Background removal timed out.")
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    @patch("accounts.views.character_image_views.start_background_removal_task")
    def test_dispatch_exception_after_deletion_does_not_recreate_or_update_job(self, dispatch):
        def deleted(job):
            BackgroundRemovalJob.objects.filter(pk=job.pk).delete()
            raise RuntimeError("synthetic lost ECS response after deletion")

        dispatch.side_effect = deleted
        response = self.post_image()
        self.assertEqual(response.status_code, 404)
        self.assertFalse(BackgroundRemovalJob.objects.exists())


@override_settings(
    BACKGROUND_REMOVAL_TASK_DEFINITION="synthetic-worker:1",
    BACKGROUND_REMOVAL_SUBNETS=["synthetic-subnet"],
    BACKGROUND_REMOVAL_SECURITY_GROUPS=["synthetic-group"],
)
class BackgroundDispatchMetadataTests(DispatchFixtureMixin, TestCase):
    @override_settings(BACKGROUND_REMOVAL_TASK_DEFINITION="")
    @patch("boto3.client")
    def test_missing_configuration_never_calls_ecs(self, boto_client):
        job = self.create_job()
        with self.assertRaisesMessage(RuntimeError, "Background removal worker is not configured."):
            start_background_removal_task(job)
        boto_client.assert_not_called()

    @patch("boto3.client")
    def test_success_response_uses_current_worker_state(self, boto_client):
        def run_task(**kwargs):
            job_id = kwargs["overrides"]["containerOverrides"][0]["command"][-1]
            BackgroundRemovalJob.objects.filter(pk=job_id).update(status=BackgroundRemovalJob.Status.RUNNING)
            return {"tasks": [{"taskArn": "synthetic-task-arn"}]}

        boto_client.return_value.run_task.side_effect = run_task
        response = self.post_image()
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.RUNNING)
        self.assertEqual(job.task_arn, "synthetic-task-arn")

    @patch("boto3.client")
    def test_task_metadata_does_not_extend_completed_result_retention(self, boto_client):
        job = self.create_job()
        completed_at = timezone.now() - timedelta(hours=25)

        def run_task(**kwargs):
            BackgroundRemovalJob.objects.filter(pk=job.pk).update(
                status=BackgroundRemovalJob.Status.COMPLETED, updated_at=completed_at
            )
            return {"tasks": [{"taskArn": "synthetic-task-arn"}]}

        boto_client.return_value.run_task.side_effect = run_task
        start_background_removal_task(job)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        job.refresh_from_db()
        self.assertEqual(job.updated_at, completed_at)
        self.assertEqual(job.task_arn, "synthetic-task-arn")

    @patch("boto3.client")
    def test_task_metadata_does_not_extend_running_timeout(self, boto_client):
        job = self.create_job()
        started_at = timezone.now() - timedelta(minutes=2)

        def run_task(**kwargs):
            BackgroundRemovalJob.objects.filter(pk=job.pk).update(
                status=BackgroundRemovalJob.Status.RUNNING, updated_at=started_at
            )
            return {"tasks": [{"taskArn": "synthetic-task-arn"}]}

        boto_client.return_value.run_task.side_effect = run_task
        start_background_removal_task(job)
        job.refresh_from_db()
        self.assertEqual(job.updated_at, started_at)

    @patch("boto3.client")
    def test_dispatch_metadata_for_deleted_job_is_not_saved(self, boto_client):
        job = self.create_job()

        def run_task(**kwargs):
            BackgroundRemovalJob.objects.filter(pk=job.pk).delete()
            return {"tasks": [{"taskArn": "synthetic-task-arn"}]}

        boto_client.return_value.run_task.side_effect = run_task
        with self.assertRaises(BackgroundRemovalJob.DoesNotExist):
            start_background_removal_task(job)
        self.assertFalse(BackgroundRemovalJob.objects.exists())


@skipUnless(connection.vendor == "postgresql", "Actual PostgreSQL row-lock inspection required")
class BackgroundDispatchLockTests(DispatchFixtureMixin, TransactionTestCase):
    assert_blocked_by_current_transaction = (
        finalization_tests.BackgroundJobLockTests.assert_blocked_by_current_transaction
    )

    def post_in_database_thread(self):
        close_old_connections()
        try:
            return self.post_image()
        finally:
            connections.close_all()

    @patch("accounts.views.character_image_views.start_background_removal_task")
    def test_dispatch_failure_waits_for_latest_state_before_source_deletion(self, dispatch):
        entered, fail = Event(), Event()
        claimed = []

        def dispatch_then_fail(job):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                claimed.append((job.pk, cursor.fetchone()[0]))
            entered.set()
            self.assertTrue(fail.wait(10))
            raise RuntimeError("synthetic lost ECS response")

        dispatch.side_effect = dispatch_then_fail
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.post_in_database_thread)
            try:
                self.assertTrue(entered.wait(5))
                job_id, worker_pid = claimed[0]
                with transaction.atomic():
                    current = BackgroundRemovalJob.objects.select_for_update().get(pk=job_id)
                    source_name = current.source_image.name
                    current.status = BackgroundRemovalJob.Status.COMPLETED
                    current.result_image.save("synthetic-output.png", ContentFile(self.image_bytes()), save=False)
                    current.save(update_fields=["status", "result_image", "updated_at"])
                    fail.set()
                    self.assert_blocked_by_current_transaction(worker_pid)
                    self.assertTrue(current.source_image.storage.exists(source_name))
                response = future.result(timeout=5)
            finally:
                fail.set()
        current.refresh_from_db()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(current.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertTrue(current.result_image.storage.exists(current.result_image.name))
        self.assertTrue(current.source_image.storage.exists(source_name))
