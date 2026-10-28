from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import BackgroundRemovalJob, CustomUser
from accounts.views.character_image_views import _validate_background_removal_image
from tests.integration import test_background_dispatch_integrity as dispatch_tests
from tests.integration import test_background_job_finalization_integrity as finalization_tests

PREMIUM_ERROR = "背景透過はプレミアムプランの機能です。"
DISPATCH_PATH = "accounts.views.character_image_views.start_background_removal_task"
VALIDATION_PATH = "accounts.views.character_image_views._validate_background_removal_image"


class PremiumGateFixtureMixin(dispatch_tests.DispatchFixtureMixin):
    def assert_denied_without_new_work(self, response, dispatch, *, existing_jobs=0):
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {"detail": PREMIUM_ERROR})
        dispatch.assert_not_called()
        self.assertEqual(BackgroundRemovalJob.objects.count(), existing_jobs)
        if not existing_jobs:
            self.assertFalse(any(path.is_file() for path in self.media_root.rglob("*")))


class BackgroundPremiumGateTests(PremiumGateFixtureMixin, TestCase):
    @patch(DISPATCH_PATH)
    def test_stale_authenticated_premium_flag_cannot_create_job(self, dispatch):
        CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)
        self.assertTrue(self.user.is_premium)
        self.assert_denied_without_new_work(self.post_image(), dispatch)

    @patch(DISPATCH_PATH)
    def test_revocation_during_image_validation_cannot_create_job(self, dispatch):
        def validate_then_revoke(*args, **kwargs):
            result = _validate_background_removal_image(*args, **kwargs)
            self.assertIsNone(result)
            CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)
            return result

        with patch(VALIDATION_PATH, side_effect=validate_then_revoke) as validation:
            response = self.post_image()
        validation.assert_called_once()
        self.assert_denied_without_new_work(response, dispatch)

    @patch(DISPATCH_PATH)
    def test_deletion_during_image_validation_is_denied_without_storage(self, dispatch):
        def validate_then_delete(*args, **kwargs):
            result = _validate_background_removal_image(*args, **kwargs)
            self.assertIsNone(result)
            CustomUser.objects.filter(pk=self.user.pk).delete()
            return result

        with patch(VALIDATION_PATH, side_effect=validate_then_delete):
            response = self.post_image()
        self.assert_denied_without_new_work(response, dispatch)

    @patch(DISPATCH_PATH)
    def test_revoked_user_does_not_clean_existing_stale_job(self, dispatch):
        job = self.create_job(status=BackgroundRemovalJob.Status.RUNNING)
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=2))
        job.refresh_from_db()
        original = (job.status, job.source_image.name, job.updated_at)
        CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)
        with patch("accounts.views.character_image_views.fail_stale_background_removal_job") as cleanup:
            response = self.post_image()
        cleanup.assert_not_called()
        self.assert_denied_without_new_work(response, dispatch, existing_jobs=1)
        job.refresh_from_db()
        self.assertEqual((job.status, job.source_image.name, job.updated_at), original)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        self.assertEqual(len([path for path in self.media_root.rglob("*") if path.is_file()]), 1)

    @patch(DISPATCH_PATH)
    def test_revocation_has_priority_over_daily_quota(self, dispatch):
        self.create_job(status=BackgroundRemovalJob.Status.FAILED)
        CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)
        with self.settings(BACKGROUND_REMOVAL_DAILY_LIMIT=1):
            response = self.post_image()
        self.assert_denied_without_new_work(response, dispatch, existing_jobs=1)

    @patch(DISPATCH_PATH)
    def test_non_premium_is_rejected_in_japanese_before_validation(self, dispatch):
        self.user.is_premium = False
        self.user.save(update_fields=["is_premium"])
        with patch(VALIDATION_PATH) as validation:
            response = self.post_image()
        validation.assert_not_called()
        self.assert_denied_without_new_work(response, dispatch)

    @patch(DISPATCH_PATH)
    def test_stale_staff_and_superuser_flags_do_not_bypass_current_premium_gate(self, dispatch):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)
        self.assert_denied_without_new_work(self.post_image(), dispatch)

    @patch(DISPATCH_PATH)
    def test_restored_premium_access_before_creation_can_create_job(self, dispatch):
        CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)

        def validate_then_restore(*args, **kwargs):
            result = _validate_background_removal_image(*args, **kwargs)
            CustomUser.objects.filter(pk=self.user.pk).update(is_premium=True)
            return result

        with patch(VALIDATION_PATH, side_effect=validate_then_restore):
            response = self.post_image()
        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get(pk=response.data["job_id"])
        dispatch.assert_called_once_with(job)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))

    @patch(DISPATCH_PATH)
    def test_revocation_after_authorized_creation_does_not_cancel_existing_job(self, dispatch):
        def revoke_after_creation(job):
            self.assertTrue(BackgroundRemovalJob.objects.filter(pk=job.pk).exists())
            CustomUser.objects.filter(pk=self.user.pk).update(is_premium=False)

        dispatch.side_effect = revoke_after_creation
        response = self.post_image()
        self.assertEqual(response.status_code, 202)
        dispatch.assert_called_once()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        job = BackgroundRemovalJob.objects.get(pk=response.data["job_id"])
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertTrue(job.source_image.storage.exists(job.source_image.name))
        current = self.client.get(reverse("character-image-background-removal-status", args=[job.pk]))
        self.assertEqual(current.status_code, 202)
        self.assertEqual(current.data["status"], BackgroundRemovalJob.Status.PENDING)
        self.assertIn("no-store", current["Cache-Control"])


@skipUnless(connection.vendor == "postgresql", "Actual PostgreSQL row-lock inspection required")
class BackgroundPremiumGateLockTests(PremiumGateFixtureMixin, TransactionTestCase):
    assert_blocked_by_current_transaction = (
        finalization_tests.BackgroundJobLockTests.assert_blocked_by_current_transaction
    )
    database_worker = staticmethod(finalization_tests.BackgroundJobLockTests.database_worker)

    @patch(DISPATCH_PATH)
    def test_creation_waits_for_committed_premium_revocation(self, dispatch):
        worker_pid, connected = [], Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                current = CustomUser.objects.select_for_update().get(pk=self.user.pk)
                current.is_premium = False
                current.save(update_fields=["is_premium"])
                future = executor.submit(self.database_worker, self.post_image, worker_pid, connected)
                self.assertTrue(connected.wait(5))
                self.assert_blocked_by_current_transaction(worker_pid[0])
                self.assertFalse(BackgroundRemovalJob.objects.exists())
                self.assertFalse(any(path.is_file() for path in self.media_root.rglob("*")))
                dispatch.assert_not_called()
            response = future.result(timeout=5)
        self.assert_denied_without_new_work(response, dispatch)
        self.assertFalse(CustomUser.objects.get(pk=self.user.pk).is_premium)

    @patch(DISPATCH_PATH)
    def test_creation_waits_for_committed_user_deletion(self, dispatch):
        worker_pid, connected = [], Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                current = CustomUser.objects.select_for_update().get(pk=self.user.pk)
                current.delete()
                future = executor.submit(self.database_worker, self.post_image, worker_pid, connected)
                self.assertTrue(connected.wait(5))
                self.assert_blocked_by_current_transaction(worker_pid[0])
                self.assertFalse(BackgroundRemovalJob.objects.exists())
                dispatch.assert_not_called()
            response = future.result(timeout=5)
        self.assert_denied_without_new_work(response, dispatch)
        self.assertFalse(CustomUser.objects.filter(pk=self.user.pk).exists())
