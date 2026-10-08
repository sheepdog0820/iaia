"""Independent cleanup/receipt transactions cannot erase a write prohibition."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

import requests
from django.conf import settings
from django.db import close_old_connections, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from schedules import google_target_execution
from schedules import test_google_cleanup_execution as cleanup_fixtures
from schedules.models import (
    AsyncJob,
    GoogleJobDispatch,
    GoogleWriteAdmission,
    GoogleWriteExecution,
    GoogleWriteRequest,
    GoogleWriteReservation,
)
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用のcleanup/receipt実ロック競合検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleCleanupConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    # Reuse fixture/actions only; do not inherit and rerun the sequential tests.
    _accepted = cleanup_fixtures.GoogleCleanupExecutionTest._accepted
    _delete_owner = cleanup_fixtures.GoogleCleanupExecutionTest._delete_owner
    _delete_job = cleanup_fixtures.GoogleCleanupExecutionTest._delete_job
    _expire_job = cleanup_fixtures.GoogleCleanupExecutionTest._expire_job
    _expire_execution = cleanup_fixtures.GoogleCleanupExecutionTest._expire_execution
    _journal = cleanup_fixtures.GoogleCleanupExecutionTest._journal
    _waiting = cleanup_fixtures.GoogleCleanupExecutionTest._waiting
    _follow_after_cleanup = cleanup_fixtures.GoogleCleanupExecutionTest._follow_after_cleanup

    def _run_race(self, mode, cleanup, known, cleanup_first):
        self.fixture_sheet_id = "cleanup-race-shared-sheet-fixture"
        job, args = self._accepted(mode)
        cleanup_pending, receipt_locked, release, cleanup_committed = (Event() for _ in range(4))
        http_entered = Event()
        pids = {}
        original_receive = google_target_execution._receive_request

        def independent(role, action):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '8s'")
                    cursor.execute("SET statement_timeout = '12s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[role] = cursor.fetchone()[0]
                return action()
            finally:
                connection.close()

        def action():
            self.assertTrue(http_entered.wait(8), "INTENT確定後のHTTP到達を確認できませんでした。")
            if not cleanup_first:
                self.assertTrue(receipt_locked.wait(8), "receiptの実行開始を確認できませんでした。")
            with transaction.atomic():
                {
                    "owner": self._delete_owner,
                    "job": self._delete_job,
                    "expiry": self._expire_job,
                    "deadline": self._expire_execution,
                }[cleanup](job)
                cleanup_pending.set()
                if cleanup_first:
                    self.assertTrue(release.wait(8), "cleanup transactionの待機が終了しませんでした。")
            cleanup_committed.set()

        def after_http(url, **kwargs):
            self.assertFalse(connection.in_atomic_block, "HTTP中にDB lockを保持しています。")
            execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
            self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
            self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
            http_entered.set()
            if cleanup_first:
                self.assertTrue(cleanup_pending.wait(8), "cleanupの未確定処理を確認できませんでした。")
            if not known:
                raise requests.Timeout("Synthetic response loss during independent cleanup")
            return self.response(200, {"id": kwargs["json"]["id"]} if mode == "calendar" else {"updatedCells": 17})

        def lock_gate(execute, sql, params, many, context):
            result = execute(sql, params, many, context)
            if "schedules_asyncjob" in sql and "FOR UPDATE" in sql:
                # Only installed inside the real receipt function. The actual
                # SELECT has acquired its PG lock before the gate is signalled.
                receipt_locked.set()
                if not cleanup_first:
                    self.assertTrue(release.wait(8), "receipt transactionの待機が終了しませんでした。")
            return result

        def receive(*receive_args, **receive_kwargs):
            with connection.execute_wrapper(lock_gate):
                result = original_receive(*receive_args, **receive_kwargs)
            if not cleanup_first:
                # Let the real cleanup commit before the worker continues to
                # completion; do not mock the receipt or completion writes.
                self.assertTrue(cleanup_committed.wait(8), "独立cleanupの確定を確認できませんでした。")
            return result

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            method = "post" if mode == "calendar" else "put"
            sends[method].side_effect = after_http
            stack.enter_context(patch.object(google_target_execution, "_receive_request", new=receive))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {
                    "worker": pool.submit(independent, "worker", lambda: self._worker(mode).run(*args)),
                    "cleanup": pool.submit(independent, "cleanup", action),
                }
                try:
                    waiter, blocker = ("worker", "cleanup") if cleanup_first else ("cleanup", "worker")
                    deadline = monotonic() + 6
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_backend_pid()")
                        observer = cursor.fetchone()[0]
                        while True:
                            for future in futures.values():
                                if future.done() and future.exception() is not None:
                                    future.result()
                            if len(pids) == 2:
                                self.assertEqual(len({observer, *pids.values()}), 3)
                                cursor.execute("SELECT pg_stat_clear_snapshot()")
                                cursor.execute(
                                    "SELECT pg_blocking_pids(pid),query FROM pg_stat_activity "
                                    "WHERE pid=%s AND wait_event_type='Lock'",
                                    [pids[waiter]],
                                )
                                observed = cursor.fetchone()
                                if observed and pids[blocker] in observed[0]:
                                    self.assertIn("schedules_asyncjob", observed[1])
                                    self.assertIn(
                                        (
                                            "FOR UPDATE"
                                            if cleanup_first
                                            else ("UPDATE" if cleanup in {"deadline", "expiry"} else "DELETE")
                                        ),
                                        observed[1],
                                    )
                                    print(
                                        f"GOOGLE_CLEANUP_LOCK mode={mode} cleanup={cleanup} known={known} "
                                        f"cleanup_first={cleanup_first} waiter={pids[waiter]} "
                                        f"blocker={pids[blocker]} observer={observer}"
                                    )
                                    break
                            self.assertLess(monotonic(), deadline, "独立接続の実PG lock待機を観測できませんでした。")
                            sleep(0.01)
                    # The independent observer sees committed INTENT, never a
                    # fake closed boundary from either uncommitted operation.
                    execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                    self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
                    self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
                    self.assertFalse(
                        execution.allocations.exclude(target__active_execution_token=execution.pk).exists()
                    )
                    release.set()
                    self.assertIsNone(futures["cleanup"].result(timeout=10))
                    self.assertEqual(futures["worker"].result(timeout=10), "inactive-job")
                finally:
                    # Unblock instrumentation on assertion failure, too. A
                    # future exception still propagates; teardown is not proof.
                    release.set()
                    cleanup_pending.set()
                    receipt_locked.set()
                    cleanup_committed.set()
                    http_entered.set()
            sends[method].assert_called_once()
            for other_method in set(sends) - {method}:
                sends[other_method].assert_not_called()

        execution.refresh_from_db()
        request = execution.requests.get()
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertIsNone(execution.closed_at)
        self.assertEqual(
            (request.state, request.response_status),
            (GoogleWriteRequest.State.KNOWN, 200) if known else (GoogleWriteRequest.State.UNKNOWN, None),
        )
        self.assertIsNotNone(request.received_at)
        self.assertEqual(execution.allocations.count(), 2 if mode == "calendar" else 1)
        self.assertFalse(execution.allocations.exclude(target__active_execution_token=execution.pk).exists())
        if cleanup == "deadline":
            job.refresh_from_db()
            self.assertEqual(job.status, AsyncJob.Status.UNCERTAIN)
            self.assertTrue(job.google_write_admission.ciphertext)
            self.assertEqual(job.google_dispatch.ciphertext, "")
        else:
            self.assertFalse(AsyncJob.objects.filter(pk=job.pk).exists())
            self.assertFalse(GoogleWriteAdmission.objects.filter(job_id=job.pk).exists())
            self.assertFalse(GoogleJobDispatch.objects.filter(job_id=job.pk).exists())
            self.assertFalse(GoogleWriteReservation.objects.exists())

        journal = self._journal()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker(mode).run(*args), "inactive-job" if cleanup == "deadline" else "invalid-job")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(self._journal(), journal)
        if mode == "sheets" or cleanup != "owner":
            execution_before = GoogleWriteExecution.objects.filter(pk=execution.pk).values().get()
            request_before = GoogleWriteRequest.objects.filter(pk=request.pk).values().get()
            self._follow_after_cleanup(mode, cleanup, job.pk, execution.pk)
            self.assertEqual(GoogleWriteExecution.objects.filter(pk=execution.pk).values().get(), execution_before)
            self.assertEqual(GoogleWriteRequest.objects.filter(pk=request.pk).values().get(), request_before)

    def test_calendar_owner_known_cleanup_first(self):
        self._run_race("calendar", "owner", True, True)

    def test_calendar_owner_known_receipt_first(self):
        self._run_race("calendar", "owner", True, False)

    def test_calendar_owner_lost_cleanup_first(self):
        self._run_race("calendar", "owner", False, True)

    def test_calendar_owner_lost_receipt_first(self):
        self._run_race("calendar", "owner", False, False)

    def test_calendar_job_known_cleanup_first(self):
        self._run_race("calendar", "job", True, True)

    def test_calendar_job_known_receipt_first(self):
        self._run_race("calendar", "job", True, False)

    def test_calendar_job_lost_cleanup_first(self):
        self._run_race("calendar", "job", False, True)

    def test_calendar_job_lost_receipt_first(self):
        self._run_race("calendar", "job", False, False)

    def test_calendar_expiry_known_cleanup_first(self):
        self._run_race("calendar", "expiry", True, True)

    def test_calendar_expiry_known_receipt_first(self):
        self._run_race("calendar", "expiry", True, False)

    def test_calendar_expiry_lost_cleanup_first(self):
        self._run_race("calendar", "expiry", False, True)

    def test_calendar_expiry_lost_receipt_first(self):
        self._run_race("calendar", "expiry", False, False)

    def test_calendar_deadline_known_cleanup_first(self):
        self._run_race("calendar", "deadline", True, True)

    def test_calendar_deadline_known_receipt_first(self):
        self._run_race("calendar", "deadline", True, False)

    def test_calendar_deadline_lost_cleanup_first(self):
        self._run_race("calendar", "deadline", False, True)

    def test_calendar_deadline_lost_receipt_first(self):
        self._run_race("calendar", "deadline", False, False)

    def test_sheets_owner_known_cleanup_first(self):
        self._run_race("sheets", "owner", True, True)

    def test_sheets_owner_known_receipt_first(self):
        self._run_race("sheets", "owner", True, False)

    def test_sheets_owner_lost_cleanup_first(self):
        self._run_race("sheets", "owner", False, True)

    def test_sheets_owner_lost_receipt_first(self):
        self._run_race("sheets", "owner", False, False)

    def test_sheets_job_known_cleanup_first(self):
        self._run_race("sheets", "job", True, True)

    def test_sheets_job_known_receipt_first(self):
        self._run_race("sheets", "job", True, False)

    def test_sheets_job_lost_cleanup_first(self):
        self._run_race("sheets", "job", False, True)

    def test_sheets_job_lost_receipt_first(self):
        self._run_race("sheets", "job", False, False)

    def test_sheets_expiry_known_cleanup_first(self):
        self._run_race("sheets", "expiry", True, True)

    def test_sheets_expiry_known_receipt_first(self):
        self._run_race("sheets", "expiry", True, False)

    def test_sheets_expiry_lost_cleanup_first(self):
        self._run_race("sheets", "expiry", False, True)

    def test_sheets_expiry_lost_receipt_first(self):
        self._run_race("sheets", "expiry", False, False)

    def test_sheets_deadline_known_cleanup_first(self):
        self._run_race("sheets", "deadline", True, True)

    def test_sheets_deadline_known_receipt_first(self):
        self._run_race("sheets", "deadline", True, False)

    def test_sheets_deadline_lost_cleanup_first(self):
        self._run_race("sheets", "deadline", False, True)

    def test_sheets_deadline_lost_receipt_first(self):
        self._run_race("sheets", "deadline", False, False)

    def test_worker_error_is_propagated_and_cleanup_waits_are_released(self):
        # A test-instrumentation failure must fail promptly, not turn into a
        # timeout, a green result, or a leftover connection/transaction.
        with patch.object(self._worker("sheets"), "run", side_effect=RuntimeError("Synthetic worker failure")):
            self.assertRaisesRegex(
                RuntimeError, "Synthetic worker failure", self._run_race, "sheets", "job", True, True
            )
        self.assertFalse(AsyncJob.objects.exists())
        self.assertFalse(GoogleWriteExecution.objects.exists())


class GoogleCleanupConcurrencyCiTest(SimpleTestCase):
    def test_production_database_job_selects_cleanup_races(self):
        workflow = (Path(settings.BASE_DIR) / ".github/workflows/django-ci.yml").read_text(encoding="utf-8")
        production_job = workflow.split("  production-database:", 1)[1].split("  playwright:", 1)[0]
        self.assertIn("schedules/test_google_cleanup_concurrency.py", production_job)
