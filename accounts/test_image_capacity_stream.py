import tempfile
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.exceptions import ValidationError

from accounts.models import CustomUser
from accounts.serializers import CharacterImageSerializer
from accounts.test_character_factories import create_character_with_system_data


class ImageCapacityStreamTests(TestCase):
    def setUp(self):
        user = CustomUser.objects.create_user(username="image-stream")
        self.registry, self.detail = create_character_with_system_data(user=user)
        self.serializer = CharacterImageSerializer(context={"character_sheet": self.registry})

    def test_failed_rewind_rejects_upload_without_changing_images(self):
        upload = Mock(size=100)
        upload.seek.side_effect = [None, OSError("secret storage path")]
        with patch("accounts.serializers.Image.open", side_effect=OSError("unreadable")):
            with self.assertRaisesMessage(ValidationError, "画像を読み直せませんでした"):
                self.serializer.validate({"image": upload})
        self.assertFalse(self.detail.images.exists())

    def test_successful_estimate_leaves_full_upload_readable(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
        contents = buffer.getvalue()
        upload = SimpleUploadedFile("image.png", contents, content_type="image/png")
        attrs = self.serializer.validate({"image": upload})
        self.assertIs(attrs["image"], upload)
        self.assertEqual(upload.tell(), 0)
        self.assertEqual(upload.read(), contents)

    @contextmanager
    def stored_image(self, edition="6th"):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            registry, detail = create_character_with_system_data(user=self.registry.user, edition=edition)
            buffer = BytesIO()
            with Image.new("RGB", (10, 10), "blue") as image:
                image.save(buffer, "PNG")
            saved = detail.images.create(
                image=SimpleUploadedFile("stored.png", buffer.getvalue(), content_type="image/png")
            )
            saved.image.close()
            storage = saved.image.storage
            original_open = storage.open
            handles = []

            def tracked_open(*args, **kwargs):
                handle = original_open(*args, **kwargs)
                handles.append(handle)
                return handle

            try:
                with patch.object(storage, "open", side_effect=tracked_open):
                    yield registry, detail, handles
            finally:
                # The RED must report an open-handle assertion, not a Windows cleanup failure.
                for handle in handles:
                    handle.close()

    def test_existing_image_handle_is_closed_for_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition), self.stored_image(edition) as (registry, detail, handles):
                attrs = CharacterImageSerializer(context={"character_sheet": registry}).validate({})
                self.assertEqual(attrs, {})
                self.assertTrue(handles)
                self.assertTrue(all(handle.closed for handle in handles))
                self.assertEqual(detail.images.count(), 1)

    def test_existing_image_handle_is_closed_when_metadata_cannot_be_read(self):
        with self.stored_image() as (registry, detail, handles):
            with patch("accounts.serializers.Image.open", side_effect=OSError("synthetic private image path")):
                CharacterImageSerializer(context={"character_sheet": registry}).validate({})
            self.assertTrue(handles)
            self.assertTrue(all(handle.closed for handle in handles))
            self.assertEqual(detail.images.count(), 1)

    def test_existing_image_handle_is_closed_before_total_capacity_rejection(self):
        with self.stored_image() as (registry, detail, handles):
            metadata = Mock(width=10000, height=10000)
            metadata.getbands.return_value = ("R", "G", "B")
            with patch("accounts.serializers.Image.open") as open_image:
                open_image.return_value.__enter__.return_value = metadata
                with self.assertRaisesMessage(ValidationError, "総容量が30MBを超えています"):
                    CharacterImageSerializer(context={"character_sheet": registry}).validate({})
            self.assertTrue(handles)
            self.assertTrue(all(handle.closed for handle in handles))
            self.assertEqual(detail.images.count(), 1)

    def test_failed_stored_handle_close_returns_safe_validation_error(self):
        with self.stored_image() as (registry, detail, handles):
            with patch.object(FieldFile, "close", side_effect=OSError("synthetic-private-location")):
                with self.assertRaisesMessage(ValidationError, "画像を読み直せませんでした") as caught:
                    CharacterImageSerializer(context={"character_sheet": registry}).validate({})
            self.assertNotIn("synthetic-private-location", str(caught.exception))
            self.assertEqual(detail.images.count(), 1)
