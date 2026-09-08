from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from schedules.attachment_service import HandoutAttachmentPermissionError, HandoutAttachmentService
from schedules.attachment_views import HandoutAttachmentDetailView, HandoutAttachmentListCreateView


class AttachmentErrorPrivacyTests(SimpleTestCase):
    def upload_failure(self, error):
        request = APIRequestFactory().post("/attachments/", {}, format="multipart")
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        with (
            patch("schedules.attachment_views.get_object_or_404"),
            patch("schedules.attachment_views.HandoutAttachmentService.upload_attachment", side_effect=error),
        ):
            return HandoutAttachmentListCreateView.as_view()(request, handout_id=1)

    def test_internal_failures_do_not_disclose_exception_details(self):
        for error in (
            OSError("private-storage-path"),
            RuntimeError("internal-database-detail"),
            PermissionError("private-filesystem-permission-detail"),
        ):
            with self.subTest(error=type(error).__name__):
                with self.assertLogs("schedules.attachment_views", level="ERROR") as logs:
                    response = self.upload_failure(error)
                self.assertIsNotNone(logs.records[0].exc_info)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(
                    response.data,
                    {"error": "添付ファイルの保存に失敗しました。時間をおいて再度お試しください。"},
                )
                self.assertNotIn(str(error), str(response.data))

    def test_validation_failure_remains_an_actionable_bad_request(self):
        response = self.upload_failure(ValidationError("ファイルサイズの上限を超えています。"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("ファイルサイズの上限を超えています。", response.data["error"])

    def test_permission_failure_remains_forbidden(self):
        response = self.upload_failure(HandoutAttachmentPermissionError("GMのみが添付ファイルを操作できます。"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "GMのみが添付ファイルを操作できます。")

    def test_anonymous_attachment_access_uses_public_permission_error(self):
        with self.assertRaises(HandoutAttachmentPermissionError):
            HandoutAttachmentService()._require_access(SimpleNamespace(), SimpleNamespace(id=None))

    def test_upload_service_rejects_non_gm_before_handling_file(self):
        with self.assertRaises(HandoutAttachmentPermissionError):
            HandoutAttachmentService().upload_attachment(
                handout=SimpleNamespace(session=SimpleNamespace(gm_id=1)),
                file=None,
                uploaded_by=SimpleNamespace(id=2),
            )

    def test_delete_service_rejects_non_owner(self):
        attachment = SimpleNamespace(handout=SimpleNamespace(session=SimpleNamespace(gm_id=1)), uploaded_by_id=1)
        with patch("schedules.attachment_service.HandoutAttachment.objects") as attachments:
            attachments.select_related.return_value.filter.return_value.first.return_value = attachment
            with self.assertRaises(HandoutAttachmentPermissionError):
                HandoutAttachmentService().delete_attachment(1, SimpleNamespace(id=2))

    def test_delete_api_returns_only_application_permission_message(self):
        request = APIRequestFactory().delete("/attachments/1/")
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        with (
            patch("schedules.attachment_views.HandoutAttachment.objects"),
            patch("schedules.attachment_views._user_can_view_handout", return_value=True),
            patch(
                "schedules.attachment_views.HandoutAttachmentService.delete_attachment",
                side_effect=HandoutAttachmentPermissionError("この添付ファイルを削除する権限がありません。"),
            ),
        ):
            response = HandoutAttachmentDetailView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"], "この添付ファイルを削除する権限がありません。")
