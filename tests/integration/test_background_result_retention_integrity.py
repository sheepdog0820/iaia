import io
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from botocore.exceptions import ClientError, EndpointConnectionError
from django.core.files.base import ContentFile, File
from django.db import close_old_connections, connection, connections, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.background_removal_tasks import cleanup_background_removal_jobs
from accounts.models import BackgroundRemovalJob
from tests.integration import test_background_job_finalization_integrity as finalization_tests


class ResultFixtureMixin(finalization_tests.BackgroundJobFixtureMixin):
    def setUp(self):
        super().setUp()
        self.now = timezone.now()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def completed_job(self, age=timedelta(hours=25)):
        job = self.create_job(status=BackgroundRemovalJob.Status.COMPLETED)
        job.result_image.save("synthetic-result.png", ContentFile(self.image_bytes()))
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=self.now - age)
        job.refresh_from_db()
        return job

    def get_result(self, job_id):
        return self.client.get(reverse("character-image-background-removal-status", args=[job_id]))

    def assert_unavailable(self, response):
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data,
            {"error": "背景透過した画像を取得できません。再度取得するか、もう一度背景透過を行ってください。"},
        )
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("Cookie", response["Vary"])
        self.assertIn("Authorization", response["Vary"])


class BackgroundResultReadTests(ResultFixtureMixin, TestCase):
    def test_missing_result_file_returns_private_unavailable_response(self):
        job = self.completed_job()
        job.result_image.storage.delete(job.result_image.name)
        response = self.get_result(job.pk)
        self.assert_unavailable(response)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertTrue(job.result_image)

    def test_missing_result_reference_keeps_unavailable_response(self):
        job = self.create_job(status=BackgroundRemovalJob.Status.COMPLETED)
        self.assert_unavailable(self.get_result(job.pk))

    def test_storage_access_error_returns_generic_response_without_detail(self):
        job = self.completed_job()
        failure = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "synthetic private bucket detail"}}, "GetObject"
        )
        with (
            patch.object(job.result_image.storage, "open", side_effect=failure),
            self.assertLogs("accounts.views.character_image_views", level="WARNING") as logs,
        ):
            self.assert_unavailable(self.get_result(job.pk))
        self.assertIn("ClientError", logs.output[0])
        self.assertNotIn("synthetic private bucket detail", "\n".join(logs.output))
        job.refresh_from_db()
        self.assertEqual(job.updated_at, self.now - timedelta(hours=25))
        self.assertTrue(job.result_image.storage.exists(job.result_image.name))

    def test_storage_connection_error_returns_generic_response(self):
        job = self.completed_job()
        failure = EndpointConnectionError(endpoint_url="https://synthetic-private-storage.example.test")
        with patch.object(job.result_image.storage, "open", side_effect=failure):
            self.assert_unavailable(self.get_result(job.pk))

    def test_storage_read_error_returns_generic_response(self):
        class BrokenRead(io.BytesIO):
            def read(self, *args, **kwargs):
                raise OSError("synthetic storage read failure")

        job = self.completed_job()
        with patch.object(job.result_image.storage, "open", return_value=BrokenRead(self.image_bytes())):
            self.assert_unavailable(self.get_result(job.pk))


