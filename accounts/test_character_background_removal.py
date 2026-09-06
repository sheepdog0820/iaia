import io
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.background_removal_tasks import process_background_removal_job, start_background_removal_task
from accounts.character_models import CharacterSheet6th
from accounts.models import BackgroundRemovalJob, CharacterSheet, CustomUser
from accounts.serializers import CharacterSheetSerializer


class CharacterBackgroundRemovalTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.media_directory.cleanup()

    def setUp(self):
        # Isolated test fixture or mocked credential; never a production secret.
        self.user = CustomUser.objects.create_user(username="premium-user", password="testpass123")  # nosec B106
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @staticmethod
    def image_upload(name="portrait.jpg", size=(4, 4)):
        image = Image.new("RGB", size, "white")
        content = io.BytesIO()
        image.save(content, "JPEG")
        return SimpleUploadedFile(name, content.getvalue(), content_type="image/jpeg")

    @staticmethod
    def transparent_png():
        image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        content = io.BytesIO()
        image.save(content, "PNG")
        return content.getvalue()

    def test_background_removal_requires_premium_access(self):
        response = self.client.post(
            reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart"
        )

        self.assertEqual(response.status_code, 403)

    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_premium_user_creates_a_background_removal_job(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])

        response = self.client.post(
            reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart"
        )

        self.assertEqual(response.status_code, 202)
        job = BackgroundRemovalJob.objects.get(pk=response.data["job_id"])
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.status, BackgroundRemovalJob.Status.PENDING)
        self.assertTrue(job.source_image.name)
        start_task.assert_called_once_with(job)
        self.assertEqual(
            response.data["status_url"], reverse("character-image-background-removal-status", args=[job.pk])
        )

    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_second_active_background_removal_job_is_rejected(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.RUNNING,
            source_image=self.image_upload(),
        )

        response = self.client.post(
            reverse("character-image-remove-background"), {"image": self.image_upload("second.jpg")}, format="multipart"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(BackgroundRemovalJob.objects.filter(user=self.user).count(), 1)
        start_task.assert_not_called()

    @override_settings(BACKGROUND_REMOVAL_DAILY_LIMIT=10)
    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_daily_background_removal_limit_is_enforced_per_user(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        for index in range(10):
            BackgroundRemovalJob.objects.create(
                user=self.user,
                status=(BackgroundRemovalJob.Status.FAILED if index == 0 else BackgroundRemovalJob.Status.COMPLETED),
                original_filename=f"portrait-{index}.jpg",
            )
        other_user = CustomUser.objects.create_user(username="other-premium-user")
        BackgroundRemovalJob.objects.create(user=other_user, status=BackgroundRemovalJob.Status.COMPLETED)

        response = self.client.post(
            reverse("character-image-remove-background"),
            {"image": self.image_upload("over-limit.jpg")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["daily_limit"], 10)
        self.assertEqual(response.data["used_count"], 10)
        self.assertIn("本日の背景透過処理回数の上限（10回）に達しました", response.data["error"])
        self.assertTrue(response.data["reset_at"].endswith("+09:00"))
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertEqual(BackgroundRemovalJob.objects.filter(user=self.user).count(), 10)
        start_task.assert_not_called()

    @override_settings(BACKGROUND_REMOVAL_DAILY_LIMIT=1)
    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_previous_day_background_removal_does_not_count_toward_daily_limit(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        previous = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.FAILED,
        )
        BackgroundRemovalJob.objects.filter(pk=previous.pk).update(created_at=timezone.now() - timedelta(days=1))

        response = self.client.post(
            reverse("character-image-remove-background"),
            {"image": self.image_upload("today.jpg")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(BackgroundRemovalJob.objects.filter(user=self.user).count(), 2)
        start_task.assert_called_once()

    @override_settings(BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS=60)
    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_stale_job_is_failed_before_a_replacement_is_started(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        stale_job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.RUNNING,
            source_image=self.image_upload("stale.jpg"),
        )
        BackgroundRemovalJob.objects.filter(pk=stale_job.pk).update(updated_at=timezone.now() - timedelta(seconds=61))

        response = self.client.post(
            reverse("character-image-remove-background"),
            {"image": self.image_upload("replacement.jpg")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 202)
        stale_job.refresh_from_db()
        self.assertEqual(stale_job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(stale_job.error_message, "Background removal timed out.")
        self.assertFalse(stale_job.source_image)
        self.assertEqual(BackgroundRemovalJob.objects.filter(user=self.user).count(), 2)
        start_task.assert_called_once()

    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_premium_user_rejects_images_exceeding_dimension_limit(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])

        response = self.client.post(
            reverse("character-image-remove-background"),
            {"image": self.image_upload(size=(4097, 4))},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Image dimensions must not exceed 4096px.")
        start_task.assert_not_called()

    @patch("accounts.views.character_image_views.start_background_removal_task", autospec=True)
    def test_background_removal_start_failure_marks_job_failed(self, start_task):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        start_task.side_effect = RuntimeError("ECS is unavailable")

        response = self.client.post(
            reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart"
        )

        self.assertEqual(response.status_code, 503)
        job = BackgroundRemovalJob.objects.get()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)

    def test_completed_job_returns_transparent_png(self):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.COMPLETED,
            original_filename='portrait"\r\nInjected.jpg',
        )
        job.result_image.save(
            "portrait-transparent.png", SimpleUploadedFile("portrait-transparent.png", self.transparent_png())
        )

        response = self.client.get(reverse("character-image-background-removal-status", args=[job.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, self.transparent_png())
        self.assertNotIn("\r", response["Content-Disposition"])
        self.assertNotIn("\n", response["Content-Disposition"])
        self.assertIn("portrait_Injected-transparent.png", response["Content-Disposition"])

    def test_background_removal_job_status_is_owner_only(self):
        # Isolated test fixture or mocked credential; never a production secret.
        other_user = CustomUser.objects.create_user(username="other-user", password="testpass123")  # nosec B106
        job = BackgroundRemovalJob.objects.create(user=other_user, source_image=self.image_upload())

        response = self.client.get(reverse("character-image-background-removal-status", args=[job.pk]))

        self.assertEqual(response.status_code, 404)

    def test_pending_job_returns_accepted_status(self):
        job = BackgroundRemovalJob.objects.create(user=self.user, source_image=self.image_upload())

        response = self.client.get(reverse("character-image-background-removal-status", args=[job.pk]))

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {"job_id": str(job.pk), "status": BackgroundRemovalJob.Status.PENDING})

    @patch("accounts.background_removal_tasks.remove_background", autospec=True)
    def test_worker_processes_persisted_job_outside_the_web_request(self, remove_background):
        job = BackgroundRemovalJob.objects.create(user=self.user, original_filename="portrait.jpg")
        job.source_image.save("portrait.jpg", self.image_upload())
        remove_background.return_value = self.transparent_png()

        processed = process_background_removal_job(job.pk)

        self.assertEqual(processed.status, BackgroundRemovalJob.Status.COMPLETED)
        self.assertTrue(processed.result_image.name)
        self.assertFalse(processed.source_image)
        remove_background.assert_called_once()

    @patch("accounts.background_removal_tasks.remove_background", autospec=True)
    def test_running_job_is_not_processed_twice(self, remove_background):
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.RUNNING,
            source_image=self.image_upload(),
        )

        processed = process_background_removal_job(job.pk)

        self.assertEqual(processed.status, BackgroundRemovalJob.Status.RUNNING)
        remove_background.assert_not_called()

    @patch("accounts.background_removal_tasks.remove_background", autospec=True)
    def test_worker_failure_is_persisted_without_exposing_internal_details(self, remove_background):
        remove_background.side_effect = RuntimeError("internal model failure")
        job = BackgroundRemovalJob.objects.create(user=self.user, source_image=self.image_upload())

        processed = process_background_removal_job(job.pk)

        self.assertEqual(processed.status, BackgroundRemovalJob.Status.FAILED)
        self.assertEqual(processed.error_message, "Background removal could not be completed.")
        self.assertNotIn("internal model failure", processed.error_message)
        self.assertFalse(processed.source_image)

    @override_settings(
        AWS_S3_REGION_NAME="ap-northeast-1",
        BACKGROUND_REMOVAL_ECS_CLUSTER="tableno-aws-pre",
        BACKGROUND_REMOVAL_TASK_DEFINITION="background-removal-task:1",
        BACKGROUND_REMOVAL_CONTAINER_NAME="background-removal",
        BACKGROUND_REMOVAL_SUBNETS=["subnet-private-a", "subnet-private-c"],
        BACKGROUND_REMOVAL_SECURITY_GROUPS=["sg-worker"],
        BACKGROUND_REMOVAL_ASSIGN_PUBLIC_IP=False,
    )
    @patch("boto3.client", autospec=True)
    def test_fargate_task_uses_configured_network_and_container(self, boto_client):
        ecs = Mock()
        ecs.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:task/job-1"}], "failures": []}
        boto_client.return_value = ecs
        job = BackgroundRemovalJob.objects.create(user=self.user, source_image=self.image_upload())

        start_background_removal_task(job)

        boto_client.assert_called_once_with("ecs", region_name="ap-northeast-1")
        ecs.run_task.assert_called_once_with(
            cluster="tableno-aws-pre",
            launchType="FARGATE",
            taskDefinition="background-removal-task:1",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": ["subnet-private-a", "subnet-private-c"],
                    "securityGroups": ["sg-worker"],
                    "assignPublicIp": "DISABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "background-removal",
                        "command": ["python", "manage.py", "process_background_removal_job", str(job.pk)],
                    }
                ]
            },
        )
        job.refresh_from_db()
        self.assertEqual(job.task_arn, "arn:aws:ecs:task/job-1")

    @override_settings(
        AWS_S3_REGION_NAME="ap-northeast-1",
        BACKGROUND_REMOVAL_ECS_CLUSTER="tableno-aws-pre",
        BACKGROUND_REMOVAL_TASK_DEFINITION="background-removal-task:1",
        BACKGROUND_REMOVAL_CONTAINER_NAME="background-removal",
        BACKGROUND_REMOVAL_SUBNETS=["subnet-private-a"],
        BACKGROUND_REMOVAL_SECURITY_GROUPS=["sg-worker"],
    )
    @patch("boto3.client", autospec=True)
    def test_fargate_launch_failure_does_not_persist_a_task_arn(self, boto_client):
        ecs = Mock()
        ecs.run_task.return_value = {"tasks": [], "failures": [{"reason": "RESOURCE:MEMORY"}]}
        boto_client.return_value = ecs
        job = BackgroundRemovalJob.objects.create(user=self.user, source_image=self.image_upload())

        with self.assertRaisesMessage(RuntimeError, "Unable to launch background removal worker"):
            start_background_removal_task(job)

        job.refresh_from_db()
        self.assertEqual(job.task_arn, "")

    @override_settings(
        BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS=24,
        BACKGROUND_REMOVAL_JOB_RETENTION_DAYS=7,
    )
    def test_cleanup_removes_expired_result_but_keeps_recent_job_record(self):
        from accounts.background_removal_tasks import cleanup_background_removal_jobs

        now = timezone.now()
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.COMPLETED,
        )
        job.result_image.save(
            "expired-result.png",
            SimpleUploadedFile("expired-result.png", self.transparent_png()),
        )
        result_name = job.result_image.name
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=now - timedelta(hours=25))
        job.refresh_from_db()
        completed_at = job.updated_at

        summary = cleanup_background_removal_jobs(now=now)

        job.refresh_from_db()
        self.assertFalse(job.result_image)
        self.assertEqual(job.updated_at, completed_at)
        self.assertFalse(job.result_image.storage.exists(result_name))
        self.assertEqual(summary["deleted_result_images"], 1)
        self.assertEqual(summary["deleted_jobs"], 0)

    @override_settings(
        BACKGROUND_REMOVAL_JOB_TIMEOUT_SECONDS=60,
        BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS=24,
        BACKGROUND_REMOVAL_JOB_RETENTION_DAYS=7,
    )
    def test_cleanup_fails_stale_active_job_before_applying_retention(self):
        from accounts.background_removal_tasks import cleanup_background_removal_jobs

        now = timezone.now()
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.RUNNING,
            source_image=self.image_upload("stale-source.jpg"),
        )
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=now - timedelta(minutes=2))

        summary = cleanup_background_removal_jobs(now=now)

        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundRemovalJob.Status.FAILED)
        self.assertFalse(job.source_image)
        self.assertEqual(summary["timed_out_jobs"], 1)
        self.assertEqual(summary["deleted_jobs"], 0)

    @override_settings(
        BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS=24,
        BACKGROUND_REMOVAL_JOB_RETENTION_DAYS=7,
    )
    def test_cleanup_deletes_expired_terminal_job_and_all_files(self):
        from accounts.background_removal_tasks import cleanup_background_removal_jobs

        now = timezone.now()
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.FAILED,
            source_image=self.image_upload("expired-source.jpg"),
        )
        job.result_image.save(
            "expired-job-result.png",
            SimpleUploadedFile("expired-job-result.png", self.transparent_png()),
        )
        source_name = job.source_image.name
        result_name = job.result_image.name
        storage = job.result_image.storage
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=now - timedelta(days=8))

        summary = cleanup_background_removal_jobs(now=now)

        self.assertFalse(BackgroundRemovalJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(storage.exists(source_name))
        self.assertFalse(storage.exists(result_name))
        self.assertEqual(summary["deleted_jobs"], 1)

    @override_settings(
        BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS=24,
        BACKGROUND_REMOVAL_JOB_RETENTION_DAYS=7,
    )
    def test_cleanup_keeps_job_when_storage_deletion_fails(self):
        from accounts.background_removal_tasks import cleanup_background_removal_jobs

        now = timezone.now()
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.COMPLETED,
        )
        job.result_image.save(
            "undeletable-result.png",
            SimpleUploadedFile("undeletable-result.png", self.transparent_png()),
        )
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=now - timedelta(days=8))

        with patch.object(job.result_image.storage, "delete", side_effect=OSError("storage unavailable")):
            summary = cleanup_background_removal_jobs(now=now)

        job.refresh_from_db()
        self.assertTrue(job.result_image)
        self.assertEqual(summary["failed_jobs"], 1)
        self.assertEqual(summary["deleted_jobs"], 0)

    @override_settings(
        BACKGROUND_REMOVAL_RESULT_RETENTION_HOURS=24,
        BACKGROUND_REMOVAL_JOB_RETENTION_DAYS=7,
    )
    def test_cleanup_management_command_supports_dry_run(self):
        job = BackgroundRemovalJob.objects.create(
            user=self.user,
            status=BackgroundRemovalJob.Status.COMPLETED,
        )
        BackgroundRemovalJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(days=8))
        stdout = StringIO()

        call_command("cleanup_background_removal_jobs", "--dry-run", stdout=stdout)

        self.assertTrue(BackgroundRemovalJob.objects.filter(pk=job.pk).exists())
        self.assertIn("削除対象ジョブ: 1件", stdout.getvalue())

    def test_background_removal_cleanup_is_registered_with_celery_beat(self):
        from django.conf import settings

        entry = settings.CELERY_BEAT_SCHEDULE["cleanup-background-removal-jobs"]
        self.assertEqual(entry["task"], "accounts.tasks.cleanup_background_removal_jobs")
        self.assertEqual(entry["schedule"], 3600.0)

    def test_character_name_kana_is_serialized(self):
        character = CharacterSheet.objects.create(user=self.user, edition="6th")
        CharacterSheet6th.objects.create(
            character_sheet=character,
            name="高島 静雄",
            name_kana="たかしま しずお",
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )

        self.assertEqual(CharacterSheetSerializer(character).data["name_kana"], "たかしま しずお")
