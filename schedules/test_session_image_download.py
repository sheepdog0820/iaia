import io
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import CustomUser, Group
from schedules.models import SessionImage, TRPGSession
from schedules.serializers import SessionImageSerializer
from schedules.session_permissions import create_participant


class SessionImageDownloadTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name, MEDIA_URL="/media/")
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = CustomUser.objects.create_user(username="image-owner")
        self.viewer = CustomUser.objects.create_user(username="image-viewer")
        self.outsider = CustomUser.objects.create_user(username="image-outsider")
        self.session = TRPGSession.objects.create(
            title="非公開の画像試験", gm=self.owner, created_by=self.owner, visibility="private"
        )
        self.participant = create_participant(session=self.session, user=self.viewer, role="player")
        data = io.BytesIO()
        Image.new("RGB", (8, 8), "purple").save(data, "PNG")
        self.picture = SessionImage.objects.create(
            session=self.session,
            uploaded_by=self.owner,
            image=SimpleUploadedFile("test.png", data.getvalue(), content_type="image/png"),
        )
        with self.picture.image.open("rb") as source:
            self.expected = source.read()
        self.legacy = self.picture.image.url
        self.url = f"/api/schedules/session-images/{self.picture.pk}/content/"

    def assert_image(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.expected)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("Cookie", response["Vary"])
        self.assertIn("Authorization", response["Vary"])

    def test_authorized_session_cookie_download_in_debug_and_production(self):
        self.client.force_login(self.viewer)
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                self.assert_image(self.client.get(self.url))
                self.assert_image(self.client.get(self.legacy))

    def test_private_image_denies_outsider_and_anonymous_in_both_modes(self):
        for user in (None, self.outsider):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for debug in (True, False):
                with self.subTest(user=user, debug=debug), override_settings(DEBUG=debug):
                    for url in (self.url, self.legacy):
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 404)
                        self.assertNotIn(self.expected, response.content)

    def test_token_authentication(self):
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.viewer)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assert_image(client.get(self.url))

    def test_participant_removal_revokes_existing_url(self):
        self.client.force_login(self.viewer)
        self.assert_image(self.client.get(self.url))
        self.participant.delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_public_image_becomes_private_without_changing_url(self):
        self.session.visibility = "public"
        self.session.save(update_fields=["visibility"])
        self.assert_image(self.client.get(self.url))
        self.session.visibility = "private"
        self.session.save(update_fields=["visibility"])
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_group_membership_removal_revokes_access(self):
        group = Group.objects.create(name="画像閲覧グループ", created_by=self.owner)
        group.members.add(self.outsider)
        self.session.group = group
        self.session.save(update_fields=["group"])
        self.client.force_login(self.outsider)
        self.assert_image(self.client.get(self.url))
        group.members.remove(self.outsider)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_normalized_legacy_path_cannot_bypass_permission(self):
        with override_settings(DEBUG=True):
            response = self.client.get(self.legacy.replace("/media/", "/media/other/../"))
        self.assertEqual(response.status_code, 404)

    def test_missing_storage_file_returns_404(self):
        self.picture.image.storage.delete(self.picture.image.name)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_missing_record_or_empty_file_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url.replace(f"/{self.picture.pk}/", "/999999/")).status_code, 404)
        self.picture.image = ""
        self.picture.save(update_fields=["image"])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertIsNone(self.picture.content_url)
        self.assertIsNone(SessionImageSerializer(self.picture).data["image_url"])

    def test_unrecognized_type_is_downloaded_instead_of_rendered(self):
        self.picture.image.save("legacy.html", SimpleUploadedFile("legacy.html", b"<script>test</script>"))
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertEqual(response["Content-Disposition"], "attachment")
        self.assertEqual(b"".join(response.streaming_content), b"<script>test</script>")

    def test_serializer_with_request_uses_absolute_protected_url(self):
        from rest_framework.test import APIRequestFactory

        data = SessionImageSerializer(self.picture, context={"request": APIRequestFactory().get("/")}).data
        self.assertEqual(data["image"], f"http://testserver{self.url}")
        self.assertEqual(data["image_url"], data["image"])

    def test_serializer_uses_authorized_url_without_requesting_storage_url(self):
        with patch.object(self.picture.image.storage, "url", side_effect=AssertionError("Storage URL exposed")):
            data = SessionImageSerializer(self.picture).data
        self.assertEqual(data["image"], self.url)
        self.assertEqual(data["image_url"], self.url)

    def test_upload_preserves_filename_length_validation(self):
        upload = SimpleUploadedFile("x" * 110 + ".png", self.expected, content_type="image/png")
        serializer = SessionImageSerializer(data={"image": upload})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["image"][0].code, "max_length")

    def test_html_uses_authorized_image_url(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("session_detail", kwargs={"pk": self.session.pk}), HTTP_ACCEPT="text/html")
        self.assertContains(response, self.url)
        self.assertNotContains(response, self.legacy)
