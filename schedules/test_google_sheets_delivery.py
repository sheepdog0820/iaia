from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from schedules.google_sheets import offset_sheet_start_range
from schedules.models import AsyncJob, GoogleIntegration
from schedules.tasks import export_google_sheet


class GoogleSheetsDeliveryTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sheets-delivery-fixture")
        GoogleIntegration.objects.create(
            user=self.user, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_large_export_updates_progress_between_bounded_requests(self, token):
        job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )
        values = [[f"row-{row}", *range(16)] for row in range(205)]
        observed_progress = []
        sent_ranges = []
        sent_row_counts = []

        def put(url, **kwargs):
            job.refresh_from_db()
            observed_progress.append(job.progress)
            sent_ranges.append(url.rsplit("/values/", 1)[1])
            sent_row_counts.append(len(kwargs["json"]["values"]))
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"updatedCells": len(kwargs["json"]["values"]) * 17}
            return response

        with patch("schedules.tasks.requests.put", side_effect=put):
            result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "'Large Export'!B7", values)

        job.refresh_from_db()
        self.assertEqual(result, "exported")
        self.assertEqual(sent_ranges, ["'Large Export'!B7", "'Large Export'!B107", "'Large Export'!B207"])
        self.assertEqual(sent_row_counts, [100, 100, 5])
        self.assertEqual(observed_progress, [10, 49, 88])
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
        self.assertEqual(job.progress, 100)
        self.assertEqual(job.result["updated_cells"], 205 * 17)
        self.assertEqual(job.result["request_count"], 3)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_large_export_failure_preserves_partial_progress_and_safe_reason(self, token):
        job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )
        values = [[f"row-{row}"] for row in range(201)]
        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = {"updatedCells": 100}
        private_error = requests.Timeout("private upstream error for fixture-sheet")

        with (
            patch("schedules.tasks.requests.put", side_effect=[first_response, private_error]) as put,
            patch.object(export_google_sheet, "retry", side_effect=Retry()) as retry,
        ):
            with self.assertRaises(Retry):
                export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "Characters!A1", values)

        job.refresh_from_db()
        self.assertEqual(put.call_count, 2)
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.progress, 49)
        self.assertEqual(
            job.error,
            "Google Sheets APIとの通信に失敗しました。途中まで出力されている可能性があります。"
            "連携状態と出力先を確認して再試行してください。",
        )
        self.assertNotIn(str(private_error), job.error)
        self.assertEqual(str(retry.call_args.kwargs["exc"]), job.error)

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_legacy_invalid_range_fails_before_delivery(self, token):
        job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )

        with patch("schedules.tasks.requests.put") as put:
            result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "NamedRange", [])

        job.refresh_from_db()
        self.assertEqual(result, "invalid-range")
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, "出力範囲はA1形式で指定してください（例: Characters!A1）。")
        put.assert_not_called()

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_invalid_updated_cells_response_is_not_exposed(self, token):
        job = AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", expires_at=timezone.now() + timedelta(days=1)
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"updatedCells": "private response content"}

        with patch("schedules.tasks.requests.put", return_value=response):
            result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "Characters!A1", [[]])

        job.refresh_from_db()
        self.assertEqual(result, "invalid-response")
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, "Google Sheetsの応答形式を確認できません。出力先を確認して再試行してください。")
        self.assertNotIn("private response content", job.error)

    def test_range_offset_rejects_invalid_inputs(self):
        message = "出力範囲はA1形式で指定してください（例: Characters!A1）。"
        with self.assertRaisesMessage(ValueError, message):
            offset_sheet_start_range("!A1", 0)
        with self.assertRaisesMessage(ValueError, "row_offset must not be negative"):
            offset_sheet_start_range("Characters!A1", -1)

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
