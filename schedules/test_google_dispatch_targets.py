from contextlib import ExitStack
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from schedules import test_google_job_target_guard as target_tests
from schedules.models import AsyncJob, GoogleCalendarSync, TRPGSession
from schedules.tasks import export_google_sheet, sync_google_calendar


class GoogleDispatchTargetsTest(TestCase):
    setUp = target_tests.GoogleJobTargetGuardTest.setUp
    _restore_connection = target_tests.GoogleJobTargetGuardTest._restore_connection
    _job = target_tests.GoogleJobTargetGuardTest._job
    _sends = target_tests.GoogleJobTargetGuardTest._sends
    response = target_tests.GoogleJobTargetGuardTest.response
    event_response = target_tests.GoogleJobTargetGuardTest.event_response
    message = "ジョブの処理対象が一致しません。連携設定から新しく実行してください。"

    def _refuse(self, job, invoke, expected="invalid-target"):
        before = list(GoogleCalendarSync.objects.order_by("pk").values())
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            calendar_retry = stack.enter_context(patch.object(sync_google_calendar, "retry"))
            sheets_retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
            self.assertEqual(invoke(), expected)
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
            calendar_retry.assert_not_called()
            sheets_retry.assert_not_called()
        self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), before)
        job.refresh_from_db()
        if expected == "invalid-target":
            self.assertEqual(job.status, AsyncJob.Status.FAILED)
            self.assertEqual(job.error, self.message)
            self.assertIsNotNone(job.finished_at)

    def test_calendar_different_same_owner_sync_never_updates_or_deletes(self):
        other_session = TRPGSession.objects.create(
            title="別の非公開同期対象", gm=self.user, group=self.session.group, date=timezone.now()
        )
        other_sync = GoogleCalendarSync.objects.create(
            user=self.user, session=other_session, external_event_id="another-private-event"
        )
        for cancelling in (False, True):
            with self.subTest(cancelling=cancelling):
                other_session.status = "cancelled" if cancelling else "planned"
                other_session.save(update_fields=["status"])
                job = self._job("calendar")
                self._refuse(job, lambda: sync_google_calendar.run(other_sync.pk, str(job.pk)))

    def test_calendar_missing_malformed_target_is_not_dispatched(self):
        for target in (None, True, False, "1", [], {}, 1.0, 0, -1):
            with self.subTest(target=target):
                job = self._job("calendar")
                job.payload["sync_id"] = target
                job.save(update_fields=["payload"])
                self._refuse(job, lambda: sync_google_calendar.run(self.sync.pk, str(job.pk)))

    def test_calendar_nonexistent_or_malformed_dispatch_returns_without_mutation(self):
        for sync_id in (None, True, "invalid", [], {}, 0, -1, self.sync.pk + 9999):
            with self.subTest(sync_id=sync_id):
                job = self._job("calendar")
                before = AsyncJob.objects.filter(pk=job.pk).values().get()
                self._refuse(job, lambda: sync_google_calendar.run(sync_id, str(job.pk)), "invalid-job")
                self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)

    def test_sheets_destination_or_range_mismatch_never_writes(self):
        for sheet, cell in (("another-private-sheet", "Characters!A1"), ("isolated-sheet", "Another!B2")):
            with self.subTest(sheet=sheet, cell=cell):
                job = self._job("sheets")
                self._refuse(job, lambda: export_google_sheet.run(str(job.pk), self.user.pk, sheet, cell, []))

    def test_sheets_missing_or_malformed_saved_target_never_writes(self):
        for field in ("spreadsheet_id", "range"):
            for value in (None, True, [], {}, "", "another-target"):
                with self.subTest(field=field, value=value):
                    job = self._job("sheets")
                    job.payload[field] = value
                    job.save(update_fields=["payload"])
                    self._refuse(
                        job,
                        lambda: export_google_sheet.run(
                            str(job.pk), self.user.pk, "isolated-sheet", "Characters!A1", []
                        ),
                    )

    def test_sheets_normalized_equivalent_destination_still_delivers(self):
        job = self._job("sheets")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(
                export_google_sheet.run(str(job.pk), self.user.pk, " isolated-sheet ", "Characters!$a$1:B5", []),
                "exported",
            )
        sends["put"].assert_called_once()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
