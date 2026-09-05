import io
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from accounts.models import CustomUser, Group
from scenarios.models import Scenario, ScenarioImage
from schedules.models import SessionImage, TRPGSession


class ImageDeletionRetryTest(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = CustomUser.objects.create_user(username="image-delete-owner")
        self.other = CustomUser.objects.create_user(username="image-delete-other")
        group = Group.objects.create(name="image-delete-private", created_by=self.owner)
        self.session = TRPGSession.objects.create(title="image-delete-private", gm=self.owner, group=group)
        self.scenario = Scenario.objects.create(
            title="image-delete-private", created_by=self.owner, visibility="private"
        )
        self.client.force_login(self.owner)

    def create_image(self, kind):
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), "purple").save(buffer, "PNG")
        image = SimpleUploadedFile("retry.png", buffer.getvalue(), content_type="image/png")
        if kind == "scenario":
            instance = ScenarioImage.objects.create(scenario=self.scenario, image=image, uploaded_by=self.owner)
            url = f"/api/scenarios/scenario-images/{instance.pk}/"
        else:
            instance = SessionImage.objects.create(session=self.session, image=image, uploaded_by=self.owner)
            url = f"/api/schedules/session-images/{instance.pk}/"
        return instance, url

    def test_storage_failure_retains_image_reference_until_successful_retry(self):
        for kind in ("scenario", "session"):
            with self.subTest(kind=kind):
                instance, url = self.create_image(kind)
                storage, name = instance.image.storage, instance.image.name
                with patch.object(storage, "delete", side_effect=OSError("private-storage-detail")) as delete:
                    response = self.client.delete(url)
                    self.assertEqual(response.status_code, 503)
                    self.assertIn("再試行", response.json()["detail"])
                    self.assertNotIn("private-storage-detail", response.content.decode())
                    delete.assert_called_once_with(name)
                instance.refresh_from_db()
                self.assertEqual(instance.image.name, name)
                self.assertTrue(storage.exists(name))
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertFalse(type(instance).objects.filter(pk=instance.pk).exists())
                self.assertFalse(storage.exists(name))

    def test_other_user_cannot_trigger_storage_deletion(self):
        self.client.force_login(self.other)
        for kind in ("scenario", "session"):
            with self.subTest(kind=kind):
                instance, url = self.create_image(kind)
                with patch.object(instance.image.storage, "delete") as delete:
                    self.assertEqual(self.client.delete(url).status_code, 404)
                    delete.assert_not_called()
                self.assertTrue(type(instance).objects.filter(pk=instance.pk).exists())

    def test_missing_file_still_allows_record_deletion(self):
        for kind in ("scenario", "session"):
            with self.subTest(kind=kind):
                instance, url = self.create_image(kind)
                instance.image.storage.delete(instance.image.name)
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertFalse(type(instance).objects.filter(pk=instance.pk).exists())
