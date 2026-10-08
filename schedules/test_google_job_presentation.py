"""Owned status hints must not expose shared holders or authorize replay."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from schedules import tasks
from schedules.google_job_lifecycle import claim_google_job_start
from schedules.google_job_presentation import google_job_presentation
from schedules.google_target_execution import finish_execution
from schedules.job_views import AsyncJobSerializer
from schedules.models import AsyncJob, GoogleIntegration, GoogleWriteExecution, GoogleWriteTarget
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleJobPresentationTest(GoogleDispatchStateFixtures, TestCase):
    def _accepted(self, mode):
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self._dispatch(mode)
        return AsyncJob.objects.get(pk=response.data["job_id"])

    def _read(self, job):
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        return response.data

    def _state(self, job, expected, can_retry=False):
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        data = self._read(job)
        self.assertEqual(data["display_state"], expected)
        self.assertIs(data["can_retry"], can_retry)
        self.assertIsInstance(data["status_message"], str)
        self.assertEqual(data["status"], before["status"])
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        return data

    def _unresolved(self, mode, state="unknown"):
        job = self._accepted(mode)
        self.assertTrue(claim_google_job_start(job))
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
        execution.state = state
        execution.save(update_fields=["state"])
        return job, execution

    def test_first_queued_and_later_fifo_waiting_are_distinct_without_state_writes(self):
        first = self._accepted("calendar")
        second = self._accepted("calendar")
        self._state(first, "queued")
        data = self._state(second, "target_waiting")
        self.assertIn("先行処理", data["status_message"])
        self.assertNotIn(str(first.pk), json.dumps(data, default=str))

    def test_running_own_active_execution_is_not_reported_unknown(self):
        job, _ = self._unresolved("calendar", "active")
        self._state(job, "running")

    def test_unknown_own_execution_is_visible_before_execution_deadline(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                self._fresh_dispatch_target()
                job, execution = self._unresolved(mode)
                self.assertGreater(job.execution_deadline, timezone.now())
                data = self._state(job, "needs_review")
                self.assertIn("再試行できません", data["status_message"])
                for secret in (str(execution.token), execution.admission_binding, execution.allocation_binding):
                    self.assertNotIn(secret, json.dumps(data, default=str))

    def test_failed_with_active_or_unknown_journal_cannot_create_a_retry(self):
        for mode in ("calendar", "sheets"):
            for journal_state in ("active", "unknown"):
                with self.subTest(mode=mode, journal_state=journal_state):
                    self._fresh_dispatch_target()
                    job, execution = self._unresolved(mode, journal_state)
                    job.mark_failed("保存結果を確認できませんでした。")
                    before = AsyncJob.objects.filter(pk=job.pk).values().get()
                    count = AsyncJob.objects.count()
                    response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("再試行できません", response.data["detail"])
                    self.assertEqual(AsyncJob.objects.count(), count)
                    self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                    execution.refresh_from_db()
                    self.assertEqual(execution.state, journal_state)
                    self.assertIsNone(execution.closed_at)
                    self._state(job, "needs_review")

    def test_known_finished_failed_execution_keeps_ordinary_retry_available(self):
        job, execution = self._unresolved("sheets", "finished")
        GoogleWriteTarget.objects.filter(executions__execution=execution).update(active_execution_token=None)
        job.mark_failed("書き込み前に拒否されました。")
        self._state(job, "failed", True)
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 202)
        self._state(job, "superseded")

    def test_deleted_unknown_source_leaves_successor_waiting_without_private_evidence(self):
        job, execution = self._unresolved("sheets")
        later = self._accepted("sheets")
        job.delete()
        before = GoogleWriteExecution.objects.filter(pk=execution.pk).values().get()
        data = self._state(later, "target_waiting")
        self.assertNotIn(str(execution.token), json.dumps(data, default=str))
        self.assertEqual(GoogleWriteExecution.objects.filter(pk=execution.pk).values().get(), before)

    def test_shared_sheet_of_other_owner_reports_only_generic_waiting(self):
        source, execution = self._unresolved("sheets")
        other = get_user_model().objects.create_user(username="private-shared-owner")
        account = SocialAccount.objects.create(user=other, provider="google", uid="private-shared-account")
        SocialToken.objects.create(account=account, token="synthetic-other-token")  # nosec B106
        GoogleIntegration.objects.create(
            user=other, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )
        self.api.force_authenticate(other)
        later = self._accepted("sheets")
        data = self._state(later, "target_waiting")
        listing = self.api.get(reverse("async-job-list")).data
        self.assertEqual([item["id"] for item in listing], [str(later.pk)])
        self.assertEqual(self.api.get(reverse("async-job-detail", kwargs={"pk": source.pk})).status_code, 404)
        for private in (
            str(source.pk),
            str(execution.token),
            self.user.username,
            "isolated-token",
            execution.allocation_binding,
        ):
            self.assertNotIn(private, json.dumps(data, default=str))

    def test_expired_queued_is_not_misreported_as_live_target_waiting(self):
        self._unresolved("calendar")
        job = self._accepted("calendar")
        job.expires_at = timezone.now() - timedelta(seconds=1)
        job.save(update_fields=["expires_at"])
        self._state(job, "expired")

    def test_supersession_remains_visible_after_successor_deletion(self):
        source = self._accepted("sheets")
        source.mark_failed("書き込み前の失敗")
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self.api.post(reverse("async-job-retry", kwargs={"pk": source.pk}))
        self.assertEqual(response.status_code, 202)
        AsyncJob.objects.get(pk=response.data["job_id"]).delete()
        self._state(source, "superseded")

    def test_plain_non_google_failure_is_not_advertised_as_retryable(self):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="statistics_export",
            status="failed",
            expires_at=timezone.now() + timedelta(days=1),
        )
        self._state(job, "failed")

    def test_malformed_saved_payload_is_unknown_without_a_retry_hint(self):
        for payload in (True, 42, [], "google_retry_successor"):
            with self.subTest(payload=payload):
                job = AsyncJob.objects.create(
                    owner=self.user,
                    job_type="google_sheets_export",
                    status="failed",
                    payload=payload,
                    expires_at=timezone.now() + timedelta(days=1),
                )
                self._state(job, "unknown")

    def test_list_presentation_uses_constant_number_of_selects(self):
        for _ in range(8):
            self._accepted("calendar")
        with CaptureQueriesContext(connection) as captured:
            response = self.api.get(reverse("async-job-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 8)
        self.assertEqual(sum(item["display_state"] == "target_waiting" for item in response.data), 7)
        selects = [query["sql"] for query in captured if query["sql"].lstrip().upper().startswith("SELECT")]
        self.assertLessEqual(len(selects), 2, selects)

    def test_retired_sequence_and_unknown_status_have_safe_hints(self):
        job = self._accepted("sheets")
        GoogleWriteTarget.objects.filter(reservations__admission__job=job).update(last_started_sequence=2)
        self._state(job, "superseded")
        job.status = "unrecognized"
        job.save(update_fields=["status"])
        self._state(job, "unknown")

    def test_plain_states_and_confirmed_completion_are_not_reclassified_by_expiry(self):
        for kind in ("google_sheets_export", "statistics_export"):
            for state in (*AsyncJob.Status.values, "unrecognized"):
                with self.subTest(kind=kind, state=state):
                    job = AsyncJob.objects.create(
                        owner=self.user, job_type=kind, status=state, expires_at=timezone.now() - timedelta(seconds=1)
                    )
                    if state == "running":
                        job.started_at = timezone.now()
                        job.execution_deadline = timezone.now() + timedelta(minutes=1)
                        job.save(update_fields=["started_at", "execution_deadline"])
                    expected = (
                        "expired"
                        if kind == "google_sheets_export" and state in ("queued", "failed")
                        else ("unknown" if state == "unrecognized" else state)
                    )
                    self._state(job, expected)

    def test_direct_serializer_reads_hints_once_and_deleted_source_fails_closed(self):
        job = self._accepted("calendar")
        with CaptureQueriesContext(connection) as queries:
            data = AsyncJobSerializer(job).data
        self.assertEqual(data["display_state"], "queued")
        self.assertEqual(len(queries), 1)
        stale = AsyncJob.objects.get(pk=job.pk)
        job.delete()
        self.assertEqual(google_job_presentation(stale)["display_state"], "unknown")
        self.assertIs(google_job_presentation(stale)["can_retry"], False)

    def test_unresolved_journal_overrides_contradictory_success_and_unknown_journal_state(self):
        for state in ("succeeded", "queued", "uncertain", "unrecognized"):
            with self.subTest(state=state):
                self._fresh_dispatch_target()
                job, _ = self._unresolved("calendar", "active")
                job.status = state
                job.save(update_fields=["status"])
                self._state(job, "needs_review")
        self._fresh_dispatch_target()
        job, _ = self._unresolved("calendar", "unrecognized")
        self._state(job, "needs_review")

    def test_missing_target_marker_does_not_hide_an_unresolved_shared_journal(self):
        source, execution = self._unresolved("sheets")
        later = self._accepted("sheets")
        GoogleWriteTarget.objects.filter(executions__execution=execution).update(active_execution_token=None)
        self._state(later, "target_waiting")
        source.delete()
        self._state(later, "target_waiting")

    def test_finished_journal_without_marker_is_not_a_target_wait(self):
        job, execution = self._unresolved("sheets", "finished")
        GoogleWriteTarget.objects.filter(executions__execution=execution).update(active_execution_token=None)
        job.mark_succeeded()
        later = self._accepted("sheets")
        self._state(later, "queued")

    def test_failed_expired_and_superseded_fifo_sources_do_not_mislabel_target_waiting(self):
        for previous in ("failed", "expired", "superseded"):
            with self.subTest(previous=previous):
                self._fresh_dispatch_target()
                first = self._accepted("calendar")
                if previous == "failed":
                    first.mark_failed("送信前の失敗")
                elif previous == "expired":
                    first.expires_at = timezone.now() - timedelta(seconds=1)
                    first.save(update_fields=["expires_at"])
                else:
                    first.payload["google_retry_successor"] = None
                    first.save(update_fields=["payload"])
                self._state(self._accepted("calendar"), "queued")

    def test_legacy_successor_detection_requires_same_owner_and_job_type(self):
        source = self._accepted("sheets")
        source.mark_failed("送信前の失敗")
        for owner, kind in ((self.other, source.job_type), (self.user, "statistics_export")):
            AsyncJob.objects.create(
                owner=owner,
                job_type=kind,
                payload={"retry_of": str(source.pk)},
                expires_at=timezone.now() + timedelta(days=1),
            )
            self._state(source, "failed", True)
        AsyncJob.objects.create(
            owner=self.user,
            job_type=source.job_type,
            payload={"retry_of": str(source.pk)},
            expires_at=timezone.now() + timedelta(days=1),
        )
        self._state(source, "superseded")

    def test_unresolved_retry_rejects_without_dispatch_and_other_owner_has_no_access(self):
        job, _ = self._unresolved("sheets")
        job.mark_failed("保存結果の確認が必要です。")
        with patch.object(tasks, "queue_google_sheet_export") as delivery:
            self.assertEqual(self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk})).status_code, 400)
            delivery.assert_not_called()
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk})).status_code, 404)
        self.api.force_authenticate(None)
        self.assertIn(self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk})).status_code, (401, 403))


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の実行記録と再試行の競合検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleJobRetryJournalConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _observe_source_lock(self, backend_ids, timeout=5):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid=ANY(%s) AND wait_event_type='Lock' "
                    "AND query LIKE '%%schedules_asyncjob%%' AND query LIKE '%%FOR UPDATE%%'",
                    [backend_ids],
                )
                if cursor.fetchone()[0]:
                    return
            sleep(0.01)
        self.fail("再試行のsource行ロック待機を観測できませんでした。")

    def _retry(self, job, backend_ids):
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                backend_ids.append(cursor.fetchone()[0])
            client = APIClient()
            client.force_authenticate(self.user)
            return client.post(reverse("async-job-retry", kwargs={"pk": job.pk})).status_code
        finally:
            close_old_connections()

    def test_retry_waits_for_committed_unresolved_or_finished_journal(self):
        for mode in ("calendar", "sheets"):
            for finished in (False, True):
                with self.subTest(mode=mode, finished=finished):
                    self._fresh_dispatch_target()
                    with patch.object(tasks, "_broker_available", return_value=False):
                        response = self._dispatch(mode)
                    job = AsyncJob.objects.get(pk=response.data["job_id"])
                    self.assertTrue(claim_google_job_start(job))
                    job.mark_failed("送信前の失敗")
                    before = AsyncJob.objects.count()
                    entered, release = Event(), Event()
                    backend_ids = []

                    def finalize():
                        close_old_connections()
                        try:
                            with transaction.atomic():
                                current = AsyncJob.objects.select_for_update().get(pk=job.pk)
                                if finished:
                                    finish_execution(current)
                                else:
                                    GoogleWriteExecution.objects.filter(job_id_snapshot=job.pk).update(state="unknown")
                                entered.set()
                                self.assertTrue(release.wait(timeout=10))
                        finally:
                            close_old_connections()

                    with (
                        patch.object(tasks, "_broker_available", return_value=False),
                        ThreadPoolExecutor(max_workers=2) as pool,
                    ):
                        worker = pool.submit(finalize)
                        try:
                            self.assertTrue(entered.wait(timeout=10))
                            request = pool.submit(self._retry, job, backend_ids)
                            self._observe_source_lock(backend_ids)
                        finally:
                            release.set()
                        worker.result(timeout=10)
                        self.assertEqual(request.result(timeout=10), 202 if finished else 400)
                    self.assertEqual(AsyncJob.objects.count(), before + int(finished))
                    execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                    self.assertEqual(execution.state, "finished" if finished else "unknown")
                    self.assertEqual(execution.closed_at is not None, finished)

    def test_lock_observation_timeout_is_bounded(self):
        with self.assertRaisesRegex(AssertionError, "ロック待機"):
            self._observe_source_lock([], timeout=0.02)
