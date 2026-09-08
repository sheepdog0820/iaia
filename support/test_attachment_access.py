import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from support.admin import SupportMessageInline
from support.models import SupportMessage, SupportTicket


class SupportAttachmentAccessTests(TestCase):
    def test_cloudfront_policy_denies_support_attachments(self):
        source = (Path(__file__).resolve().parents[1] / "infrastructure/terraform/main.tf").read_text(encoding="utf-8")
        deny = source.split('Sid       = "DenyPublicPrivateMediaDownloads"', 1)[1].split("Condition =", 1)[0]
        self.assertIn('"${aws_s3_bucket.assets.arn}/support/line/*"', deny)
        self.assertIn('"${aws_s3_bucket.assets.arn}/*/support/line/*"', deny)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username="support-reader", is_staff=True)
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="support", codename__in=["view_supportticket", "view_supportmessage"]
            )
        )
        ticket = SupportTicket.objects.create(subject="添付試験", line_user_id="synthetic")
        self.message = SupportMessage.objects.create(
            ticket=ticket,
            kind="image",
            line_message_id="synthetic-attachment",
            attachment=ContentFile(b"private-support-content", name="receipt.txt"),
        )

    def paths(self):
        return [
            reverse("support-attachment-download", args=[self.message.pk]),
            "/media/" + self.message.attachment.name,
            "/media/other/../" + self.message.attachment.name,
        ]

    def test_authorized_staff_downloads_without_public_cache(self):
        self.client.force_login(self.user)
        for path in self.paths():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), b"private-support-content")
                self.assertIn("no-store", response["Cache-Control"])
                self.assertIn("private", response["Cache-Control"])
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response["Content-Type"], "application/octet-stream")
                self.assertIn("Cookie", response["Vary"])
                self.assertTrue(response["Content-Disposition"].startswith("attachment;"))

    def test_change_permissions_also_allow_download(self):
        self.user.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label="support", codename__in=["change_supportticket", "change_supportmessage"]
            )
        )
        self.client.force_login(self.user)
        response = self.client.get(self.paths()[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"private-support-content")

    def test_empty_attachment_and_missing_record_return_404(self):
        self.client.force_login(self.user)
        url = self.paths()[0]
        self.message.attachment = ""
        self.message.save(update_fields=["attachment"])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.message.delete()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_admin_page_uses_protected_download_link(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:support_supportticket_change", args=[self.message.ticket_id]))
        self.assertContains(response, reverse("support-attachment-download", args=[self.message.pk]))
        self.assertContains(response, "添付をダウンロード")
        self.assertNotContains(response, self.message.attachment.url)

    def test_unauthorized_users_cannot_read_even_in_debug(self):
        variants = [None, (False, True, True), (True, False, True), (True, True, False)]
        for index, flags in enumerate(variants):
            self.client.logout()
            if flags:
                staff, active, grant = flags
                actor = get_user_model().objects.create_user(
                    username=f"blocked-{index}", is_staff=staff, is_active=active
                )
                if grant:
                    actor.user_permissions.set(self.user.user_permissions.all())
                self.client.force_login(actor)
            with override_settings(DEBUG=True):
                for path in self.paths():
                    with self.subTest(actor=index, path=path):
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 404)
                        self.assertNotIn(b"private-support-content", response.content)

    def test_both_ticket_and_message_permissions_are_required(self):
        for codename in ("view_supportticket", "view_supportmessage"):
            self.user.user_permissions.set(
                Permission.objects.filter(content_type__app_label="support", codename=codename)
            )
            self.client.force_login(self.user)
            self.assertEqual(self.client.get(self.paths()[0]).status_code, 404)

    def test_missing_file_returns_404(self):
        self.client.force_login(self.user)
        with patch.object(self.message.attachment.storage, "open", side_effect=FileNotFoundError):
            self.assertEqual(self.client.get(self.paths()[0]).status_code, 404)

    def test_inline_links_to_authorized_route_not_storage(self):
        inline = SupportMessageInline(SupportTicket, admin.site)
        self.assertIn("attachment", inline.exclude)
        html = str(inline.attachment_download(self.message))
        self.assertIn(reverse("support-attachment-download", args=[self.message.pk]), html)
        self.assertNotIn(self.message.attachment.url, html)
        self.assertIn("添付をダウンロード", html)
        self.message.attachment = ""
        self.assertEqual(inline.attachment_download(self.message), "添付なし")
