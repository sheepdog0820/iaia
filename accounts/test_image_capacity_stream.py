from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
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