class BackgroundResultCleanupTests(ResultFixtureMixin, TestCase):
    def assert_recent_snapshot_is_not_deleted(self, age):
        job = self.completed_job(age)
        source_name, result_name = job.source_image.name, job.result_image.name
        original_iterator = QuerySet.iterator

        def refresh_after_snapshot(queryset, *args, **kwargs):
            for candidate in original_iterator(queryset, *args, **kwargs):
                BackgroundRemovalJob.objects.filter(pk=candidate.pk).update(updated_at=self.now)
                yield candidate

        with patch.object(QuerySet, "iterator", refresh_after_snapshot):
            summary = cleanup_background_removal_jobs(now=self.now)
        job.refresh_from_db()
        self.assertEqual(summary["deleted_jobs"], 0)
        self.assertEqual(summary["deleted_result_images"], 0)
        self.assertEqual(job.updated_at, self.now)
        self.assertTrue(job.source_image.storage.exists(source_name))
        self.assertTrue(job.result_image.storage.exists(result_name))

    def test_stale_terminal_snapshot_cannot_delete_recent_job(self):
        self.assert_recent_snapshot_is_not_deleted(timedelta(days=8))

    def test_stale_result_snapshot_cannot_delete_recent_result(self):
        self.assert_recent_snapshot_is_not_deleted(timedelta(hours=25))

    def test_stale_active_selection_cannot_timeout_a_recent_job(self):
        job = self.create_job(status=BackgroundRemovalJob.Status.RUNNING)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=self.now - timedelta(minutes=2))
        original_iterator = QuerySet.iterator

        def refresh_after_snapshot(queryset, *args, **kwargs):
            for candidate in original_iterator(queryset, *args, **kwargs):
                BackgroundRemovalJob.objects.filter(pk=candidate.pk).update(updated_at=self.now)
                yield candidate

        with patch.object(QuerySet, "iterator", refresh_after_snapshot):
            summary = cleanup_background_removal_jobs(now=self.now)
        job.refresh_from_db()
        self.assertEqual(summary["timed_out_jobs"], 0)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.RUNNING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    def test_changed_or_deleted_snapshot_is_rechecked_before_storage_deletion(self):
        original_iterator = QuerySet.iterator
        for age in (timedelta(days=8), timedelta(hours=25)):
            for mutation in ("status", "delete"):
                with self.subTest(age=age, mutation=mutation):
                    job = self.completed_job(age)
                    source_name, result_name = job.source_image.name, job.result_image.name

                    def mutate_after_snapshot(queryset, *args, **kwargs):
                        for candidate in original_iterator(queryset, *args, **kwargs):
                            current = BackgroundRemovalJob.objects.filter(pk=candidate.pk)
                            if mutation == "delete":
                                current.delete()
                            else:
                                current.update(status=BackgroundRemovalJob.Status.PENDING)
                            yield candidate

                    with patch.object(QuerySet, "iterator", mutate_after_snapshot):
                        summary = cleanup_background_removal_jobs(now=self.now)
                    self.assertEqual(summary["deleted_jobs"], 0)
                    self.assertEqual(summary["deleted_result_images"], 0)
                    self.assertTrue(job.source_image.storage.exists(source_name))
                    self.assertTrue(job.result_image.storage.exists(result_name))
                    # Restore the synthetic row so a later subtest does not time it out.
                    BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=self.now)

    def test_terminal_partial_storage_failure_preserves_uncleared_reference(self):
        job = self.completed_job(timedelta(days=8))
        source_name, result_name = job.source_image.name, job.result_image.name
        storage = job.result_image.storage
        original_delete = storage.delete

        def fail_result_only(name):
            if name == result_name:
                raise OSError("synthetic result deletion failure")
            return original_delete(name)

        with patch.object(storage, "delete", fail_result_only):
            summary = cleanup_background_removal_jobs(now=self.now)
        job.refresh_from_db()
        self.assertFalse(job.source_image)
        self.assertFalse(storage.exists(source_name))
        self.assertEqual(job.result_image.name, result_name)
        self.assertTrue(storage.exists(result_name))
        self.assertEqual(job.updated_at, self.now - timedelta(days=8))
        self.assertEqual(summary["failed_jobs"], 1)
        self.assertEqual(summary["deleted_jobs"], 0)

    def test_recent_result_storage_failure_keeps_reference_and_age(self):
        job = self.completed_job()
        result_name = job.result_image.name
        with patch.object(job.result_image.storage, "delete", side_effect=OSError("synthetic deletion failure")):
            summary = cleanup_background_removal_jobs(now=self.now)
        job.refresh_from_db()
        self.assertEqual(job.result_image.name, result_name)
        self.assertEqual(job.updated_at, self.now - timedelta(hours=25))
        self.assertTrue(job.result_image.storage.exists(result_name))
        self.assertEqual(summary["failed_jobs"], 1)
        self.assertEqual(summary["deleted_result_images"], 0)

    def test_terminal_job_without_files_is_deleted(self):
        job = BackgroundRemovalJob.objects.create(user=self.user, status=BackgroundRemovalJob.Status.FAILED)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=self.now - timedelta(days=8))
        summary = cleanup_background_removal_jobs(now=self.now)
        self.assertEqual(summary["deleted_jobs"], 1)
        self.assertFalse(BackgroundRemovalJob.objects.filter(pk=job.pk).exists())

    def test_retention_cutoffs_remain_inclusive_and_newer_result_is_kept(self):
        terminal = self.completed_job(timedelta(days=7))
        result = self.completed_job(timedelta(hours=24))
        recent = self.completed_job(timedelta(hours=24) - timedelta(microseconds=1))
        summary = cleanup_background_removal_jobs(now=self.now)
        self.assertEqual(summary["deleted_jobs"], 1)
        self.assertEqual(summary["deleted_result_images"], 1)
        self.assertFalse(BackgroundRemovalJob.objects.filter(pk=terminal.pk).exists())
        result.refresh_from_db()
        recent.refresh_from_db()
        self.assertFalse(result.result_image)
        self.assertTrue(recent.result_image.storage.exists(recent.result_image.name))


