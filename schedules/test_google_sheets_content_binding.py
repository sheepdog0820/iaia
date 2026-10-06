import copy
import json
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules import google_job_connection
from schedules import test_google_job_target_guard as target_tests
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.tasks import export_google_sheet


class GoogleSheetsContentBindingTest(TestCase):
    setUp = target_tests.GoogleJobTargetGuardTest.setUp
    _restore_connection = target_tests.GoogleJobTargetGuardTest._restore_connection
    _sends = target_tests.GoogleJobTargetGuardTest._sends
    response = target_tests.GoogleJobTargetGuardTest.response
    event_response = target_tests.GoogleJobTargetGuardTest.event_response
    message = "ジョブ作成時のGoogle Sheets出力内容を確認できません。連携設定から新しく出力してください。"

    def _character(self, name):
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(character_sheet=character, name=name)
        return character

    def _queue(self):
        with patch("schedules.integration_views.queue_google_sheet_export", return_value=True) as queue:
            response = self.api.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": "isolated-content-sheet"},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        queue.assert_called_once()
        return AsyncJob.objects.get(pk=response.data["job_id"]), queue.call_args.args

    def _refuse(self, job, args):
        original_payload = copy.deepcopy(job.payload)
        original_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
            self.assertEqual(export_google_sheet.run(*args), "invalid-values")
            token.assert_not_called()
            retry.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, self.message)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(job.payload, original_payload)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), original_sync)
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["error"], self.message)

    def test_api_stores_opaque_content_binding_without_rows_or_credentials(self):
        self._character("非公開の出力内容フィクスチャ")
        job, args = self._queue()
        self.assertRegex(job.payload.get("google_values", ""), r"^[0-9a-f]{64}$")
        stored = json.dumps(job.payload, ensure_ascii=False)
        for private in (args[-1][1][1], "isolated-token", "delivery-fixture"):
            self.assertNotIn(private, stored)

    def test_changed_rows_headers_or_shape_are_refused_before_token_lookup(self):
        self._character("初回の非公開内容")
        self._character("二番目の非公開内容")
        for change in ("cell", "header", "removed", "added", "order", "none", "dict", "string", "nested"):
            with self.subTest(change=change):
                job, args = self._queue()
                values = copy.deepcopy(args[-1])
                if change == "cell":
                    values[1][1] = "差し替えた非公開内容"
                elif change == "header":
                    values[0][0] = "wrong-header"
                elif change == "removed":
                    values.pop()
                elif change == "added":
                    values.append(values[1])
                elif change == "order":
                    values[1:] = reversed(values[1:])
                elif change == "nested":
                    values[1][1] = {"private": "nested"}
                else:
                    values = {"none": None, "dict": {}, "string": "private"}[change]
                self._refuse(job, (*args[:-1], values))

    def test_missing_or_malformed_saved_binding_is_not_rebuilt_from_queue(self):
        for value in (None, [], {}, True, "wrong", "f" * 64):
            with self.subTest(value=value):
                job, args = self._queue()
                job.payload["google_values"] = value
                job.save(update_fields=["payload"])
                self._refuse(job, args)
        job, args = self._queue()
        job.payload.pop("google_values", None)
        job.save(update_fields=["payload"])
        self._refuse(job, args)

    def test_unchanged_empty_and_populated_api_jobs_deliver_exact_rows(self):
        for populated in (False, True):
            with self.subTest(populated=populated), ExitStack() as stack:
                if populated:
                    self._character("=1+1 日本語の保持")
                job, args = self._queue()
                sends, _ = self._sends(stack)
                self.assertEqual(export_google_sheet.run(*args), "exported")
                self.assertEqual(sends["put"].call_args.kwargs["json"]["values"], args[-1])
                self.assertEqual(sends["put"].call_args.kwargs["params"], {"valueInputOption": "RAW"})
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_retry_seals_current_owned_rows_without_expanding_original_selection(self):
        character = self._character("以前の内容")
        first, _ = self._queue()
        first.mark_failed("以前の出力失敗")
        CharacterSheet7th.objects.filter(character_sheet=character).update(name="再試行時の内容")
        self._character("後から追加した対象外")
        with patch("schedules.job_views.queue_google_sheet_export", return_value=True) as queue:
            response = self.api.post(reverse("async-job-retry", kwargs={"pk": first.pk}))
        self.assertEqual(response.status_code, 202)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        self.assertRegex(job.payload.get("google_values", ""), r"^[0-9a-f]{64}$")
        self.assertNotEqual(job.payload.get("google_values"), first.payload.get("google_values"))
        values = queue.call_args.args[-1]
        self.assertEqual([row[0] for row in values[1:]], [character.pk])
        self.assertEqual(values[1][1], "再試行時の内容")
        with ExitStack() as stack:
            self._sends(stack)
            self.assertEqual(export_google_sheet.run(*queue.call_args.args), "exported")

    def test_binding_rejects_non_table_non_scalar_and_non_finite_values(self):
        binding = getattr(google_job_connection, "google_sheet_values_binding", None)
        self.assertIsNotNone(binding)
        for value in (None, {}, "private", [1], [[{}]], [[[]]], [[float("nan")]], [[float("inf")]], [["\ud800"]]):
            with self.subTest(value=repr(value)):
                self.assertIsNone(binding(value))
        self.assertRegex(binding([["日本語", None, True, 1, 1.5]]), r"^[0-9a-f]{64}$")
        first = binding([["日本語"]])
        with override_settings(SECRET_KEY="synthetic-values-signing-key"):  # nosec B106
            self.assertNotEqual(first, binding([["日本語"]]))

    def test_content_matcher_refuses_non_mapping_payload(self):
        matcher = getattr(google_job_connection, "google_job_values_match", None)
        self.assertIsNotNone(matcher)
        self.assertFalse(matcher(SimpleNamespace(payload=[]), [["row"]]))
