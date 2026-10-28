import io
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from accounts.background_removal_tasks import fail_stale_background_removal_job, process_background_removal_job
from accounts.models import BackgroundRemovalJob, CustomUser


class BackgroundJobFixtureMixin:
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.media_root = Path(media.name)
        settings = override_settings(MEDIA_ROOT=media.name, BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS=60)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = CustomUser.objects.create_user(username="synthetic-background-finalization")

    @staticmethod
    def image_bytes(image_format="PNG"):
        stream = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(stream, image_format)
        return stream.getvalue()

    def create_job(self, **kwargs):
        return BackgroundRemovalJob.objects.create(
            user=self.user, source_image=ContentFile(self.image_bytes(), name="synthetic-source.png"), **kwargs
        )

    def timeout(self, job_id):
        BackgroundRemovalJob.objects.filter(pk=job_id).update(updated_at=timezone.now() - timedelta(minutes=2))
        job = BackgroundRemovalJob.objects.get(pk=job_id)
        self.assertTrue(fail_stale_background_removal_job(job))
        return job


class BackgroundJobFinalizationTests(BackgroundJobFixtureMixin, TestCase):
    @patch("accounts.background_removal_tasks.remove_background")
    def test_late_success_cannot_replace_timeout_or_publish_result(self, inference):
        job = self.create_job()
        source_name = job.source_image.name

        def finish_after_timeout(source):
            self.timeout(job.pk)
            return self.image_bytes()

        inference.side_effect = finish_after_timeout
        processed = process_background_removal_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(job.error_message, "Background removal timed out.")
        self.assertFalse(job.result_image)
        self.assertFalse(job.source_image)
        self.assertFalse(job.source_image.storage.exists(source_name))
        self.assertFalse((self.media_root / "background_removal/output").exists())

    @patch("accounts.background_removal_tasks.remove_background")
    def test_late_failure_preserves_existing_timeout(self, inference):
        job = self.create_job()

        def fail_after_timeout(source):
            self.timeout(job.pk)
            raise RuntimeError("synthetic inference failure after timeout")

        inference.side_effect = fail_after_timeout
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(processed.error_message, "Background removal timed out.")
        self.assertFalse(processed.result_image)

    def test_stale_snapshot_does_not_timeout_a_completed_job(self):
        job = self.create_job(status=BackgroundRemovalJob.Status.RUNNING)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        job.refresh_from_db()
        current = BackgroundRemovalJob.objects.get(pk=job.pk)
        current.status = BackgroundRemovalJob.Status.COMPLETED
        current.result_image.save("synthetic-result.png", ContentFile(self.image_bytes()), save=False)
        current.save(update_fields=["status", "result_image", "updated_at"])

        self.assertFalse(fail_stale_background_removal_job(job))
        current.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertEqual(current.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertTrue(current.result_image.storage.exists(current.result_image.name))
        self.assertTrue(current.source_image)

    def test_stale_pending_snapshot_does_not_timeout_a_new_worker_claim(self):
        job = self.create_job()
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        job.refresh_from_db()
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(
            status=BackgroundRemovalJob.Status.RUNNING, updated_at=timezone.now()
        )
        self.assertFalse(fail_stale_background_removal_job(job))
        self.assertEqual(job.status, BackgroundRemovalJob.Status.RUNNING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    def test_timeout_of_deleted_snapshot_does_not_recreate_job(self):
        job = self.create_job()
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        job.refresh_from_db()
        job_id = job.pk
        BackgroundRemovalJob.objects.filter(pk=job_id).delete()
        self.assertFalse(fail_stale_background_removal_job(job))
        self.assertFalse(BackgroundRemovalJob.objects.filter(pk=job_id).exists())

    @patch("accounts.background_removal_tasks.remove_background")
    def test_deleted_job_cannot_leave_a_late_result(self, inference):
        job = self.create_job()
        source_name = job.source_image.name

        def finish_after_deletion(source):
            BackgroundRemovalJob.objects.filter(pk=job.pk).delete()
            return self.image_bytes()

        inference.side_effect = finish_after_deletion
        with self.assertRaises(BackgroundRemovalJob.DoesNotExist):
            process_background_removal_job(job.pk)
        self.assertFalse(BackgroundRemovalJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(job.source_image.storage.exists(source_name))
        self.assertFalse((self.media_root / "background_removal/output").exists())

    @patch("accounts.background_removal_tasks.remove_background")
    def test_source_file_is_closed_before_inference(self, inference):
        job = self.create_job()
        source_name = job.source_image.name

        def infer_after_removal(source):
            job.source_image.storage.delete(source_name)
            return self.image_bytes()

        inference.side_effect = infer_after_removal
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.COMPLETED)

    @patch("accounts.background_removal_tasks.remove_background")
    def test_non_png_inference_result_is_failed_without_publication(self, inference):
        job = self.create_job()
        inference.return_value = self.image_bytes("JPEG")
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(processed.result_image)
        self.assertFalse(processed.source_image)

    @patch("accounts.background_removal_tasks.remove_background")
    def test_storage_failure_is_failed_without_leaving_a_result_reference(self, inference):
        job = self.create_job()
        inference.return_value = self.image_bytes()
        with patch.object(job.result_image.storage, "save", side_effect=OSError("synthetic result storage failure")):
            processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(processed.result_image)
        self.assertFalse(processed.source_image)

    @patch("accounts.background_removal_tasks.remove_background")
    def test_unsafe_filename_uses_existing_character_fallback(self, inference):
        job = self.create_job(original_filename="../***.jpg")
        inference.return_value = self.image_bytes()
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertTrue(processed.result_image.name.endswith("character-transparent.png"))

    def test_timeout_without_source_keeps_existing_failure_behavior(self):
        job = BackgroundRemovalJob.objects.create(user=self.user, status=BackgroundRemovalJob.Status.RUNNING)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        self.assertTrue(fail_stale_background_removal_job(job))
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)

    def test_missing_source_is_failed_without_result(self):
        job = BackgroundRemovalJob.objects.create(user=self.user)
        processed = process_background_removal_job(job.pk)
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(processed.source_image)
        self.assertFalse(processed.result_image)


@skipUnless(connection.vendor == "postgresql", "Actual PostgreSQL row-lock inspection required")
class BackgroundJobLockTests(BackgroundJobFixtureMixin, TransactionTestCase):
    def test_lock_probe_fails_when_wait_is_not_observed(self):
        with (
            patch("tests.integration.test_background_job_finalization_integrity.time.monotonic", side_effect=[0, 6]),
            self.assertRaisesMessage(AssertionError, "Worker did not wait for the held job row lock"),
        ):
            self.assert_blocked_by_current_transaction(0)

    def assert_blocked_by_current_transaction(self, worker_pid):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))", [worker_pid])
                if cursor.fetchone()[0]:
                    return
            time.sleep(0.01)
        self.fail("Worker did not wait for the held job row lock")

    @staticmethod
    def database_worker(callback, worker_pid, connected):
        close_old_connections()
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                worker_pid.append(cursor.fetchone()[0])
            connected.set()
            return callback()
        finally:
            connections.close_all()

    def test_timeout_waits_for_completion_before_deleting_source(self):
        job = self.create_job(status=BackgroundRemovalJob.Status.RUNNING)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        job.refresh_from_db()
        source_name = job.source_image.name
        worker_pid, connected = [], Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                current = BackgroundRemovalJob.objects.select_for_update().get(pk=job.pk)
                current.status = BackgroundRemovalJob.Status.COMPLETED
                current.save(update_fields=["status", "updated_at"])
                future = executor.submit(
                    self.database_worker, lambda: fail_stale_background_removal_job(job), worker_pid, connected
                )
                self.assertTrue(connected.wait(5))
                self.assert_blocked_by_current_transaction(worker_pid[0])
                self.assertTrue(job.source_image.storage.exists(source_name))
            self.assertFalse(future.result(timeout=5))
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)

    @patch("accounts.background_removal_tasks.remove_background")
    def test_worker_waits_for_timeout_before_publishing_result(self, inference):
        job = self.create_job()
        entered, finish = Event(), Event()
        worker_pid, connected = [], Event()

        def infer(source):
            entered.set()
            self.assertTrue(finish.wait(10))
            return self.image_bytes()

        inference.side_effect = infer
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self.database_worker, lambda: process_background_removal_job(job.pk), worker_pid, connected
            )
            try:
                self.assertTrue(entered.wait(5))
                with transaction.atomic():
                    current = BackgroundRemovalJob.objects.select_for_update().get(pk=job.pk)
                    current.status = BackgroundRemovalJob.Status.FAILED
                    current.error_message = "Background removal timed out."
                    current.save(update_fields=["status", "error_message", "updated_at"])
                    finish.set()
                    self.assert_blocked_by_current_transaction(worker_pid[0])
                    self.assertFalse((self.media_root / "background_removal/output").exists())
                processed = future.result(timeout=5)
            finally:
                finish.set()
        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(processed.error_message, "Background removal timed out.")
        self.assertFalse(processed.result_image)
