from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from schedules.models import AsyncJob, GoogleIntegration
from schedules.tasks import export_google_sheet


class GoogleSheetsDeliveryTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sheets-delivery-fixture")
        GoogleIntegration.objects.create(
            user=self.user, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_http_failure_does_not_store_sheet_id_or_external_error(self, token):
        job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )
        spreadsheet_id = "private-spreadsheet-id"
        external_error = requests.Timeout(f"timed out while writing {spreadsheet_id}")

        with (
            patch("schedules.tasks.requests.put", side_effect=external_error),
            patch.object(export_google_sheet, "retry", side_effect=Retry()) as retry,
        ):
            with self.assertRaises(Retry):
                export_google_sheet.run(str(job.pk), self.user.pk, spreadsheet_id, "Characters!A1", [])

        job.refresh_from_db()
        self.assertEqual(
            job.error,
            "Google Sheets APIとの通信に失敗しました。連携状態と出力先を確認して再試行してください。",
        )
        self.assertNotIn(spreadsheet_id, job.error)
        self.assertNotIn(str(external_error), job.error)
        retry_error = retry.call_args.kwargs["exc"]
        self.assertEqual(str(retry_error), job.error)
        self.assertNotIn(spreadsheet_id, str(retry_error))

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_invalid_response_finishes_job_without_exposing_response_body(self, token):
        for value in (None, [], "private response content", 42, ValueError("private response content")):
            with self.subTest(value=type(value).__name__):
                job = AsyncJob.objects.create(
                    owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
                )
                response = Mock()
                response.raise_for_status.return_value = None
                if isinstance(value, Exception):
                    response.json.side_effect = value
                else:
                    response.json.return_value = value
                with patch("schedules.tasks.requests.put", return_value=response) as put:
                    result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "Characters!A1", [])
                self.assertEqual(result, "invalid-response")
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertIsNotNone(job.finished_at)
                self.assertEqual(
                    job.error, "Google Sheetsの応答形式を確認できません。出力先を確認して再試行してください。"
                )
                put.assert_called_once()
