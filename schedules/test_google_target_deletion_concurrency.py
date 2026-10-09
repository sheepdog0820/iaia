"""Real Calendar completion/delete locks preserve source incarnations."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

import requests
from django.conf import settings
from django.db import close_old_connections, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from schedules import google_target_execution
from schedules import test_google_cleanup_execution as cleanup_fixtures
from schedules.models import (
    AsyncJob,
    GoogleCalendarSync,
    GoogleJobDispatch,
    GoogleWriteAdmission,
    GoogleWriteExecution,
    GoogleWriteRequest,
    TRPGSession,
)
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用のCalendar保存/対象削除実ロック競合検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleTargetDeletionConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _accepted = cleanup_fixtures.GoogleCleanupExecutionTest._accepted
    _delete_session = cleanup_fixtures.GoogleCleanupExecutionTest._delete_session
    _delete_sync = cleanup_fixtures.GoogleCleanupExecutionTest._delete_sync
    _journal = cleanup_fixtures.GoogleCleanupExecutionTest._journal

    def _run_race(self, cleanup, cleanup_first):
        job, args = self._accepted("calendar")
        source_session, source_sync = self.session, self.sync
        http_entered, deleted, saved, release = (Event() for _ in range(4))
        pids = {}

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

        def delete():
            self.assertTrue(http_entered.wait(8), "INTENT確定後のHTTP到達を確認できませんでした。")
            if not cleanup_first:
                self.assertTrue(saved.wait(8), "同期行の実UPDATEを確認できませんでした。")
            with transaction.atomic():
                {"session": self._delete_session, "sync": self._delete_sync}[cleanup](job)
                deleted.set()
                if cleanup_first:
                    self.assertTrue(release.wait(8), "対象削除transactionの待機が終了しませんでした。")

        def after_http(url, **kwargs):
            self.assertFalse(connection.in_atomic_block, "HTTP中にDB lockを保持しています。")
            execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
            self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
            self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
            http_entered.set()
            if cleanup_first:
                self.assertTrue(deleted.wait(8), "対象削除の未確定処理を確認できませんでした。")
            return self.response(200, {"id": kwargs["json"]["id"]})

        def save_gate(execute, sql, params, many, context):
            result = execute(sql, params, many, context)
            if sql.startswith('UPDATE "schedules_googlecalendarsync"'):
                # Pause after the real UPDATE acquired its lock, not instead of
                # saving. The wrapper is installed only on the worker connection.
                saved.set()
                if not cleanup_first:
                    self.assertTrue(release.wait(8), "同期保存transactionの待機が終了しませんでした。")
            return result

        def worker():
            with connection.execute_wrapper(save_gate):
                return self._worker("calendar").run(*args)

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["post"].side_effect = after_http
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {
                    "worker": pool.submit(independent, "worker", worker),
                    "cleanup": pool.submit(independent, "cleanup", delete),
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
                                    self.assertIn("schedules_googlecalendarsync", observed[1])
                                    self.assertIn("UPDATE" if cleanup_first else "DELETE", observed[1])
                                    print(
                                        f"GOOGLE_TARGET_DELETE_LOCK cleanup={cleanup} cleanup_first={cleanup_first} "
                                        f"waiter={pids[waiter]} blocker={pids[blocker]} observer={observer}"
                                    )
                                    break
                            self.assertLess(monotonic(), deadline, "独立接続の実PG lock待機を観測できませんでした。")
                            sleep(0.01)
                    execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                    self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
                    self.assertEqual(
                        (execution.requests.get().state, execution.requests.get().response_status),
                        (GoogleWriteRequest.State.KNOWN, 200),
                    )
                    self.assertFalse(
                        execution.allocations.exclude(target__active_execution_token=execution.pk).exists()
                    )
                    release.set()
                    self.assertIsNone(futures["cleanup"].result(timeout=10))
                    self.assertEqual(
                        futures["worker"].result(timeout=10), "inactive-job" if cleanup_first else "synced"
                    )
                finally:
                    # Propagate failures without leaving a held fixture lock.
                    release.set()
                    saved.set()
                    deleted.set()
                    http_entered.set()
            sends["post"].assert_called_once()
            for method in set(sends) - {"post"}:
                sends[method].assert_not_called()

        self.assertFalse(GoogleCalendarSync.objects.filter(pk=source_sync.pk).exists())
        self.assertEqual(TRPGSession.objects.filter(pk=source_session.pk).exists(), cleanup != "session")
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED if cleanup_first else AsyncJob.Status.SUCCEEDED)
        execution.refresh_from_db()
        self.assertEqual(execution.state, GoogleWriteExecution.State.FINISHED)
        self.assertIsNotNone(execution.closed_at)
        self.assertEqual(execution.allocations.count(), 2)
        self.assertFalse(execution.allocations.filter(target__active_execution_token__isnull=False).exists())
        request = execution.requests.get()
        self.assertEqual((request.state, request.response_status), (GoogleWriteRequest.State.KNOWN, 200))
        self.assertIsNotNone(request.received_at)
        journal = self._journal()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker("calendar").run(*args), "invalid-job")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(self._journal(), journal)

        # Same PK is not the same incarnation. A new accepted source is allowed
        # after the known terminal boundary, but the old delivery cannot touch it.
        before_execution = GoogleWriteExecution.objects.filter(pk=execution.pk).values().get()
        before_request = GoogleWriteRequest.objects.filter(pk=request.pk).values().get()
        if cleanup == "session":
            self.session = TRPGSession.objects.create(
                pk=source_session.pk,
                title="削除後に作成した別世代の予定",
                group=source_session.group,
                gm=self.user,
                date=timezone.now() + timedelta(days=1),
            )
            self.assertNotEqual(self.session.created_at, source_session.created_at)
        self.sync = GoogleCalendarSync.objects.create(pk=source_sync.pk, user=self.user, session=self.session)
        self.assertNotEqual(self.sync.created_at, source_sync.created_at)
        successor, successor_args = self._accepted("calendar")
        sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            # FAILED sources are eligible for the existing task retry path.
            # Their sealed snapshot rejects the new incarnation before token
            # lookup/HTTP; SUCCEEDED sources never enter that path at all.
            self.assertEqual(
                self._worker("calendar").run(*args), "invalid-admission" if cleanup_first else "inactive-job"
            )
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED if cleanup_first else AsyncJob.Status.SUCCEEDED)
        before_job = AsyncJob.objects.filter(pk=job.pk).values().get()
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(self._worker("calendar").run(*successor_args), "synced")
            sends["post"].assert_called_once()
            for method in set(sends) - {"post"}:
                sends[method].assert_not_called()
        successor.refresh_from_db()
        self.assertEqual(successor.status, AsyncJob.Status.SUCCEEDED)
        self.assertNotEqual(successor.execution_token, execution.pk)
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before_job)
        self.assertEqual(GoogleWriteExecution.objects.filter(pk=execution.pk).values().get(), before_execution)
        self.assertEqual(GoogleWriteRequest.objects.filter(pk=request.pk).values().get(), before_request)

    def test_session_cleanup_locks_before_completion(self):
        self._run_race("session", True)

    def test_session_completion_locks_before_cleanup(self):
        self._run_race("session", False)

    def test_sync_cleanup_locks_before_completion(self):
        self._run_race("sync", True)

    def test_sync_completion_locks_before_cleanup(self):
        self._run_race("sync", False)

    def test_worker_error_is_propagated_and_fixture_waits_are_released(self):
        with patch.object(self._worker("calendar"), "run", side_effect=RuntimeError("Synthetic worker failure")):
            self.assertRaisesRegex(RuntimeError, "Synthetic worker failure", self._run_race, "session", True)
        self.assertFalse(GoogleWriteExecution.objects.exists())
        self.assertFalse(GoogleCalendarSync.objects.exists())


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の応答不明/Calendar対象削除独立接続検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleUnknownTargetDeletionTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _accepted = cleanup_fixtures.GoogleCleanupExecutionTest._accepted
    _delete_session = cleanup_fixtures.GoogleCleanupExecutionTest._delete_session
    _delete_sync = cleanup_fixtures.GoogleCleanupExecutionTest._delete_sync
    _expire_job = cleanup_fixtures.GoogleCleanupExecutionTest._expire_job
    _journal = cleanup_fixtures.GoogleCleanupExecutionTest._journal

    def _assert_waiting(self, job, args):
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        delivery = GoogleJobDispatch.objects.filter(job=job).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker("calendar").run(*args), "target-waiting")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        self.assertEqual(GoogleJobDispatch.objects.filter(job=job).values().get(), delivery)
        self.assertEqual(delivery["state"], GoogleJobDispatch.State.PENDING)
        self.assertTrue(delivery["ciphertext"])

    def _run_unknown(self, cleanup, delete_first):
        job, args = self._accepted("calendar")
        source_session, source_sync = self.session, self.sync
        http_entered, deleted, received, release, cleanup_committed = (Event() for _ in range(5))
        pids = {}
        phases = []
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

        def delete():
            self.assertTrue(http_entered.wait(8), "INTENT確定後のHTTP到達を確認できませんでした。")
            if not delete_first:
                self.assertTrue(received.wait(8), "UNKNOWN receiptの実確定を確認できませんでした。")
            with transaction.atomic():
                {"session": self._delete_session, "sync": self._delete_sync}[cleanup](job)
                phases.append("delete")
                deleted.set()
                self.assertTrue(release.wait(8), "対象削除transactionの待機が終了しませんでした。")
            cleanup_committed.set()

        def lost(url, **kwargs):
            self.assertFalse(connection.in_atomic_block, "HTTP中にDB lockを保持しています。")
            execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
            self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
            self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
            http_entered.set()
            if delete_first:
                self.assertTrue(deleted.wait(8), "対象削除の未確定処理を確認できませんでした。")
            raise requests.Timeout("Synthetic response loss during independent target deletion")

        def receive(*receive_args, **receive_kwargs):
            # The real atomic receipt has committed before this gate. Do not
            # add an outer transaction or fabricate a shared-row lock conflict.
            result = original_receive(*receive_args, **receive_kwargs)
            self.assertFalse(connection.in_atomic_block)
            phases.append("receipt")
            received.set()
            self.assertTrue(release.wait(8), "UNKNOWN receipt後の待機が終了しませんでした。")
            self.assertTrue(cleanup_committed.wait(8), "独立対象削除の確定を確認できませんでした。")
            return result

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["post"].side_effect = lost
            stack.enter_context(patch.object(google_target_execution, "_receive_request", new=receive))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {
                    "worker": pool.submit(independent, "worker", lambda: self._worker("calendar").run(*args)),
                    "cleanup": pool.submit(independent, "cleanup", delete),
                }
                try:
                    deadline = monotonic() + 6
                    while not (deleted.is_set() and received.is_set()):
                        for future in futures.values():
                            if future.done() and future.exception() is not None:
                                future.result()
                        self.assertLess(monotonic(), deadline, "独立接続の削除/UNKNOWN確定を観測できませんでした。")
                        sleep(0.01)
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_backend_pid()")
                        observer = cursor.fetchone()[0]
                        self.assertEqual(len({observer, *pids.values()}), 3)
                        cursor.execute("SELECT pg_stat_clear_snapshot()")
                        cursor.execute(
                            "SELECT pid,state,wait_event_type,pg_blocking_pids(pid) "
                            "FROM pg_stat_activity WHERE pid IN (%s,%s)",
                            [pids["worker"], pids["cleanup"]],
                        )
                        states = {pid: (state, wait, blockers) for pid, state, wait, blockers in cursor.fetchall()}
                    self.assertEqual(states[pids["cleanup"]][0], "idle in transaction")
                    self.assertEqual(states[pids["worker"]][0], "idle")
                    for state, wait, blockers in states.values():
                        self.assertNotEqual(wait, "Lock")
                        self.assertEqual(blockers, [])
                    self.assertEqual(phases, ["delete", "receipt"] if delete_first else ["receipt", "delete"])
                    self.assertFalse(cleanup_committed.is_set())
                    self.assertTrue(GoogleCalendarSync.objects.filter(pk=source_sync.pk).exists())
                    execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                    self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
                    request = execution.requests.get()
                    self.assertEqual((request.state, request.response_status), (GoogleWriteRequest.State.UNKNOWN, None))
                    self.assertIsNotNone(request.received_at)
                    self.assertFalse(
                        execution.allocations.exclude(target__active_execution_token=execution.pk).exists()
                    )
                    print(
                        f"GOOGLE_UNKNOWN_TARGET_DELETE cleanup={cleanup} delete_first={delete_first} "
                        f"worker={pids['worker']} cleanup_pid={pids['cleanup']} observer={observer} "
                        "receipt_committed=true cleanup_uncommitted=true sql_lock_wait=false"
                    )
                    release.set()
                    self.assertIsNone(futures["cleanup"].result(timeout=10))
                    self.assertEqual(futures["worker"].result(timeout=10), "uncertain")
                finally:
                    release.set()
                    deleted.set()
                    received.set()
                    cleanup_committed.set()
                    http_entered.set()
            sends["post"].assert_called_once()
            for method in set(sends) - {"post"}:
                sends[method].assert_not_called()

        self.assertFalse(GoogleCalendarSync.objects.filter(pk=source_sync.pk).exists())
        self.assertEqual(TRPGSession.objects.filter(pk=source_session.pk).exists(), cleanup != "session")
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.UNCERTAIN)
        execution.refresh_from_db()
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertIsNone(execution.closed_at)
        self.assertEqual(execution.allocations.count(), 2)
        self.assertFalse(execution.allocations.exclude(target__active_execution_token=execution.pk).exists())
        request.refresh_from_db()
        before_execution = GoogleWriteExecution.objects.filter(pk=execution.pk).values().get()
        before_request = GoogleWriteRequest.objects.filter(pk=request.pk).values().get()
        journal = self._journal()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker("calendar").run(*args), "invalid-job")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(self._journal(), journal)

        if cleanup == "session":
            self.session = TRPGSession.objects.create(
                pk=source_session.pk,
                title="結果不明の削除後に作成した別世代の予定",
                group=source_session.group,
                gm=self.user,
                date=timezone.now() + timedelta(days=1),
            )
            self.assertNotEqual(self.session.created_at, source_session.created_at)
        self.sync = GoogleCalendarSync.objects.create(pk=source_sync.pk, user=self.user, session=self.session)
        self.assertNotEqual(self.sync.created_at, source_sync.created_at)
        successor, successor_args = self._accepted("calendar")
        self._assert_waiting(successor, successor_args)
        sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker("calendar").run(*args), "inactive-job")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
        self._expire_job(job)
        self.assertFalse(AsyncJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(GoogleWriteAdmission.objects.filter(job_id=job.pk).exists())
        self.assertFalse(GoogleJobDispatch.objects.filter(job_id=job.pk).exists())
        self._assert_waiting(successor, successor_args)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
        self.assertEqual(GoogleWriteExecution.objects.filter(pk=execution.pk).values().get(), before_execution)
        self.assertEqual(GoogleWriteRequest.objects.filter(pk=request.pk).values().get(), before_request)

    def test_session_delete_before_unknown_receipt(self):
        self._run_unknown("session", True)

    def test_session_unknown_receipt_before_delete(self):
        self._run_unknown("session", False)

    def test_sync_delete_before_unknown_receipt(self):
        self._run_unknown("sync", True)

    def test_sync_unknown_receipt_before_delete(self):
        self._run_unknown("sync", False)

    def test_worker_error_is_propagated_and_fixture_waits_are_released(self):
        with patch.object(self._worker("calendar"), "run", side_effect=RuntimeError("Synthetic worker failure")):
            self.assertRaisesRegex(RuntimeError, "Synthetic worker failure", self._run_unknown, "session", True)
        self.assertFalse(GoogleWriteExecution.objects.exists())
        self.assertFalse(GoogleCalendarSync.objects.exists())


class GoogleTargetDeletionConcurrencyCiTest(SimpleTestCase):
    def test_production_database_job_selects_target_deletion_races(self):
        workflow = (Path(settings.BASE_DIR) / ".github/workflows/django-ci.yml").read_text(encoding="utf-8")
        production_job = workflow.split("  production-database:", 1)[1].split("  playwright:", 1)[0]
        self.assertIn("schedules/test_google_target_deletion_concurrency.py", production_job)
