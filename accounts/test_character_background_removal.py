import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.character_models import CharacterSheet6th
from accounts.models import CharacterSheet, CustomUser
from accounts.serializers import CharacterSheetSerializer


class CharacterBackgroundRemovalTests(TestCase):
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
        response = self.client.post(reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart")

        self.assertEqual(response.status_code, 403)

    @patch("accounts.views.character_image_views.remove_background", autospec=True)
    def test_premium_user_receives_transparent_png(self, remove_background):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        remove_background.return_value = self.transparent_png()

        response = self.client.post(reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(response["Content-Disposition"].endswith('filename="portrait-transparent.png"'))
        self.assertEqual(response.content, self.transparent_png())
        remove_background.assert_called_once()

    @patch("accounts.views.character_image_views.remove_background", autospec=True)
    def test_premium_user_rejects_images_exceeding_dimension_limit(self, remove_background):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])

        response = self.client.post(
            reverse("character-image-remove-background"),
            {"image": self.image_upload(size=(4097, 4))},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Image dimensions must not exceed 4096px.")
        remove_background.assert_not_called()

    @patch("accounts.views.character_image_views.remove_background", autospec=True)
    def test_invalid_background_removal_result_returns_service_error(self, remove_background):
        self.user.is_premium = True
        self.user.save(update_fields=["is_premium"])
        remove_background.return_value = b"not-an-image"

        response = self.client.post(reverse("character-image-remove-background"), {"image": self.image_upload()}, format="multipart")

        self.assertEqual(response.status_code, 503)

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
