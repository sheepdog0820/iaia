"""All five producers seal their authorized acceptance before delivery."""

from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import GroupMembership
from schedules import google_write_intake as intake
from schedules import tasks
from schedules.google_write_ledger import (
    INVALID_ADMISSION_MESSAGE,
    InvalidGoogleWriteAdmission,
    calendar_session_target_key,
    open_google_write_snapshot,
    sheet_target_key,
)
from schedules.integration_access import visible_user_sessions
from schedules.models import (
    AsyncJob,
    GoogleCalendarSync,
    GoogleIntegration,
    GoogleJobDispatch,
    GoogleWriteAdmission,
    GoogleWriteReservation,
    GoogleWriteTarget,
)
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleWriteIntakeTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _invoke(self, route):
        if route.startswith("retry-"):
            original, _ = self._queue(route.removeprefix("retry-"))
            original.mark_failed("元の合成ジョブの失敗")
            return lambda: self.api.post(reverse("async-job-retry", kwargs={"pk": original.pk}))
        if route == "calendar":
            return lambda: self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        if route == "sheets":
            return lambda: self.api.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": "intake-shared-sheet"},
                format="json",
            )
        return lambda: tasks.schedule_session_google_syncs(self.session)

    def test_all_five_real_producers_commit_admission_and_outbox_even_when_callback_is_lost(self):
        for route in self.routes:
            with self.subTest(route=route):
                invoke = self._invoke(route)
                with patch("django.db.transaction.on_commit"):
                    response = invoke()
                job = AsyncJob.objects.first()
                if response is not None:
                    self.assertEqual(response.status_code, 202)
                    self.assertNotIn("admission", str(response.data))
                row = GoogleWriteAdmission.objects.get(job=job)
                snapshot = open_google_write_snapshot(row)
                self.assertEqual(snapshot["kind"], job.job_type)
                self.assertEqual(snapshot["google_connection"], job.payload["google_connection"])
                self.assertTrue(job.google_dispatch.ciphertext)
                if self._mode(route) == "calendar":
                    self.assertEqual(snapshot["sync"]["id"], self.sync.pk)
                    self.assertEqual(snapshot["calendar"]["event"]["summary"], self.session.title)
                    self.assertTrue(
                        row.reservations.filter(
                            target_id=calendar_session_target_key(self.user.pk, self.session.pk)
                        ).exists()
                    )
                    self.assertEqual(row.reservations.count(), 2)
                else:
                    self.assertEqual(snapshot["sheets"]["spreadsheet_id"], job.payload["spreadsheet_id"])
                    self.assertEqual(snapshot["sheets"]["range"], job.payload["range"])
                    self.assertEqual(row.reservations.get().target_id, sheet_target_key(job.payload["spreadsheet_id"]))

    def test_mocking_only_delivery_cannot_hide_admission_in_any_producer(self):
        for route in self.routes:
            with self.subTest(route=route):
                invoke = self._invoke(route)
                prefix = (
                    "tasks"
                    if route == "session"
                    else "job_views" if route.startswith("retry-") else "integration_views"
                )
                name = "queue_google_sheet_export" if self._mode(route) == "sheets" else "queue_google_calendar_sync"
                with patch(f"schedules.{prefix}.{name}", return_value=True) as queue:
                    response = invoke()
                self.assertEqual(queue.call_count, 1)
                job = AsyncJob.objects.first()
                self.assertTrue(GoogleWriteAdmission.objects.filter(job=job).exists())
                if response is not None:
                    self.assertEqual(response.status_code, 202)

    def test_outer_and_savepoint_rollback_leave_no_admission_sequence_or_delivery_from_all_routes(self):
        for route in self.routes:
            for nested in (False, True):
                with self.subTest(route=route, nested=nested), ExitStack() as stack:
                    invoke = self._invoke(route)
                    before = [
                        list(model.objects.values())
                        for model in (
                            AsyncJob,
                            GoogleWriteTarget,
                            GoogleWriteAdmission,
                            GoogleWriteReservation,
                            GoogleCalendarSync,
                        )
                    ]
                    callback = stack.enter_context(patch("django.db.transaction.on_commit"))
                    with transaction.atomic():
                        with transaction.atomic():
                            invoke()
                            if nested:
                                transaction.set_rollback(True)
                        if not nested:
                            transaction.set_rollback(True)
                    after = [
                        list(model.objects.values())
                        for model in (
                            AsyncJob,
                            GoogleWriteTarget,
                            GoogleWriteAdmission,
                            GoogleWriteReservation,
                            GoogleCalendarSync,
                        )
                    ]
                    self.assertEqual(after, before)
                    callback.assert_called_once()

    def test_calendar_snapshot_does_not_change_with_later_session_or_sync_updates(self):
        with patch("django.db.transaction.on_commit"):
            response = self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        row = GoogleWriteAdmission.objects.get(job_id=response.data["job_id"])
        accepted = open_google_write_snapshot(row)
        self.session.title = "後から変更された非公開本文"
        self.session.status = "cancelled"
        self.session.save(update_fields=["title", "status"])
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(external_event_id="later-external-id")
        self.assertEqual(open_google_write_snapshot(row), accepted)
        self.assertNotIn("後から変更された非公開本文", row.ciphertext)
        self.assertNotIn("後から変更された非公開本文", str(row.job.payload))

    def test_mid_intake_failure_rolls_back_all_five_producers_before_delivery(self):
        for route in self.routes:
            with self.subTest(route=route):
                invoke = self._invoke(route)
                models = (
                    AsyncJob,
                    GoogleWriteTarget,
                    GoogleWriteAdmission,
                    GoogleWriteReservation,
                    GoogleCalendarSync,
                    GoogleJobDispatch,
                )
                before = [list(model.objects.values()) for model in models]
                original = intake.register_google_write

                def broken(*args):
                    original(*args)
                    raise RuntimeError("合成の受付保存障害")

                with (
                    patch.object(intake, "register_google_write", side_effect=broken),
                    patch("django.db.transaction.on_commit") as callback,
                ):
                    if route == "session":
                        with self.assertRaisesRegex(RuntimeError, "合成の受付保存障害"):
                            invoke()
                    else:
                        self.assertEqual(invoke().status_code, 500)
                self.assertEqual([list(model.objects.values()) for model in models], before)
                callback.assert_not_called()

    def test_invalid_intake_is_a_fixed_japanese_400_and_rolls_back_api_and_retry(self):
        for route in self.routes[:-1]:
            with self.subTest(route=route):
                invoke = self._invoke(route)
                before = list(AsyncJob.objects.values())
                with patch.object(intake, "register_google_write", side_effect=InvalidGoogleWriteAdmission):
                    response = invoke()
                self.assertEqual(response.status_code, 400)
                self.assertEqual(str(response.data["detail"]), INVALID_ADMISSION_MESSAGE)
                self.assertEqual(list(AsyncJob.objects.values()), before)

    def test_rechecking_scope_enabled_flag_and_active_owner_prevents_admission(self):
        for mode in ("calendar", "sheets"):
            job, args = self._queue(mode)
            for change in ("scope", "disabled", "inactive"):
                with self.subTest(mode=mode, change=change), transaction.atomic():
                    if change == "scope":
                        GoogleIntegration.objects.filter(pk=self.integration.pk).update(scopes=[])
                    elif change == "disabled":
                        GoogleIntegration.objects.filter(pk=self.integration.pk).update(**{f"{mode}_enabled": False})
                    else:
                        type(self.user).objects.filter(pk=self.user.pk).update(is_active=False)
                    with self.assertRaises(InvalidGoogleWriteAdmission):
                        if mode == "calendar":
                            intake.register_calendar_intake(job, self.sync, self.session)
                        else:
                            intake.register_sheets_intake(job, args[-1])
                    transaction.set_rollback(True)

    def test_invalid_internal_source_uses_uniform_rejection_not_attribute_errors(self):
        for source in (None, {}, AsyncJob(payload=[])):
            with self.subTest(source_type=type(source).__name__), self.assertRaises(InvalidGoogleWriteAdmission):
                intake.register_sheets_intake(source, [])

    def test_calendar_visibility_is_rechecked_before_new_intake(self):
        job, _ = self._queue("calendar")
        type(self.session).objects.filter(pk=self.session.pk).update(gm=self.other, created_by=self.other)
        type(self.session.group).objects.filter(pk=self.session.group_id).update(created_by=self.other)
        GroupMembership.objects.filter(user=self.user).delete()
        self.session.participants.remove(self.user)
        self.assertFalse(visible_user_sessions(self.user).filter(pk=self.session.pk).exists())
        with self.assertRaises(InvalidGoogleWriteAdmission):
            intake.register_calendar_intake(job, self.sync, self.session)

    def test_automatic_missing_credentials_or_inactive_owner_skip_without_blocking_session_work(self):
        from allauth.socialaccount.models import SocialToken

        for reason in ("missing-credential", "inactive"):
            with self.subTest(reason=reason), transaction.atomic():
                if reason == "missing-credential":
                    SocialToken.objects.filter(account__user=self.user).delete()
                else:
                    type(self.user).objects.filter(pk=self.user.pk).update(is_active=False)
                before = list(AsyncJob.objects.values())
                tasks.schedule_session_google_syncs(self.session)
                self.assertEqual(list(AsyncJob.objects.values()), before)
                self.assertFalse(GoogleWriteAdmission.objects.exists())
                transaction.set_rollback(True)

    def test_expiration_reports_deleted_jobs_not_their_private_child_rows(self):
        with patch("django.db.transaction.on_commit"):
            response = self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        AsyncJob.objects.filter(pk=response.data["job_id"]).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(tasks.expire_async_jobs(), 1)
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())
        self.assertFalse(GoogleJobDispatch.objects.exists())
        self.assertEqual(GoogleWriteTarget.objects.count(), 2)

    def test_automatic_intake_denial_after_partial_save_leaves_no_delivery_or_sync_changes(self):
        models = (
            AsyncJob,
            GoogleWriteTarget,
            GoogleWriteAdmission,
            GoogleWriteReservation,
            GoogleCalendarSync,
            GoogleJobDispatch,
        )
        before = [list(model.objects.values()) for model in models]
        original = intake.register_google_write

        def denied(*args):
            original(*args)
            raise InvalidGoogleWriteAdmission

        with (
            patch.object(intake, "register_google_write", side_effect=denied),
            patch("django.db.transaction.on_commit") as callback,
            self.assertLogs("schedules.tasks", level="WARNING") as logs,
        ):
            tasks.schedule_session_google_syncs(self.session)
        self.assertEqual([list(model.objects.values()) for model in models], before)
        callback.assert_not_called()
        self.assertEqual(
            logs.output,
            [
                "WARNING:schedules.tasks:Google Calendarの自動同期を受け付けられませんでした。"
                "連携状態と権限を確認してください。"
            ],
        )

    def test_automatic_owner_denial_preserves_the_other_owners_atomic_intake(self):
        from allauth.socialaccount.models import SocialAccount, SocialToken

        account = SocialAccount.objects.create(user=self.other, provider="google", uid="intake-valid-other")
        transport_fixture = "synthetic-intake-transport-material"
        SocialToken.objects.create(account=account, token=transport_fixture)
        GoogleIntegration.objects.create(
            user=self.other, calendar_enabled=True, scopes=[GoogleIntegration.REQUIRED_CALENDAR_SCOPE]
        )
        self.session.participants.add(self.other)
        original = intake.register_google_write
        sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        for rejected, accepted in ((self.user, self.other), (self.other, self.user)):
            with self.subTest(rejected=rejected.pk), transaction.atomic():

                def denied(job, *args):
                    row = original(job, *args)
                    if job.owner_id == rejected.pk:
                        raise InvalidGoogleWriteAdmission
                    return row

                with (
                    patch.object(intake, "register_google_write", side_effect=denied),
                    patch("django.db.transaction.on_commit") as callback,
                    self.assertLogs("schedules.tasks", level="WARNING"),
                ):
                    tasks.schedule_session_google_syncs(self.session)
                job = AsyncJob.objects.get()
                self.assertEqual(job.owner_id, accepted.pk)
                self.assertEqual(GoogleWriteAdmission.objects.get().job_id, job.pk)
                self.assertEqual(GoogleJobDispatch.objects.get().job_id, job.pk)
                self.assertEqual(GoogleWriteTarget.objects.count(), 2)
                self.assertCountEqual(list(GoogleWriteReservation.objects.values_list("sequence", flat=True)), [1, 1])
                self.assertEqual(
                    GoogleCalendarSync.objects.get(user=accepted).status, GoogleCalendarSync.Status.PENDING
                )
                if rejected == self.user:
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
                else:
                    self.assertFalse(GoogleCalendarSync.objects.filter(user=rejected).exists())
                callback.assert_called_once()
                transaction.set_rollback(True)

    def test_session_edit_api_succeeds_when_google_permission_disappears_during_intake(self):
        before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        original = intake.register_calendar_intake

        def revoked(job, sync, session):
            GoogleIntegration.objects.filter(user=self.user).update(calendar_enabled=False)
            return original(job, sync, session)

        with (
            patch.object(tasks, "register_calendar_intake", side_effect=revoked),
            patch.object(tasks, "queue_discord_event"),
            patch("django.db.transaction.on_commit") as callback,
        ):
            response = self.api.patch(
                reverse("session-detail", kwargs={"pk": self.session.pk}),
                {"title": "失効時も保存するセッション編集"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "失効時も保存するセッション編集")
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before)
        for model in (AsyncJob, GoogleWriteTarget, GoogleWriteAdmission, GoogleWriteReservation, GoogleJobDispatch):
            self.assertFalse(model.objects.exists())
        callback.assert_not_called()

    def test_automatic_immediate_delivery_refusal_keeps_admission_and_records_failure(self):
        with patch.object(tasks, "queue_google_calendar_sync", return_value=False) as queue:
            tasks.schedule_session_google_syncs(self.session)
        job = AsyncJob.objects.get()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertEqual(job.error, tasks.BACKGROUND_TASK_UNAVAILABLE_MESSAGE)
        self.assertEqual(GoogleWriteAdmission.objects.get().job_id, job.pk)
        self.sync.refresh_from_db()
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
        self.assertEqual(self.sync.last_error, job.error)
        queue.assert_called_once_with(self.sync.pk, str(job.pk))

    def test_undated_or_cancelled_acceptance_keeps_an_explicit_operation_without_event_body(self):
        for change in ({"date": None}, {"status": "cancelled"}):
            with self.subTest(change=change), patch("django.db.transaction.on_commit"):
                type(self.session).objects.filter(pk=self.session.pk).update(**change)
                response = self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
                snapshot = open_google_write_snapshot(GoogleWriteAdmission.objects.get(job_id=response.data["job_id"]))
                self.assertIsNone(snapshot["calendar"]["event"])
                self.assertEqual(snapshot["calendar"]["operation"], "cancel" if "status" in change else "upsert")

    def test_invalid_values_or_wrong_calendar_target_are_rejected_without_new_receipt(self):
        job, args = self._queue("sheets")
        with self.assertRaises(InvalidGoogleWriteAdmission):
            intake.register_sheets_intake(job, [["本文を差し替えた合成セル"]])
        job, _ = self._queue("calendar")
        self.sync.user_id = self.other.pk
        with self.assertRaises(InvalidGoogleWriteAdmission):
            intake.register_calendar_intake(job, self.sync, self.session)
