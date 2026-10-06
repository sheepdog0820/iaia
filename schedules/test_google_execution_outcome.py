import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from threading import Event
from unittest import skipUnless
from unittest.mock import patch
from uuid import UUID

import requests
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from schedules import google_job_lifecycle as lifecycle
from schedules import tasks
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleExecutionOutcomeTest(GoogleJobStartFixtures, TestCase):
    def _claim(self, mode="sheets"):
        job, args = self._queue(mode)
        self.assertTrue(lifecycle.claim_google_job_start(job))
        return job, args

    def _stale(self, job):
        AsyncJob.objects.filter(pk=job.pk).update(execution_deadline=timezone.now() - timedelta(seconds=1))

    def _detect(self, job):
        return lifecycle.mark_stalled_google_jobs(AsyncJob.objects.filter(pk=job.pk))

    def test_claim_has_unique_execution_token_and_bounded_deadline(self):
        job, _ = self._claim()
        self.assertIsInstance(job.execution_token, UUID)
        self.assertGreater(job.execution_deadline, timezone.now() + timedelta(seconds=950))
        self.assertLessEqual(job.execution_deadline, timezone.now() + timedelta(seconds=960))
        original_token, original_start = job.execution_token, job.started_at
        lifecycle.fail_google_job(job, "合成の通信失敗")
        self.assertTrue(lifecycle.claim_google_job_start(job))
        self.assertNotEqual(job.execution_token, original_token)
        self.assertEqual(job.started_at, original_start)
        self.assertIsNone(job.finished_at)

    def test_claim_deadline_does_not_exceed_current_job_expiry(self):
        job, _ = self._queue("sheets")
        deadline = timezone.now() + timedelta(seconds=10)
        AsyncJob.objects.filter(pk=job.pk).update(expires_at=deadline)
        self.assertTrue(lifecycle.claim_google_job_start(job))
        self.assertEqual(job.execution_deadline, deadline)

    def test_execution_window_honors_longer_limit_and_bounds_disabled_or_invalid_limits(self):
        for limit, expected in ((900, 960), (1200, 1260), (0, 960), (-1, 960), (None, 960), (True, 960), ("900", 960)):
            with self.subTest(limit=limit), override_settings(CELERY_TASK_TIME_LIMIT=limit):
                self.assertEqual(lifecycle.google_execution_window(), timedelta(seconds=expected))

    def test_detector_marks_only_stale_google_running_jobs_and_is_idempotent(self):
        now = timezone.now()
        selected = []
        for kind in ("google_calendar_sync", "google_sheets_export", "statistics_export"):
            for state in ("queued", "running", "succeeded", "failed", "uncertain"):
                for deadline in (now - timedelta(seconds=1), now + timedelta(minutes=1)):
                    job = AsyncJob.objects.create(
                        owner=self.user,
                        job_type=kind,
                        status=state,
                        execution_deadline=deadline,
                        execution_token=UUID(int=1),
                        progress=42,
                        result={"retained": True},
                        payload={"private": "合成の秘密入力"},
                        started_at=now - timedelta(minutes=2),
                        expires_at=now + timedelta(days=1),
                    )
                    if kind != "statistics_export" and state == "running" and deadline < now:
                        selected.append(job.pk)
        query = AsyncJob.objects.all()
        before = {row["id"]: row for row in query.values()}
        self.assertEqual(lifecycle.mark_stalled_google_jobs(query), 2)
        self.assertEqual(lifecycle.mark_stalled_google_jobs(query), 0)
        for job in query.all():
            old = before[job.pk]
            if job.pk in selected:
                self.assertEqual(job.status, "uncertain")
                self.assertEqual(job.error, lifecycle.GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
                self.assertIsNotNone(job.finished_at)
                self.assertEqual(
                    (job.payload, job.progress, job.result, job.execution_token),
                    (old["payload"], old["progress"], old["result"], old["execution_token"]),
                )
            else:
                self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), old)

    def test_detector_boundary_and_legacy_start_or_creation_fallback(self):
        now = timezone.now()
        for deadline, start_age, created_age, expected in (
            (now, 0, 0, 1),
            (now + timedelta(microseconds=1), 2000, 2000, 0),
            (None, 960, 2000, 1),
            (None, 959, 2000, 0),
            (None, None, 960, 1),
            (None, None, 959, 0),
        ):
            with self.subTest(deadline=deadline, start_age=start_age, created_age=created_age):
                job = AsyncJob.objects.create(
                    owner=self.user,
                    job_type="google_sheets_export",
                    status="running",
                    execution_deadline=deadline,
                    started_at=now - timedelta(seconds=start_age) if start_age is not None else None,
                    created_at=now - timedelta(seconds=created_age),
                    expires_at=now + timedelta(days=1),
                )
                with patch.object(lifecycle.timezone, "now", return_value=now):
                    self.assertEqual(self._detect(job), expected)

    def test_stale_execution_cannot_send_progress_fail_or_succeed_even_before_detection(self):
        for mode in ("sheets", "calendar"):
            job, _ = self._claim(mode)
            self._stale(job)
            before = AsyncJob.objects.filter(pk=job.pk).values().get()
            for update in (
                lambda: lifecycle.require_running_google_job(job),
                lambda: lifecycle.set_google_job_progress(job, 99),
                lambda: lifecycle.fail_google_job(job, "遅い失敗"),
                lambda: lifecycle.succeed_google_job(job, {"late": True}),
            ):
                with self.assertRaises(lifecycle.GoogleJobInactive):
                    update()
            self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)

    def test_old_execution_token_cannot_update_a_later_failed_retry_claim(self):
        stale, _ = self._claim()
        lifecycle.fail_google_job(stale, "合成の再試行")
        current = AsyncJob.objects.get(pk=stale.pk)
        self.assertTrue(lifecycle.claim_google_job_start(current))
        before = AsyncJob.objects.filter(pk=current.pk).values().get()
        with self.assertRaises(lifecycle.GoogleJobInactive):
            lifecycle.succeed_google_job(stale, {"obsolete": True})
        with self.assertRaises(lifecycle.GoogleJobInactive):
            lifecycle.set_google_job_progress(stale, 88)
        self.assertEqual(AsyncJob.objects.filter(pk=current.pk).values().get(), before)
        lifecycle.succeed_google_job(current, {"current": True})

    def test_live_legacy_running_record_remains_active_until_cutoff(self):
        job, _ = self._queue("sheets")
        job.mark_running()
        lifecycle.require_running_google_job(job)
        self.assertEqual(self._detect(job), 0)
        AsyncJob.objects.filter(pk=job.pk).update(started_at=timezone.now() - timedelta(minutes=17))
        with self.assertRaises(lifecycle.GoogleJobInactive):
            lifecycle.require_running_google_job(job)
        self.assertEqual(self._detect(job), 1)

    def test_detail_marks_only_requested_owned_stale_job_and_hides_execution_fields(self):
        job, _ = self._claim()
        other, _ = self._claim()
        self._stale(job)
        self._stale(other)
        response = self.api.get(f"/api/jobs/{job.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "uncertain")
        self.assertEqual(response.data["error"], lifecycle.GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
        self.assertNotIn("execution_token", response.data)
        self.assertNotIn("execution_deadline", response.data)
        other.refresh_from_db()
        self.assertEqual(other.status, "running")

    def test_fresh_job_reads_and_nonfailed_retry_do_not_attempt_any_update(self):
        job, _ = self._claim()
        with patch.object(QuerySet, "update", side_effect=DatabaseError("合成の書き込み障害")) as update:
            self.assertEqual(self.api.get(f"/api/jobs/{job.pk}/").status_code, 200)
            self.assertEqual(self.api.get("/api/jobs/").status_code, 200)
            self.assertEqual(self.api.post(f"/api/jobs/{job.pk}/retry/").status_code, 400)
            update.assert_not_called()

    def test_foreign_or_unauthenticated_reads_cannot_mark_owner_job(self):
        job, _ = self._claim()
        self._stale(job)
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get(f"/api/jobs/{job.pk}/").status_code, 404)
        self.assertEqual(self.api.post(f"/api/jobs/{job.pk}/retry/").status_code, 404)
        self.assertEqual(self.api.get("/api/jobs/").status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(f"/api/jobs/{job.pk}/").status_code, 401)
        self.assertEqual(self.api.get("/api/jobs/").status_code, 401)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

    def test_list_classifies_before_status_filter_and_preserves_other_owners(self):
        job, _ = self._claim()
        self._stale(job)
        other = AsyncJob.objects.create(
            owner=self.other,
            job_type="google_sheets_export",
            status="running",
            execution_deadline=timezone.now() - timedelta(minutes=1),
            expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.api.get("/api/jobs/?job_type=google_sheets_export&status=uncertain")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(row["id"]) for row in response.data], [str(job.pk)])
        other.refresh_from_db()
        self.assertEqual(other.status, "running")

    def test_uncertain_retry_is_rejected_without_new_job_or_dispatch(self):
        for mode in ("sheets", "calendar"):
            job, args = self._claim(mode)
            self._stale(job)
            with (
                patch("schedules.job_views.queue_google_calendar_sync") as calendar,
                patch("schedules.job_views.queue_google_sheet_export") as sheets,
            ):
                before = AsyncJob.objects.count()
                response = self.api.post(f"/api/jobs/{job.pk}/retry/")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["detail"], lifecycle.GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
                self.assertEqual(AsyncJob.objects.count(), before)
                calendar.assert_not_called()
                sheets.assert_not_called()
            self._refuse_unchanged(mode, AsyncJob.objects.get(pk=job.pk), args)

    def test_late_provider_success_keeps_uncertain_job_and_does_not_retry(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                sends, _ = self._sends(stack)
                worker = self._worker(mode)
                retry = stack.enter_context(patch.object(worker, "retry"))
                saved = []

                def send(url, **kwargs):
                    self._stale(job)
                    self.assertEqual(self._detect(job), 1)
                    saved.extend(AsyncJob.objects.filter(pk=job.pk).values())
                    return self.response(
                        200, {"updatedCells": 17} if mode == "sheets" else {"id": kwargs["json"]["id"]}
                    )

                sends["put" if mode == "sheets" else "post"].side_effect = send
                self.assertEqual(worker.run(*args), "inactive-job")
                self.assertEqual(list(AsyncJob.objects.filter(pk=job.pk).values()), saved)
                retry.assert_not_called()

    def test_late_provider_failure_keeps_uncertain_job_sync_and_does_not_retry(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                sends, _ = self._sends(stack)
                retry = stack.enter_context(patch.object(self._worker(mode), "retry"))

                def send(*args, **kwargs):
                    self._stale(job)
                    self.assertEqual(self._detect(job), 1)
                    raise requests.Timeout("合成の遅い応答切断")

                sends["put" if mode == "sheets" else "post"].side_effect = send
                self.assertEqual(self._worker(mode).run(*args), "inactive-job")
                job.refresh_from_db()
                self.assertEqual(job.status, "uncertain")
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                retry.assert_not_called()

    def test_expiry_cleanup_classifies_unexpired_stale_job_but_keeps_existing_retention(self):
        job, _ = self._claim()
        self._stale(job)
        self.assertEqual(tasks.expire_async_jobs(), 0)
        job.refresh_from_db()
        self.assertEqual(job.status, "uncertain")
        AsyncJob.objects.filter(pk=job.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(tasks.expire_async_jobs(), 1)

    def test_uncertain_badge_is_japanese_and_has_dark_warning_contrast(self):
        source = (Path(__file__).resolve().parents[1] / "templates/integrations/settings.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("uncertain: 'bg-warning text-dark'", source)
        self.assertIn("#integration-jobs .badge.bg-warning.text-dark {\n        color: #212529 !important;", source)
        self.assertIn("status === 'uncertain' ? '結果不明' : status", source)


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の結果不明判定競合検証")
class GoogleExecutionOutcomeConcurrencyTest(GoogleJobStartFixtures, TransactionTestCase):
    def _wait_for_lock(self, worker_pid):
        deadline = time.monotonic() + 5
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            blocker = cursor.fetchone()[0]
            while True:
                cursor.execute(
                    "SELECT wait_event_type,pg_blocking_pids(pid) FROM pg_stat_activity WHERE pid=%s", [worker_pid]
                )
                row = cursor.fetchone()
                if row and row[0] == "Lock" and blocker in row[1]:
                    return
                self.assertLess(time.monotonic(), deadline, "実PGの行ロック待機を観測できませんでした。")
                time.sleep(0.02)

    def test_completion_or_new_claim_committed_during_detector_lock_wait_is_not_overwritten(self):
        for changed in ("completion", "new-claim"):
            with self.subTest(changed=changed):
                job, _ = self._queue("sheets")
                self.assertTrue(lifecycle.claim_google_job_start(job))
                AsyncJob.objects.filter(pk=job.pk).update(execution_deadline=timezone.now() - timedelta(seconds=1))
                ready = Event()
                worker_pid = []

                def detect():
                    close_old_connections()
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT pg_backend_pid()")
                            worker_pid.append(cursor.fetchone()[0])
                        ready.set()
                        return lifecycle.mark_stalled_google_jobs(AsyncJob.objects.filter(pk=job.pk))
                    finally:
                        close_old_connections()

                with ThreadPoolExecutor(max_workers=1) as pool:
                    with transaction.atomic():
                        AsyncJob.objects.select_for_update().get(pk=job.pk)
                        future = pool.submit(detect)
                        self.assertTrue(ready.wait(5))
                        self._wait_for_lock(worker_pid[0])
                        if changed == "completion":
                            AsyncJob.objects.filter(pk=job.pk).update(status="succeeded", result={"accepted": True})
                        else:
                            AsyncJob.objects.filter(pk=job.pk).update(status="failed")
                            self.assertTrue(lifecycle.claim_google_job_start(job))
                    self.assertEqual(future.result(timeout=10), 0)
                job.refresh_from_db()
                self.assertEqual(job.status, "succeeded" if changed == "completion" else "running")
