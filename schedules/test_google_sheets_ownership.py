import copy
from contextlib import ExitStack
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules import test_google_sheets_content_binding as content_tests
from schedules.google_job_connection import google_sheet_values_binding
from schedules.google_sheets import SHEET_COLUMNS, sheet_export_character_ids
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.tasks import export_google_sheet
from tests.utils.google_sheet_fixtures import run_sheet_fixture


class GoogleSheetsOwnershipTest(TestCase):
    setUp = content_tests.GoogleSheetsContentBindingTest.setUp
    _restore_connection = content_tests.GoogleSheetsContentBindingTest._restore_connection
    _sends = content_tests.GoogleSheetsContentBindingTest._sends
    response = content_tests.GoogleSheetsContentBindingTest.response
    event_response = content_tests.GoogleSheetsContentBindingTest.event_response
    _character = content_tests.GoogleSheetsContentBindingTest._character
    _queue = content_tests.GoogleSheetsContentBindingTest._queue
    changed_message = (
        "出力対象のキャラクターが削除されたか、所有者が変更されました。連携設定から新しく出力してください。"
    )
    selection_message = "ジョブ作成時の出力対象を確認できません。連携設定から新しく出力してください。"
    partial_message = "途中まで出力されている可能性があります。出力先を確認してください。"

    def _change(self, character, reason):
        selected = CharacterSheet.objects.filter(pk=character.pk)
        if reason == "deleted":
            selected.delete()
        else:
            selected.update(user=self.other)

    def _assert_finished(self, job, message):
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, message)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(job.result, {})
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["error"], message)

    def _refuse(self, job, args, result="characters-changed", message=None):
        before = copy.deepcopy(job.payload)
        sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
            self.assertEqual(export_google_sheet.run(*args), result)
            token.assert_not_called()
            retry.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self._assert_finished(job, message or self.changed_message)
        self.assertEqual(job.payload, before)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync)

    def test_deleted_or_transferred_selection_is_refused_before_token(self):
        for reason in ("deleted", "transferred"):
            with self.subTest(reason=reason):
                character = self._character("待機中の非公開内容")
                job, args = self._queue()
                self._change(character, reason)
                self._refuse(job, args)

    def test_selection_change_during_refresh_prevents_first_send(self):
        for reason in ("deleted", "transferred"):
            with self.subTest(reason=reason), ExitStack() as stack:
                character = self._character("token更新中の非公開内容")
                job, args = self._queue()
                sends, token = self._sends(stack)

                def read(user):
                    self._change(character, reason)
                    return "isolated-token"

                token.side_effect = read
                retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
                self.assertEqual(export_google_sheet.run(*args), "characters-changed")
                for send in sends.values():
                    send.assert_not_called()
                retry.assert_not_called()
                self._assert_finished(job, self.changed_message)
                self.assertEqual(job.progress, 10)

    def test_change_between_chunks_stops_remaining_writes_and_keeps_partial_notice(self):
        for reason in ("deleted", "transferred"):
            for already_sent in (False, True):
                with self.subTest(reason=reason, already_sent=already_sent), ExitStack() as stack:
                    characters = [self._character(f"分割送信の非公開内容 {index}") for index in range(200)]
                    job, args = self._queue()
                    sends, _ = self._sends(stack)
                    selected = characters[0] if already_sent else characters[-1]

                    def put(url, **kwargs):
                        self._change(selected, reason)
                        return self.response(200, {"updatedCells": 1700})

                    sends["put"].side_effect = put
                    retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
                    self.assertEqual(export_google_sheet.run(*args), "characters-changed")
                    sends["put"].assert_called_once()
                    self.assertEqual(sends["put"].call_args.kwargs["json"]["values"], args[-1][:100])
                    for method in ("get", "post", "delete"):
                        sends[method].assert_not_called()
                    retry.assert_not_called()
                    self._assert_finished(job, self.changed_message + self.partial_message)
                    self.assertEqual(job.progress, 49)
                    CharacterSheet.objects.filter(user=self.user).delete()

    def test_saved_selection_must_be_strict_unique_ordered_ids_matching_table(self):
        first = self._character("最初の対象")
        second = self._character("二番目の対象")
        invalid_ids = (
            None,
            {},
            "1",
            [True],
            [False],
            [0],
            [-1],
            [2**63],
            [str(first.pk)],
            [1.0],
            [],
            [first.pk, first.pk],
            [second.pk, first.pk],
            [first.pk],
        )
        for ids in invalid_ids:
            with self.subTest(ids=ids):
                job, args = self._queue()
                job.payload["character_ids"] = ids
                job.save(update_fields=["payload"])
                self._refuse(job, args, "invalid-selection", self.selection_message)
        for snapshot in (None, False, 1, "true", [], {}):
            with self.subTest(snapshot=snapshot):
                job, args = self._queue()
                job.payload["selection_snapshot"] = snapshot
                job.save(update_fields=["payload"])
                self._refuse(job, args, "invalid-selection", self.selection_message)
        for field in ("selection_snapshot", "character_ids"):
            job, args = self._queue()
            job.payload.pop(field)
            job.save(update_fields=["payload"])
            self._refuse(job, args, "invalid-selection", self.selection_message)

    def test_sealed_non_export_table_is_not_a_character_selection(self):
        character = self._character("確定済みの非公開内容")
        for values in (
            [],
            [["wrong-header"]],
            [SHEET_COLUMNS, []],
            [SHEET_COLUMNS, [character.pk]],
            [SHEET_COLUMNS, [True] + [""] * 16],
        ):
            with self.subTest(values=values):
                job, args = self._queue()
                job.payload["google_values"] = google_sheet_values_binding(values)
                job.save(update_fields=["payload"])
                self._refuse(job, (*args[:-1], values), "invalid-selection", self.selection_message)

    def test_unchanged_ownership_preserves_initial_snapshot_not_current_name(self):
        character = self._character("=1+1 初回の名前")
        job, args = self._queue()
        CharacterSheet7th.objects.filter(character_sheet=character).update(name="更新後の名前")
        self._character("後から追加した対象外")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(export_google_sheet.run(*args), "exported")
            self.assertEqual(sends["put"].call_args.kwargs["json"]["values"], args[-1])
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_selection_parser_handles_non_mapping_and_non_table_boundary(self):
        payload = {"selection_snapshot": True, "character_ids": []}
        for invalid in (None, [], "private"):
            self.assertIsNone(sheet_export_character_ids(invalid, [SHEET_COLUMNS]))
        for values in (None, {}, "private", [SHEET_COLUMNS, "private"], [SHEET_COLUMNS, [1.0] + [""] * 16]):
            self.assertIsNone(sheet_export_character_ids(payload, values))
        self.assertEqual(sheet_export_character_ids(payload, [SHEET_COLUMNS]), [])

    def test_transport_fixture_builds_owned_rows_without_relaxing_worker(self):
        for rows in ([], [["old-header"], []], [["old-header"], ["=1+1 日本語"]]):
            with self.subTest(rows=rows), ExitStack() as stack:
                job, args = self._queue()
                sends, _ = self._sends(stack)
                self.assertEqual(run_sheet_fixture(*args[:-1], rows), "exported")
                actual = sends["put"].call_args.kwargs["json"]["values"]
                job.refresh_from_db()
                self.assertEqual(actual[0], SHEET_COLUMNS)
                self.assertEqual(len(actual), max(1, len(rows)))
                self.assertEqual([row[0] for row in actual[1:]], job.payload["character_ids"])
                self.assertTrue(all(len(row) == 17 for row in actual))
                self.assertEqual(
                    CharacterSheet.objects.filter(user=self.user, pk__in=job.payload["character_ids"]).count(),
                    len(actual) - 1,
                )
                if rows:
                    self.assertEqual(actual[1][1], "=1+1 日本語" if rows[1] else "合成配送試験")

    def test_retry_rebuilds_only_still_owned_original_selection_including_zero(self):
        first = self._character("失効する対象")
        remaining = self._character("残る対象")
        job, _ = self._queue()
        self._change(first, "transferred")
        self._character("後から追加した対象外")
        for empty in (False, True):
            with self.subTest(empty=empty):
                job.mark_failed("失効した出力")
                if empty:
                    self._change(remaining, "deleted")
                with patch("schedules.job_views.queue_google_sheet_export", return_value=True) as queue:
                    response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                self.assertEqual(response.status_code, 202)
                retry_job = AsyncJob.objects.get(pk=response.data["job_id"])
                self.assertEqual(retry_job.payload["character_ids"], [] if empty else [remaining.pk])
                with ExitStack() as stack:
                    sends, _ = self._sends(stack)
                    self.assertEqual(export_google_sheet.run(*queue.call_args.args), "exported")
                    self.assertEqual(sends["put"].call_args.kwargs["json"]["values"], queue.call_args.args[-1])
