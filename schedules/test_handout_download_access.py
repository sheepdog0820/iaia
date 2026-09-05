import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import CustomUser, Group
from schedules.models import HandoutInfo, SessionParticipant, TRPGSession


class HandoutDownloadAccessTest(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        setting = override_settings(MEDIA_ROOT=media.name)
        setting.enable()
        self.addCleanup(setting.disable)
        self.gm = CustomUser.objects.create_user(username="download-gm")
        self.pl = CustomUser.objects.create_user(username="download-pl")
        self.other = CustomUser.objects.create_user(username="download-other")
        group = Group.objects.create(name="private", created_by=self.gm)
        session = TRPGSession.objects.create(title="private", gm=self.gm, group=group)
        participant = SessionParticipant.objects.create(session=session, user=self.pl)
        self.handout = HandoutInfo.objects.create(
            session=session, participant=participant, title="secret", content="secret", is_secret=True
        )
        self.client.force_login(self.gm)
        self.payload = b"secret-handout-content"
        response = self.client.post(
            f"/api/schedules/handouts/{self.handout.pk}/attachments/",
            {"file": SimpleUploadedFile("secret.txt", self.payload, content_type="text/plain")},
        )
        self.assertEqual(response.status_code, 201)
        self.data = response.json()

    def test_urls_are_authenticated_downloads_for_gm_and_assigned_player(self):
        self.assertEqual(self.data["file"], self.data["file_url"])
        self.assertIn("/api/schedules/", self.data["file_url"])
        for user in (self.gm, self.pl):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.data["file_url"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), self.payload)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertIn("private", response["Cache-Control"])
                self.assertIn("attachment", response["Content-Disposition"])
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_saved_url_denies_other_user_anonymous_and_reassigned_player(self):
        for user in (self.other, None, self.pl):
            with self.subTest(user=getattr(user, "username", "anonymous")):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                if user == self.pl:
                    participant = SessionParticipant.objects.create(session=self.handout.session, user=self.other)
                    self.handout.participant = participant
                    self.handout.save()
                response = self.client.get(self.data["file_url"])
                self.assertIn(response.status_code, (401, 403, 404))
                self.assertIn("no-store", response["Cache-Control"])
                self.assertNotIn(self.payload, response.content)

    def test_missing_file_returns_not_found(self):
        attachment = self.handout.attachments.get()
        attachment.file.delete(save=False)
        response = self.client.get(self.data["file_url"])
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response["Cache-Control"])

    def test_legacy_media_url_rechecks_access(self):
        attachment = self.handout.attachments.get()
        url = "/media/" + attachment.file.name
        self.client.force_login(self.pl)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.payload)
        self.client.force_login(self.other)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response["Cache-Control"])

    @override_settings(DEBUG=True)
    def test_normalized_legacy_paths_cannot_bypass_permission_checks(self):
        attachment = self.handout.attachments.get()
        self.client.force_login(self.other)
        for prefix in ("./", "other/../", "%2e/", "other/%2e%2e/"):
            with self.subTest(prefix=prefix):
                response = self.client.get("/media/" + prefix + attachment.file.name)
                self.assertEqual(response.status_code, 404)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertNotIn(self.payload, response.content)

    def test_non_handout_development_media_behavior_is_preserved(self):
        Path(settings.MEDIA_ROOT, "public.txt").write_bytes(b"public-media")
        self.client.logout()
        with override_settings(DEBUG=True):
            response = self.client.get("/media/public.txt")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"public-media")
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get("/media/public.txt").status_code, 404)
