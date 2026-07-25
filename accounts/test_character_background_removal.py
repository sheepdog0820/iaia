import io
import tempfile
from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.user = CustomUser.objects.create_user(username="premium-user", password="testpass123")
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
        other_user = CustomUser.objects.create_user(username="other-user", password="testpass123")
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
