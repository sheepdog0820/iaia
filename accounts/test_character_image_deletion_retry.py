import io
import tempfile
from unittest.mock import patch

from botocore.exceptions import ClientError, EndpointConnectionError
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.test_character_factories import create_character_with_system_data


class CharacterImageDeletionRetryTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = get_user_model().objects.create_user(username="portrait-delete-owner")
        self.other = get_user_model().objects.create_user(username="portrait-delete-other")
        self.client = APIClient()
        self.client.raise_request_exception = False
        self.client.force_authenticate(user=self.owner)
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), "purple").save(buffer, "PNG")
        self.content = buffer.getvalue()

    def make_images(self, edition):
        character, detail = create_character_with_system_data(user=self.owner, edition=edition, name="画像削除再試行")
        images = [
            detail.images.create(
                image=SimpleUploadedFile(f"retry-{index}.png", self.content, content_type="image/png"),
                is_main=index == 0,
                order=index,
            )
            for index in range(2)
        ]
        return character, detail, images

    def check_storage_failure(self, edition, error, *, delete_main):
        character, detail, images = self.make_images(edition)
        image = images[0 if delete_main else 1]
        storage, name = image.image.storage, image.image.name
        url = f"/api/accounts/character-sheets/{character.pk}/images/{image.pk}/"
        before = list(detail.images.order_by("pk").values_list("pk", "image", "is_main", "order"))
        with patch.object(storage, "delete", side_effect=error) as delete:
            with self.assertLogs(level="WARNING") as captured:
                response = self.client.delete(url)
            self.assertEqual(response.status_code, 503)
            self.assertIn("再試行", response.json()["detail"])
            self.assertNotIn("private-storage-detail", response.content.decode())
            self.assertNotIn("private-storage-detail", "\n".join(captured.output))
            self.assertIn("no-store", response["Cache-Control"])
            delete.assert_called_once_with(name)
        self.assertEqual(list(detail.images.order_by("pk").values_list("pk", "image", "is_main", "order")), before)
        for attached in images:
            with attached.image.open("rb") as stored:
                self.assertEqual(stored.read(), self.content)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(detail.images.filter(pk=image.pk).exists())
        self.assertFalse(storage.exists(name))
        remaining = detail.images.get()
        self.assertTrue(remaining.is_main)
        with remaining.image.open("rb") as stored:
            self.assertEqual(stored.read(), self.content)

    def test_storage_errors_preserve_main_flags_and_allow_retry(self):
        for edition in ("6th", "7th"):
            for error in (
                OSError("private-storage-detail"),
                EndpointConnectionError(endpoint_url="https://private-storage-detail.invalid"),
                ClientError(
                    {"Error": {"Code": "ServiceUnavailable", "Message": "private-storage-detail"}}, "DeleteObject"
                ),
            ):
                with self.subTest(edition=edition, error_type=type(error).__name__):
                    self.check_storage_failure(edition, error, delete_main=True)

    def test_nonmain_storage_failure_does_not_change_main_image(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                self.check_storage_failure(edition, OSError("private-storage-detail"), delete_main=False)

    def test_missing_file_allows_metadata_deletion(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                character, detail, images = self.make_images(edition)
                target = images[0]
                target.image.storage.delete(target.image.name)
                url = f"/api/accounts/character-sheets/{character.pk}/images/{target.pk}/"
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertFalse(detail.images.filter(pk=target.pk).exists())
                self.assertTrue(detail.images.get().is_main)

    def test_other_user_cannot_trigger_storage_deletion(self):
        self.client.force_authenticate(user=self.other)
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                character, detail, images = self.make_images(edition)
                target = images[0]
                with patch.object(target.image.storage, "delete") as delete:
                    url = f"/api/accounts/character-sheets/{character.pk}/images/{target.pk}/"
                    self.assertEqual(self.client.delete(url).status_code, 403)
                    delete.assert_not_called()
                target.refresh_from_db()
                self.assertTrue(target.is_main)
                self.assertEqual(detail.images.count(), 2)
                self.assertTrue(target.image.storage.exists(target.image.name))
