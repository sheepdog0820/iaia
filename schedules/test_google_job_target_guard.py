import uuid
from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from schedules import test_google_calendar_delivery as delivery_tests
from schedules.google_job_connection import google_connection_binding, google_sheet_values_binding
from schedules.google_sheets import SHEET_COLUMNS
from schedules.google_write_intake import register_calendar_intake, register_sheets_intake
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration
from schedules.tasks import export_google_sheet, sync_google_calendar


class GoogleJobTargetGuardTest(TestCase):
    response = delivery_tests.GoogleCalendarDeliveryTest.response
    event_response = delivery_tests.GoogleCalendarDeliveryTest.event_response
    retry_error = "ジョブ作成時のGoogle接続先を確認できません。連携設定から新しく実行してください。"

    def setUp(self):
        delivery_tests.GoogleCalendarDeliveryTest.setUp(self)
        self.other = get_user_model().objects.create_user(username="other-job-target-fixture")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.api.raise_request_exception = False
        self._restore_connection()
        network = patch("requests.sessions.Session.request", side_effect=AssertionError("Unmocked HTTP forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def _restore_connection(self):
        account, _ = SocialAccount.objects.get_or_create(user=self.user, provider="google")
        account.uid = "delivery-fixture"
        account.save(update_fields=["uid"])
        SocialToken.objects.update_or_create(
            account=account, defaults={"token": "isolated-token"}  # Synthetic fixture only. # nosec B105
        )
        self.integration, _ = GoogleIntegration.objects.update_or_create(
            user=self.user,
            defaults={
                "calendar_enabled": True,
                "sheets_enabled": True,
                "scopes": [GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE],
                "connected_at": timezone.now() - timedelta(minutes=1),
            },
        )

    def _job(self, mode, owner=None, kind=None):
        self.sync.status = GoogleCalendarSync.Status.FAILED
        self.sync.last_error = "以前の試行失敗"
        self.sync.save(update_fields=["status", "last_error"])
        job = AsyncJob.objects.create(
            owner=owner or self.user,
            job_type=kind or ("google_sheets_export" if mode == "sheets" else "google_calendar_sync"),
            error="以前の試行失敗",
            expires_at=timezone.now() + timedelta(days=1),
            payload={
                "sync_id": self.sync.pk,
                "spreadsheet_id": "isolated-sheet",
                "range": "Characters!A1",
                "character_ids": [],
                "selection_snapshot": True,
                "google_connection": google_connection_binding(self.integration),
                "google_values": google_sheet_values_binding([SHEET_COLUMNS]),
            },
        )
        if job.owner_id == self.user.pk and job.job_type == (
            "google_sheets_export" if mode == "sheets" else "google_calendar_sync"
        ):
            if mode == "sheets":
                register_sheets_intake(job, [SHEET_COLUMNS])
            else:
                register_calendar_intake(job, self.sync, self.session)
        job.mark_failed("以前の試行失敗")
        return job

    def _sends(self, stack):
        generated = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"https://tableno.jp/calendar-sync/{self.sync.pk}/{self.user.pk}/{self.session.pk}/{self.sync.created_at.isoformat()}",
        ).hex
        sends = {
            method: stack.enter_context(patch(f"schedules.tasks.requests.{method}"))
            for method in ("get", "put", "post", "delete")
        }
        sends["post"].return_value = self.response(200, {"id": generated})
        sends["get"].side_effect = self.event_response
        sends["put"].return_value = self.response(200, {"updatedCells": 0})
        sends["delete"].return_value = self.response(204, {})
        token = stack.enter_context(patch("schedules.tasks.get_google_access_token", return_value="isolated-token"))
        return sends, token

    def _run(self, mode, job_id):
        if mode == "sheets":
            return export_google_sheet.run(
                str(job_id), self.user.pk, "isolated-sheet", "Characters!A1", [SHEET_COLUMNS]
            )
        return sync_google_calendar.run(self.sync.pk, str(job_id))

    def _unchanged(self, mode, job):
        before_job = AsyncJob.objects.filter(pk=job.pk).values().get()
        before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            result = self._run(mode, job.pk)
            self.assertEqual(result, "invalid-job")
            for send in sends.values():
                send.assert_not_called()
            token.assert_not_called()
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before_job)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)

    def test_calendar_does_not_use_another_owners_job(self):
        for status in ("planned", "cancelled"):
            with self.subTest(status=status):
                self.session.status = status
                self.session.save(update_fields=["status"])
                self._unchanged("calendar", self._job("calendar", owner=self.other))

    def test_workers_do_not_use_another_kind_of_job(self):
        for mode in ("calendar", "sheets"):
            for kind in ("statistics_export", "google_calendar_sync" if mode == "sheets" else "google_sheets_export"):
                with self.subTest(mode=mode, kind=kind):
                    self._unchanged(mode, self._job(mode, kind=kind))

    def test_sheets_wrong_owner_and_missing_jobs_do_not_change_state(self):
        self._unchanged("sheets", self._job("sheets", owner=self.other))
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                sends, token = self._sends(stack)
                result = self._run(mode, uuid.uuid4())
                self.assertEqual(result, "invalid-job")
                for send in sends.values():
                    send.assert_not_called()
                token.assert_not_called()
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before)

    def test_retry_preserves_binding_and_delivers_through_actual_worker(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job = self._job(mode)
                binding = job.payload["google_connection"]
                queue = stack.enter_context(
                    patch(
                        f"schedules.job_views.queue_google_{'sheet_export' if mode == 'sheets' else 'calendar_sync'}",
                        return_value=True,
                    )
                )
                self._sends(stack)
                result = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                self.assertEqual(result.status_code, 202)
                queued = AsyncJob.objects.get(pk=result.data["job_id"])
                self.assertEqual(queued.payload.get("google_connection"), binding)
                self.assertEqual(queued.payload["retry_of"], str(job.pk))
                worker = export_google_sheet if mode == "sheets" else sync_google_calendar
                self.assertEqual(
                    worker.run(*queue.call_args.args),
                    "exported" if mode == "sheets" else GoogleCalendarSync.Status.SYNCED,
                )
                queued.refresh_from_db()
                self.assertEqual(queued.status, AsyncJob.Status.SUCCEEDED)
                queue.assert_called_once()
                # Each subcase starts with a synthetic not-yet-saved event.
                GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(external_event_id="")
                self.sync.refresh_from_db()

    def test_retry_after_access_rotation_keeps_original_target_binding(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                self._restore_connection()
                job = self._job(mode)
                SocialToken.objects.filter(account__user=self.user).update(
                    token="isolated-rotated-access"
                )  # nosec B106
                queue = stack.enter_context(
                    patch(
                        f"schedules.job_views.queue_google_{'sheet_export' if mode == 'sheets' else 'calendar_sync'}",
                        return_value=True,
                    )
                )
                result = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                self.assertEqual(result.status_code, 202)
                queued = AsyncJob.objects.get(pk=result.data["job_id"])
                self.assertEqual(queued.payload.get("google_connection"), job.payload["google_connection"])
                sends, token = self._sends(stack)
                token.return_value = "isolated-rotated-access"  # Synthetic fixture only. # nosec B105
                worker = export_google_sheet if mode == "sheets" else sync_google_calendar
                self.assertEqual(
                    worker.run(*queue.call_args.args),
                    "exported" if mode == "sheets" else GoogleCalendarSync.Status.SYNCED,
                )
                self.assertEqual(
                    sends["put" if mode == "sheets" else "post"].call_args.kwargs["headers"]["Authorization"],
                    "Bearer isolated-rotated-access",
                )
                queue.assert_called_once()

    def test_retry_rejects_changed_missing_or_malformed_connection_without_side_effects(self):
        for mode in ("calendar", "sheets"):
            for reason in (
                "legacy",
                "malformed-payload",
                "malformed-binding",
                "wrong-binding",
                "reconnected",
                "deleted-token",
                "replaced-token",
                "account-changed",
                "recreated-integration",
                "key-changed",
            ):
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    self._restore_connection()
                    job = self._job(mode)
                    if reason in ("legacy", "malformed-payload", "malformed-binding", "wrong-binding"):
                        job.payload = (
                            {"sync_id": self.sync.pk}
                            if reason == "legacy"
                            else (
                                []
                                if reason == "malformed-payload"
                                else {"google_connection": [] if reason == "malformed-binding" else "wrong"}
                            )
                        )
                        job.save(update_fields=["payload"])
                    elif reason == "reconnected":
                        GoogleIntegration.objects.filter(pk=self.integration.pk).update(connected_at=timezone.now())
                    elif reason in ("deleted-token", "replaced-token"):
                        SocialToken.objects.filter(account__user=self.user).delete()
                        if reason == "replaced-token":
                            SocialToken.objects.create(
                                account=SocialAccount.objects.get(user=self.user), token="isolated-replacement"
                            )  # nosec B106
                    elif reason == "account-changed":
                        SocialAccount.objects.filter(user=self.user).update(uid="another-private-identity")
                    elif reason == "recreated-integration":
                        self.integration.delete()
                        self._restore_connection()
                    else:
                        stack.enter_context(
                            override_settings(SECRET_KEY="synthetic-alternate-signing-key")  # nosec B106
                        )
                    original = AsyncJob.objects.filter(pk=job.pk).values().get()
                    original_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    count = AsyncJob.objects.count()
                    calendar = stack.enter_context(
                        patch("schedules.job_views.queue_google_calendar_sync", return_value=True)
                    )
                    sheets = stack.enter_context(
                        patch("schedules.job_views.queue_google_sheet_export", return_value=True)
                    )
                    result = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                    self.assertEqual(result.status_code, 400)
                    self.assertEqual(result.data["detail"], self.retry_error)
                    self.assertEqual(AsyncJob.objects.count(), count)
                    self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), original)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), original_sync)
                    calendar.assert_not_called()
                    sheets.assert_not_called()

    def test_foreign_user_cannot_retry_even_with_matching_binding(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job = self._job(mode, owner=self.other)
                count = AsyncJob.objects.count()
                result = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                self.assertEqual(result.status_code, 404)
                self.assertEqual(AsyncJob.objects.count(), count)
