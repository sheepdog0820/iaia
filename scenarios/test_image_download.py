import io
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIRequestFactory

from accounts.models import CustomUser, Group
from scenarios.models import Scenario, ScenarioImage
from scenarios.serializers import ScenarioImageSerializer
from schedules.models import TRPGSession
from schedules.session_permissions import create_participant


class ScenarioImageDownloadTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name, MEDIA_URL="/media/")
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = CustomUser.objects.create_user(username="scenario-image-owner")
        self.viewer = CustomUser.objects.create_user(username="scenario-image-viewer")
        self.scenario = Scenario.objects.create(title="非公開シナリオ", created_by=self.owner, visibility="private")
        data = io.BytesIO()
        Image.new("RGB", (8, 8), "green").save(data, "PNG")
        self.picture = ScenarioImage.objects.create(
            scenario=self.scenario,
            image=SimpleUploadedFile("test.png", data.getvalue(), content_type="image/png"),
        )
        with self.picture.image.open("rb") as source:
            self.expected = source.read()
        self.url = f"/api/scenarios/scenario-images/{self.picture.pk}/content/"
        self.legacy = self.picture.image.url

    def assert_image(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.expected)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("Cookie", response["Vary"])
        self.assertIn("Authorization", response["Vary"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_owner_and_unrelated_users_in_debug_and_production(self):
        for user in (None, self.viewer, self.owner):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for debug in (True, False):
                with self.subTest(user=user, debug=debug), override_settings(DEBUG=debug):
                    for url in (self.url, self.legacy):
                        response = self.client.get(url)
                        if user == self.owner:
                            self.assert_image(response)
                        else:
                            self.assertEqual(response.status_code, 404)

    def test_public_page_uses_protected_url_and_non_public_transition_revokes_it(self):
        self.scenario.visibility = "public"
        self.scenario.save(update_fields=["visibility"])
        response = self.client.get(reverse("scenario_public_view", kwargs={"scenario_id": self.scenario.pk}))
        self.assertContains(response, self.url)
        self.assertNotContains(response, self.legacy)
        self.assert_image(self.client.get(self.url))
        self.scenario.visibility = "private"
        self.scenario.save(update_fields=["visibility"])
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_group_departure_revokes_access(self):
        group = Group.objects.create(name="画像共有グループ", created_by=self.owner)
        group.members.add(self.owner, self.viewer)
        self.client.force_login(self.viewer)
        self.assert_image(self.client.get(self.url))
        group.members.remove(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_linked_session_viewer_uses_scoped_url_and_loses_access_after_leaving(self):
        session = TRPGSession.objects.create(
            title="関連セッション", gm=self.owner, created_by=self.owner, scenario=self.scenario, visibility="private"
        )
        participant = create_participant(session=session, user=self.viewer, role="player")
        url = f"/api/scenarios/scenario-images/{self.picture.pk}/sessions/{session.pk}/content/"
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("session_detail", kwargs={"pk": session.pk}), HTTP_ACCEPT="text/html")
        self.assertContains(response, url)
        self.assertNotContains(response, self.legacy)
        self.assert_image(self.client.get(url))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        participant.delete()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unrelated_session_and_anonymous_context_do_not_grant_access(self):
        unrelated = TRPGSession.objects.create(title="別のセッション", gm=self.viewer, visibility="public")
        self.client.force_login(self.viewer)
        url = f"/api/scenarios/scenario-images/{self.picture.pk}/sessions/{unrelated.pk}/content/"
        self.assertEqual(self.client.get(url).status_code, 404)
        unrelated.scenario = self.scenario
        unrelated.save(update_fields=["scenario"])
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_normalized_legacy_path_is_authorized(self):
        with override_settings(DEBUG=True):
            self.assertEqual(self.client.get(self.legacy.replace("/media/", "/media/other/../")).status_code, 404)

    def test_missing_file_and_missing_record_return_404(self):
        self.client.force_login(self.owner)
        self.picture.image.storage.delete(self.picture.image.name)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.picture.delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_serializer_never_asks_for_storage_url(self):
        with patch.object(self.picture.image.storage, "url", side_effect=AssertionError("Storage URL exposed")):
            data = ScenarioImageSerializer(self.picture).data
        self.assertEqual(data["image"], self.url)
        self.assertEqual(data["image_url"], self.url)
        data = ScenarioImageSerializer(self.picture, context={"request": APIRequestFactory().get("/")}).data
        self.assertEqual(data["image"], f"http://testserver{self.url}")
        self.assertEqual(data["image_url"], data["image"])

    def test_empty_file_has_no_content_url(self):
        self.picture.image = ""
        self.picture.save(update_fields=["image"])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertIsNone(self.picture.content_url)
        self.assertIsNone(ScenarioImageSerializer(self.picture).data["image_url"])

    def test_unknown_type_is_not_rendered(self):
        self.picture.image.save("legacy.html", SimpleUploadedFile("legacy.html", b"<script>test</script>"))
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertEqual(response["Content-Disposition"], "attachment")
        self.assertEqual(b"".join(response.streaming_content), b"<script>test</script>")

    def test_upload_keeps_filename_length_validation(self):
        upload = SimpleUploadedFile("x" * 110 + ".png", self.expected, content_type="image/png")
        serializer = ScenarioImageSerializer(data={"image": upload})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["image"][0].code, "max_length")
