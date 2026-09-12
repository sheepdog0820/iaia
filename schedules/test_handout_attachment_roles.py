import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from schedules import session_permissions
from schedules.attachment_service import HandoutAttachmentService
from schedules.models import HandoutAttachment, HandoutInfo, TRPGSession


class HandoutAttachmentRoleTests(APITestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        users = get_user_model()
        self.gm = users.objects.create_user(username="attachment_gm")
        self.delegate = users.objects.create_user(username="attachment_delegate")
        self.player = users.objects.create_user(username="attachment_player")
        self.session = TRPGSession.objects.create(title="添付権限確認", gm=self.gm, date=timezone.now())
        self.delegate_participant = session_permissions.create_participant(
            session=self.session, user=self.delegate, role="gm"
        )
        participant = session_permissions.create_participant(session=self.session, user=self.player, role="player")
        self.handout = HandoutInfo.objects.create(
            session=self.session, participant=participant, title="秘密資料", content="内容", is_secret=True
        )
        self.url = f"/api/schedules/handouts/{self.handout.pk}/attachments/"

    def file(self):
        return SimpleUploadedFile("secret.pdf", b"%PDF-1.4\nprivate", content_type="application/pdf")

    def attachment(self):
        return HandoutAttachmentService().upload_attachment(handout=self.handout, file=self.file(), uploaded_by=self.gm)

    def test_delegated_gm_can_upload(self):
        self.client.force_authenticate(self.delegate)
        response = self.client.post(self.url, {"file": self.file()}, format="multipart")
        self.assertEqual(response.status_code, 201)
        attachment = HandoutAttachment.objects.get(pk=response.data["id"])
        self.assertEqual(attachment.uploaded_by_id, self.delegate.pk)
        self.assertEqual(attachment.handout_id, self.handout.pk)

    def test_delegated_gm_can_delete_original_gms_attachment(self):
        attachment = self.attachment()
        storage, name = attachment.file.storage, attachment.file.name
        self.client.force_authenticate(self.delegate)
        response = self.client.delete(f"/api/schedules/attachments/{attachment.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(HandoutAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(storage.exists(name))

    def test_recipient_can_read_but_cannot_upload_or_delete(self):
        attachment = self.attachment()
        self.client.force_authenticate(self.player)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"file": self.file()}, format="multipart").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/schedules/attachments/{attachment.pk}/").status_code, 403)
        self.assertEqual(HandoutAttachment.objects.count(), 1)
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))

    def test_revoked_gm_cannot_upload_or_delete(self):
        attachment = self.attachment()
        self.delegate_participant.participant_roles.filter(role="gm").delete()
        self.client.force_authenticate(self.delegate)
        self.assertEqual(self.client.post(self.url, {"file": self.file()}, format="multipart").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/schedules/attachments/{attachment.pk}/").status_code, 404)
        self.assertTrue(HandoutAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
