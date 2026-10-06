import json
from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, unquote, urlsplit

import requests
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from schedules.google_job_connection import google_connection_binding
from schedules.google_sheets import SHEET_COLUMNS
from schedules.models import AsyncJob, GoogleIntegration
from schedules.tasks import export_google_sheet


class GoogleSheetsDestinationTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="sheets-destination-fixture")
        account = SocialAccount.objects.create(user=self.user, provider="google", uid="sheets-destination-fixture")
        SocialToken.objects.create(account=account, token="isolated-token")  # Isolated fixture. # nosec B106
        GoogleIntegration.objects.create(
            user=self.user, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )
        self.client.force_authenticate(self.user)

    def _job(self):
        return AsyncJob.objects.create(
            owner=self.user,
            job_type="google_sheets_export",
            expires_at=timezone.now() + timedelta(days=1),
            payload={"google_connection": google_connection_binding(GoogleIntegration.objects.get(user=self.user))},
        )

    @patch("schedules.tasks.get_google_access_token", return_value="isolated-token")
    def test_prepared_requests_preserve_each_destination_component(self, token):
        # These are transport fixtures, not a claim that Google accepts every title/ID.
        destinations = (
            ("fixture-sheet", "'調査#2'!B7"),
            ("fixture-sheet", "'Jon''s_Data %25'!B7"),
            ("fixture-sheet", "'sheet?valueInputOption=USER_ENTERED&key=x'!B7"),
            ("fixture-sheet", "'path/../sheet'!B7"),
            ("fixture/id?key=x#fragment", "Characters!B7"),
            ("fixture%2Fid", "Characters!B7"),
        )
        values = [["=SUM(A1:A3)", row] for row in range(101)]
        for spreadsheet_id, range_name in destinations:
            with self.subTest(spreadsheet_id=spreadsheet_id, range_name=range_name):
                job = self._job()
                prepared = []

                def put(url, **kwargs):
                    prepared.append(
                        requests.Request(
                            "PUT", url, params=kwargs["params"], headers=kwargs["headers"], json=kwargs["json"]
                        ).prepare()
                    )
                    response = Mock()
                    response.json.return_value = {"updatedCells": len(kwargs["json"]["values"]) * 2}
                    return response

                with patch("schedules.tasks.requests.put", side_effect=put):
                    result = export_google_sheet.run(str(job.pk), self.user.pk, spreadsheet_id, range_name, values)
                self.assertEqual(result, "exported")
                self.assertEqual(len(prepared), 2)
                for index, request in enumerate(prepared):
                    parsed = urlsplit(request.url)
                    self.assertEqual((parsed.scheme, parsed.netloc), ("https", "sheets.googleapis.com"))
                    self.assertEqual(parsed.fragment, "")
                    self.assertEqual(parse_qs(parsed.query), {"valueInputOption": ["RAW"]})
                    parts = parsed.path.split("/")
                    self.assertEqual(len(parts), 6)
                    self.assertEqual(parts[:3], ["", "v4", "spreadsheets"])
                    self.assertEqual(parts[4], "values")
                    self.assertEqual(unquote(parts[3]), spreadsheet_id)
                    self.assertEqual(unquote(parts[5]), range_name.replace("!B7", f"!B{7 + index * 100}"))
                    self.assertEqual(request.headers["Authorization"], "Bearer isolated-token")
                    self.assertIn(b"=SUM(A1:A3)", request.body)
                job.refresh_from_db()
                self.assertEqual(job.result["spreadsheet_id"], spreadsheet_id)
                self.assertEqual(job.result["range"], range_name)
                self.assertEqual(job.result["updated_cells"], 202)

    @patch("schedules.integration_views.queue_google_sheet_export", return_value=True)
    def test_api_rejects_invalid_ids_without_job_or_queue(self, queue):
        for value in (
            {},
            [],
            True,
            False,
            42,
            ".",
            "..",
            "private\x00id",
            "private\nid",
            "private\x7fid",
            "private\ud800id",
        ):
            with self.subTest(value=repr(value)):
                response = self.client.post(
                    "/api/character-sheets/google-sheets/export/",
                    json.dumps({"spreadsheet_id": value}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["spreadsheet_id"], ["出力先のスプレッドシートIDを正しく指定してください。"]
                )
                self.assertFalse(AsyncJob.objects.exists())
                queue.assert_not_called()

    @patch("schedules.integration_views.queue_google_sheet_export", return_value=True)
    def test_empty_id_keeps_preview_without_queue(self, queue):
        for payload in ({}, {"spreadsheet_id": None}, {"spreadsheet_id": ""}, {"spreadsheet_id": " \t "}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/character-sheets/google-sheets/export/", payload, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, {"columns": SHEET_COLUMNS, "rows": []})
                self.assertFalse(AsyncJob.objects.exists())
                queue.assert_not_called()

    @patch("schedules.integration_views.queue_google_sheet_export", return_value=True)
    def test_api_passes_normalized_id_and_range_to_job_and_queue(self, queue):
        response = self.client.post(
            "/api/character-sheets/google-sheets/export/",
            {"spreadsheet_id": " fixture-sheet ", "range": "'調査#2'!$b$7:C20"},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        self.assertEqual(job.payload["spreadsheet_id"], "fixture-sheet")
        self.assertEqual(job.payload["range"], "'調査#2'!B7")
        queue.assert_called_once_with(str(job.pk), self.user.pk, "fixture-sheet", "'調査#2'!B7", [SHEET_COLUMNS])

    def test_worker_rejects_legacy_invalid_id_before_token_or_delivery(self):
        for value in (
            None,
            "",
            " \t ",
            {},
            [],
            True,
            42,
            ".",
            "..",
            "private\x00id",
            "private\nid",
            "private\x7fid",
            "private\ud800id",
        ):
            with self.subTest(value=repr(value)):
                job = self._job()
                with (
                    patch("schedules.tasks.get_google_access_token", return_value="isolated-token") as token,
                    patch("schedules.tasks.requests.put") as put,
                    patch.object(export_google_sheet, "retry") as retry,
                ):
                    result = export_google_sheet.run(str(job.pk), self.user.pk, value, "A1", [])
                job.refresh_from_db()
                self.assertEqual(result, "invalid-spreadsheet")
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(job.error, "出力先のスプレッドシートIDを正しく指定してください。")
                self.assertIsNotNone(job.finished_at)
                token.assert_not_called()
                put.assert_not_called()
                retry.assert_not_called()

    def test_worker_validates_range_before_token_refresh(self):
        job = self._job()
        with (
            patch("schedules.tasks.get_google_access_token", return_value="isolated-token") as token,
            patch("schedules.tasks.requests.put") as put,
        ):
            result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", "NamedRange", [])
        self.assertEqual(result, "invalid-range")
        token.assert_not_called()
        put.assert_not_called()

    def test_invalid_unicode_range_fails_before_refresh_or_delivery(self):
        range_name = "'private\ud800sheet'!A1"
        with patch("schedules.integration_views.queue_google_sheet_export") as queue:
            response = self.client.post(
                "/api/character-sheets/google-sheets/export/",
                json.dumps({"spreadsheet_id": "fixture-sheet", "range": range_name}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["range"], ["出力範囲はA1形式で指定してください（例: Characters!A1）。"])
        queue.assert_not_called()
        self.assertFalse(AsyncJob.objects.exists())
        job = self._job()
        with (
            patch("schedules.tasks.get_google_access_token", return_value="isolated-token") as token,
            patch("schedules.tasks.requests.put") as put,
        ):
            result = export_google_sheet.run(str(job.pk), self.user.pk, "fixture-sheet", range_name, [])
        self.assertEqual(result, "invalid-range")
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, "出力範囲はA1形式で指定してください（例: Characters!A1）。")
        token.assert_not_called()
        put.assert_not_called()