@skipUnless(connection.vendor == "postgresql", "Actual PostgreSQL row-lock inspection required")
class BackgroundResultLockTests(ResultFixtureMixin, TransactionTestCase):
    @staticmethod
    def database_worker(callback, pid, connected):
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pid.append(cursor.fetchone()[0])
            connected.set()
            return callback()
        finally:
            connections.close_all()

    def assert_blocked_by(self, waiting_pid, holding_pid):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s = ANY(pg_blocking_pids(%s))", [holding_pid, waiting_pid])
                if cursor.fetchone()[0]:
                    return
            time.sleep(0.01)
        self.fail("Cleanup did not wait for the result row lock")

    def test_lock_observation_fails_when_no_wait_was_seen(self):
        with (
            patch("tests.integration.test_background_result_retention_integrity.time.monotonic", side_effect=[0, 6]),
            self.assertRaisesMessage(AssertionError, "Cleanup did not wait for the result row lock"),
        ):
            self.assert_blocked_by(0, 0)

    def assert_cleanup_waits_for_result_read(self, age, deletion_field):
        job = self.completed_job(age)
        source_name, result_name = job.source_image.name, job.result_image.name
        storage = job.result_image.storage
        original_open = storage.open
        reading, release = Event(), Event()
        getter_pid, cleaner_pid = [], []
        getter_connected, cleaner_connected = Event(), Event()

        case = self

        class BlockingReadFile(File):
            def read(self, *args, **kwargs):
                reading.set()
                case.assertTrue(release.wait(10))
                return self.file.read(*args, **kwargs)

        def block_open(name, mode="rb"):
            return BlockingReadFile(original_open(name, mode))

        with patch.object(storage, "open", block_open), ThreadPoolExecutor(max_workers=2) as executor:
            getter = executor.submit(
                self.database_worker, lambda: self.get_result(job.pk), getter_pid, getter_connected
            )
            try:
                self.assertTrue(reading.wait(5))
                cleaner = executor.submit(
                    self.database_worker,
                    lambda: cleanup_background_removal_jobs(now=self.now),
                    cleaner_pid,
                    cleaner_connected,
                )
                self.assertTrue(cleaner_connected.wait(5))
                self.assert_blocked_by(cleaner_pid[0], getter_pid[0])
                self.assertTrue(storage.exists(source_name))
                self.assertTrue(storage.exists(result_name))
            finally:
                release.set()
            response = getter.result(timeout=5)
            summary = cleaner.result(timeout=5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.image_bytes())
        self.assertEqual(summary[deletion_field], 1)
        self.assertFalse(storage.exists(result_name))

    def test_result_cleanup_waits_until_api_has_read_complete_image(self):
        self.assert_cleanup_waits_for_result_read(timedelta(hours=25), "deleted_result_images")

    def test_terminal_cleanup_waits_until_api_has_read_complete_image(self):
        self.assert_cleanup_waits_for_result_read(timedelta(days=8), "deleted_jobs")

    def assert_cleanup_rechecks_current_age_after_wait(self, age):
        job = self.completed_job(age)
        result_name = job.result_image.name
        cleaner_pid, connected = [], Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                current = BackgroundRemovalJob.objects.select_for_update().get(pk=job.pk)
                current.updated_at = self.now
                current.save(update_fields=["updated_at"])
                future = executor.submit(
                    self.database_worker, lambda: cleanup_background_removal_jobs(now=self.now), cleaner_pid, connected
                )
                self.assertTrue(connected.wait(5))
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    holding_pid = cursor.fetchone()[0]
                self.assert_blocked_by(cleaner_pid[0], holding_pid)
                self.assertTrue(job.result_image.storage.exists(result_name))
            summary = future.result(timeout=5)
        job.refresh_from_db()
        self.assertEqual(summary["deleted_jobs"], 0)
        self.assertEqual(summary["deleted_result_images"], 0)
        self.assertTrue(job.result_image.storage.exists(result_name))

    def test_terminal_cleanup_rechecks_age_after_actual_lock_wait(self):
        self.assert_cleanup_rechecks_current_age_after_wait(timedelta(days=8))

    def test_result_cleanup_rechecks_age_after_actual_lock_wait(self):
        self.assert_cleanup_rechecks_current_age_after_wait(timedelta(hours=25))

    def assert_concurrent_cleaners_delete_once(self, age, deletion_field):
        job = self.completed_job(age)
        result_name = job.result_image.name
        storage, deleting, release = job.result_image.storage, Event(), Event()
        original_delete = storage.delete
        first_pid, second_pid = [], []
        first_connected, second_connected = Event(), Event()

        def block_delete(name):
            deleting.set()
            self.assertTrue(release.wait(10))
            return original_delete(name)

        with (
            patch.object(storage, "delete", side_effect=block_delete) as deletion,
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            first = executor.submit(
                self.database_worker,
                lambda: cleanup_background_removal_jobs(now=self.now),
                first_pid,
                first_connected,
            )
            try:
                self.assertTrue(deleting.wait(5))
                second = executor.submit(
                    self.database_worker,
                    lambda: cleanup_background_removal_jobs(now=self.now),
                    second_pid,
                    second_connected,
                )
                self.assertTrue(second_connected.wait(5))
                self.assert_blocked_by(second_pid[0], first_pid[0])
                self.assertTrue(storage.exists(result_name))
            finally:
                release.set()
            summaries = [first.result(timeout=5), second.result(timeout=5)]
        self.assertEqual(sum(summary[deletion_field] for summary in summaries), 1)
        self.assertEqual(sum(summary["failed_jobs"] for summary in summaries), 0)
        self.assertFalse(storage.exists(result_name))
        self.assertEqual(sum(call.args == (result_name,) for call in deletion.call_args_list), 1)

    def test_concurrent_result_cleaners_delete_once(self):
        self.assert_concurrent_cleaners_delete_once(timedelta(hours=25), "deleted_result_images")

    def test_concurrent_terminal_cleaners_delete_once(self):
        self.assert_concurrent_cleaners_delete_once(timedelta(days=8), "deleted_jobs")
