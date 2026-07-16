import io
import tempfile
import zipfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CharacterSheet
from accounts.character_models import CharacterImage6th as CharacterImage
from accounts.test_character_integration import CharacterIntegrationTestCase
from accounts.test_character_factories import create_6th_character

User = get_user_model()


class CharacterImageAPISMokeTest(APITestCase):
    """画像APIの簡易スモークテスト"""

    def setUp(self):
        self.user = User.objects.create_user(username="apitester", password="pass123", email="api@example.com")
        self.client.force_authenticate(user=self.user)

        self.sheet, self.detail = create_6th_character(
            user=self.user,
            name="Image API Sheet",
            edition="6th",
            age=25,
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

    def test_set_main_endpoint_updates_flag(self):
        """set-mainエンドポイントでメイン画像を切替できること"""
        img1 = CharacterImage.objects.create(
            character_sheet=self.detail,
            image="test1.jpg",
            is_main=True,
            order=0,
        )
        img2 = CharacterImage.objects.create(
            character_sheet=self.detail,
            image="test2.jpg",
            is_main=False,
            order=1,
        )

        url = reverse(
            "character-images-set-main",
            kwargs={"character_sheet_id": self.sheet.id, "pk": img2.id},
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_main)
        self.assertTrue(img2.is_main)

    def test_delete_main_promotes_next(self):
        """メイン画像を削除すると次の画像がメインになる"""
        img1 = CharacterImage.objects.create(
            character_sheet=self.detail,
            image="main.jpg",
            is_main=True,
            order=0,
        )
        img2 = CharacterImage.objects.create(
            character_sheet=self.detail,
            image="second.jpg",
            is_main=False,
            order=1,
        )

        url = reverse(
            "character-images-detail",
            kwargs={"character_sheet_id": self.sheet.id, "pk": img1.id},
        )
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        img2.refresh_from_db()
        self.assertTrue(img2.is_main)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CharacterImageDownloadZipTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="zip_owner",
            password="pass123",
            email="zip-owner@example.com",
        )
        self.other_user = User.objects.create_user(
            username="zip_other",
            password="pass123",
            email="zip-other@example.com",
        )
        self.sheet, self.detail = create_6th_character(
            user=self.user,
            name="ZIP Investigator",
            edition="6th",
            age=25,
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
            access_scope="private",
        )

    def uploaded_file(self, name, content):
        return SimpleUploadedFile(name, content, content_type="image/png")

    def archive(self, response):
        return zipfile.ZipFile(io.BytesIO(response.content))

    def test_owner_downloads_character_images_zip_in_display_order(self):
        CharacterImage.objects.create(
            character_sheet=self.detail,
            image=self.uploaded_file("second.png", b"second-image"),
            is_main=False,
            order=2,
        )
        CharacterImage.objects.create(
            character_sheet=self.detail,
            image=self.uploaded_file("main.png", b"main-image"),
            is_main=True,
            order=1,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("character-image-download", kwargs={"character_id": self.sheet.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment", response["Content-Disposition"])

        with self.archive(response) as archive:
            self.assertEqual(archive.namelist(), ["01_main_main.png", "02_second.png"])
            self.assertEqual(archive.read("01_main_main.png"), b"main-image")
            self.assertEqual(archive.read("02_second.png"), b"second-image")

    def test_download_uses_legacy_character_image_when_multiple_images_are_absent(self):
        self.detail.character_image = self.uploaded_file("legacy.png", b"legacy-image")
        self.detail.save(update_fields=["character_image"])

        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("character-image-download", kwargs={"character_id": self.sheet.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.archive(response) as archive:
            self.assertEqual(archive.namelist(), ["01_main_legacy.png"])
            self.assertEqual(archive.read("01_main_legacy.png"), b"legacy-image")

    def test_download_returns_404_when_no_images_are_available(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("character-image-download", kwargs={"character_id": self.sheet.id}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_character_images_are_not_readable_by_anonymous_or_unrelated_users(self):
        CharacterImage.objects.create(
            character_sheet=self.detail,
            image=self.uploaded_file("private.png", b"private-image"),
            is_main=True,
        )
        url = reverse("character-image-download", kwargs={"character_id": self.sheet.id})
        list_url = reverse("character-image-list", kwargs={"character_id": self.sheet.id})

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(list_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_public_character_zip_is_readable_anonymously(self):
        self.sheet.access_scope = "public"
        self.sheet.save(update_fields=["access_scope"])
        CharacterImage.objects.create(
            character_sheet=self.detail,
            image=self.uploaded_file("public.png", b"public-image"),
            is_main=True,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("character-image-download", kwargs={"character_id": self.sheet.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.archive(response) as archive:
            self.assertEqual(archive.read("01_main_public.png"), b"public-image")

    def test_link_shared_character_zip_uses_share_token_and_closes_when_private(self):
        self.sheet.access_scope = "link"
        self.sheet.save(update_fields=["access_scope"])
        CharacterImage.objects.create(
            character_sheet=self.detail,
            image=self.uploaded_file("shared.png", b"shared-image"),
            is_main=True,
        )
        url = f"/share/characters/{self.sheet.share_token}/images.zip"

        self.client.force_authenticate(user=None)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.archive(response) as archive:
            self.assertEqual(archive.read("01_main_shared.png"), b"shared-image")

        self.sheet.access_scope = "private"
        self.sheet.save(update_fields=["access_scope"])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)


class CCFOLIAEndpointSmokeTest(APITestCase):
    """CCFOLIAエクスポートの簡易確認"""

    def setUp(self):
        self.user = User.objects.create_user(username="ccfoliauser", password="pass123", email="ccfolia@example.com")
        self.client.force_authenticate(user=self.user)

        helper = CharacterIntegrationTestCase()
        helper.setUp()
        self.sheet = helper.create_character_with_stats(user=self.user)

    def test_ccfolia_json_status_ok(self):
        url = reverse("character-sheet-ccfolia-json", kwargs={"pk": self.sheet.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("data", resp.data)
        self.assertEqual(resp.data.get("kind"), "character")
