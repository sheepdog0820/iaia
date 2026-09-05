import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import CustomUser, Group
from schedules.models import HandoutAttachment, HandoutInfo, SessionParticipant, TRPGSession


class HandoutDeletionRetryTest(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.gm = CustomUser.objects.create_user(username="delete-gm")
        self.pl = CustomUser.objects.create_user(username="delete-pl")
        group = Group.objects.create(name="delete-private", created_by=self.gm)
        session = TRPGSession.objects.create(title="delete-private", gm=self.gm, group=group)
        participant = SessionParticipant.objects.create(session=session, user=self.pl)
        handout = HandoutInfo.objects.create(session=session, participant=participant, title="secret", content="secret")
        self.client.force_login(self.gm)
        upload = self.client.post(
            f"/api/schedules/handouts/{handout.pk}/attachments/",
            {"file": SimpleUploadedFile("secret.txt", b"synthetic-private-content", content_type="text/plain")},
        )
        self.assertEqual(upload.status_code, 201)
        self.attachment = HandoutAttachment.objects.get(pk=upload.json()["id"])
        self.url = f"/api/schedules/attachments/{self.attachment.pk}/"

    def test_storage_failure_preserves_reference_and_allows_retry(self):
        storage = self.attachment.file.storage
        name = self.attachment.file.name
        with patch.object(storage, "delete", side_effect=OSError("private-backend-detail")) as delete:
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 503)
            self.assertIn("再試行", response.json()["detail"])
            self.assertNotIn("private-backend-detail", response.content.decode())
            delete.assert_called_once_with(name)
        self.attachment.refresh_from_db()
        self.assertEqual(self.attachment.file.name, name)
        self.assertTrue(storage.exists(name))
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(HandoutAttachment.objects.filter(pk=self.attachment.pk).exists())
        self.assertFalse(storage.exists(name))

    def test_player_cannot_trigger_storage_deletion(self):
        self.client.force_login(self.pl)
        with patch.object(self.attachment.file.storage, "delete") as delete:
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 403)
            delete.assert_not_called()
        self.assertTrue(HandoutAttachment.objects.filter(pk=self.attachment.pk).exists())

    def test_already_missing_file_does_not_prevent_record_deletion(self):
        self.attachment.file.storage.delete(self.attachment.file.name)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(HandoutAttachment.objects.filter(pk=self.attachment.pk).exists())
