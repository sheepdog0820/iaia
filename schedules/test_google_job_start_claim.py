from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from schedules import tasks
from schedules import test_google_sheets_content_binding as content_tests
from schedules.models import AsyncJob, GoogleCalendarSync


class GoogleJobStartFixtures:
    setUp = content_tests.GoogleSheetsContentBindingTest.setUp
    _restore_connection = content_tests.GoogleSheetsContentBindingTest._restore_connection
    _sends = content_tests.GoogleSheetsContentBindingTest._sends
    response = content_tests.GoogleSheetsContentBindingTest.response
    event_response = content_tests.GoogleSheetsContentBindingTest.event_response

    def _queue(self, mode):
        if mode == "sheets":
            return content_tests.GoogleSheetsContentBindingTest._queue(self)
        with patch("schedules.integration_views.queue_google_calendar_sync", return_value=True) as queue:
            response = self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        self.assertEqual(response.status_code, 202)
        queue.assert_called_once()
        return AsyncJob.objects.get(pk=response.data["job_id"]), queue.call_args.args

    def _worker(self, mode):
        return tasks.export_google_sheet if mode == "sheets" else tasks.sync_google_calendar

    def _refuse_unchanged(self, mode, job, args):
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            retry = stack.enter_context(patch.object(self._worker(mode), "retry"))
            self.assertEqual(self._worker(mode).run(*args), "inactive-job")
            token.assert_not_called()
            retry.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)


class GoogleJobStartClaimTest(GoogleJobStartFixtures, TestCase):
    def test_successful_running_and_unknown_jobs_never_reenter_or_change_saved_state(self):
        for mode in ("sheets", "calendar"):
            for state in (AsyncJob.Status.SUCCEEDED, AsyncJob.Status.RUNNING, "unknown"):
                with self.subTest(mode=mode, state=state):
                    job, args = self._queue(mode)
                    job.status = state
                    job.result = {"retained": "以前の非公開結果"}
                    job.error = "以前の記録"
                    job.payload = []  # No failed-target mutation even with a broken saved payload.
                    job.save(update_fields=["status", "result", "error", "payload"])
                    self._refuse_unchanged(mode, job, args)

    def test_expired_jobs_are_unchanged_before_authentication_or_target_validation(self):
        for mode in ("sheets", "calendar"):
            for state in AsyncJob.Status.values:
                with self.subTest(mode=mode, state=state):
                    job, args = self._queue(mode)
                    job.status = state
                    job.expires_at = timezone.now() - timedelta(seconds=1)
                    job.save(update_fields=["status", "expires_at"])
                    self._refuse_unchanged(mode, job, args)

    def test_successful_api_job_sends_once_and_preserves_result_on_redelivery(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                sends, _ = self._sends(stack)
                self.assertEqual(self._worker(mode).run(*args), "exported" if mode == "sheets" else "synced")
                self.assertEqual(sum(send.call_count for send in sends.values()), 1)
            self._refuse_unchanged(mode, job, args)

    def test_reentry_while_first_worker_is_running_cannot_lookup_or_send_again(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                sends, token = self._sends(stack)
                observed = []

                def read(user):
                    # Bound the RED reentry without a fixture-only untested branch.
                    token.side_effect = None
                    observed.append(self._worker(mode).run(*args))
                    return "isolated-token"

                token.side_effect = read
                self.assertEqual(self._worker(mode).run(*args), "exported" if mode == "sheets" else "synced")
                self.assertEqual(observed, ["inactive-job"])
                token.assert_called_once()
                self.assertEqual(sum(send.call_count for send in sends.values()), 1)

    def test_failed_retry_keeps_original_start_but_clears_old_finish_and_error(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                start = timezone.now() - timedelta(minutes=1)
                job.started_at = start
                job.save(update_fields=["started_at"])
                job.mark_failed("以前の通信失敗")
                self._sends(stack)

                def put(url, **kwargs):
                    job.refresh_from_db()
                    self.assertEqual(job.started_at, start)
                    self.assertEqual(job.status, AsyncJob.Status.RUNNING)
                    self.assertIsNone(job.finished_at)
                    self.assertEqual(job.error, "")
                    return self.response(
                        200, {"updatedCells": 0} if mode == "sheets" else {"id": "known-start-fixture"}
                    )

                stack.enter_context(patch("schedules.tasks.requests.put", side_effect=put))
                if mode == "calendar":
                    # A known event uses GET + conditional PUT, exercising a failed job's restart.
                    self.sync.external_event_id = "known-start-fixture"
                    self.sync.save(update_fields=["external_event_id"])
                result = self._worker(mode).run(*args)
                self.assertEqual(result, "exported" if mode == "sheets" else "synced")

    def test_expiry_between_initial_read_and_claim_prevents_first_send(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                sends, token = self._sends(stack)
                original = tasks.google_job_can_start

                def read(*args):
                    result = original(*args)
                    AsyncJob.objects.filter(pk=job.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
                    return result

                stack.enter_context(patch.object(tasks, "google_job_can_start", side_effect=read))
                self.assertEqual(self._worker(mode).run(*args), "inactive-job")
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertIsNone(job.started_at)


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の開始競合検証")
class GoogleJobStartConcurrencyTest(GoogleJobStartFixtures, TransactionTestCase):
    def test_two_real_workers_read_the_same_queued_job_but_only_one_claims_it(self):
        for mode in ("sheets", "calendar"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue(mode)
                sends, _ = self._sends(stack)
                barrier = Barrier(2)
                original = tasks.google_job_can_start

                def read(*args):
                    result = original(*args)
                    barrier.wait(timeout=5)
                    return result

                def run():
                    close_old_connections()
                    try:
                        return self._worker(mode).run(*args)
                    finally:
                        close_old_connections()

                stack.enter_context(patch.object(tasks, "google_job_can_start", side_effect=read))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(run) for _ in range(2)]
                    results = [future.result(timeout=10) for future in futures]
                self.assertCountEqual(results, ["inactive-job", "exported" if mode == "sheets" else "synced"])
                self.assertEqual(sum(send.call_count for send in sends.values()), 1)
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
