from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from schedules import google_dispatch_outbox as outbox
from schedules import tasks
from schedules.google_job_lifecycle import (
    GoogleJobInactive,
    claim_google_job_start,
    fail_google_job,
    fail_unstarted_google_dispatch,
    google_job_can_start,
    require_running_google_job,
    set_google_job_progress,
    succeed_google_job,
    uncertain_google_job,
)
from schedules.google_target_execution import execution_scope, finish_execution
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch, GoogleWriteExecution, GoogleWriteRequest
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleRetrySupersessionFixtures(GoogleJobStartFixtures):
    message = "このジョブは既に再試行を受け付けています。ジョブ一覧で新しい処理の結果を確認してください。"

    def _failed(self, mode):
        job, args = self._queue(mode)
        job.mark_failed("以前の失敗記録")
        return job, args

    def _retry(self, mode, job, client=None):
        name = "queue_google_sheet_export" if mode == "sheets" else "queue_google_calendar_sync"
        with patch(f"schedules.job_views.{name}", return_value=True) as queue:
            response = (client or self.api).post(reverse("async-job-retry", kwargs={"pk": job.pk}))
        return response, queue


class GoogleRetrySupersessionTest(GoogleRetrySupersessionFixtures, TestCase):
    def test_old_failed_message_cannot_resume_after_manual_retry_acceptance(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args = self._failed(mode)
                response, queue = self._retry(mode, job)
                self.assertEqual(response.status_code, 202)
                successor = AsyncJob.objects.get(pk=response.data["job_id"])
                self.assertEqual(successor.payload["retry_of"], str(job.pk))
                self._refuse_unchanged(mode, job, args)
                self.assertEqual(successor.status, AsyncJob.Status.QUEUED)
                queue.assert_called_once()

    def test_repeated_manual_retry_never_creates_or_dispatches_another_successor(self):
        for mode in ("calendar", "sheets"):
            for state in AsyncJob.Status.values:
                with self.subTest(mode=mode, state=state):
                    job, _ = self._failed(mode)
                    first, _ = self._retry(mode, job)
                    self.assertEqual(first.status_code, 202)
                    successor = AsyncJob.objects.get(pk=first.data["job_id"])
                    successor.status = state
                    successor.save(update_fields=["status"])
                    jobs = list(AsyncJob.objects.order_by("pk").values())
                    syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
                    response, queue = self._retry(mode, job)
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(response.data, {"detail": self.message})
                    queue.assert_not_called()
                    self.assertEqual(list(AsyncJob.objects.order_by("pk").values()), jobs)
                    self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)

    def test_successor_can_deliver_and_its_failed_job_can_have_its_own_single_retry(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, _ = self._failed(mode)
                first, queue = self._retry(mode, job)
                successor = AsyncJob.objects.get(pk=first.data["job_id"])
                sends, _ = self._sends(stack)
                self.assertEqual(
                    self._worker(mode).run(*queue.call_args.args), "synced" if mode == "calendar" else "exported"
                )
                self.assertEqual(sum(send.call_count for send in sends.values()), 1)
                successor.mark_failed("別の合成失敗")
                second, _ = self._retry(mode, successor)
                self.assertEqual(second.status_code, 202)
                later = AsyncJob.objects.get(pk=second.data["job_id"])
                self.assertEqual(later.payload["retry_of"], str(successor.pk))
                self.assertFalse(google_job_can_start(job))
                self.assertFalse(google_job_can_start(successor))
                self.assertTrue(google_job_can_start(later))

    def test_unrelated_owner_kind_or_original_job_is_not_a_superseding_retry(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                for changes in (
                    {"owner": self.other},
                    {"job_type": "statistics_export"},
                    {"payload": {"retry_of": "different-original"}},
                ):
                    values = {
                        "owner": self.user,
                        "job_type": job.job_type,
                        "payload": {"retry_of": str(job.pk)},
                        "expires_at": job.expires_at,
                    }
                    AsyncJob.objects.create(**{**values, **changes})
                self.assertTrue(google_job_can_start(job))
                response, queue = self._retry(mode, job)
                self.assertEqual(response.status_code, 202)
                queue.assert_called_once()

    def test_claim_rechecks_successor_created_after_initial_start_read(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._failed(mode)
                sends, token = self._sends(stack)
                original = tasks.google_job_can_start

                def read(candidate):
                    allowed = original(candidate)
                    response, _ = self._retry(mode, job)
                    self.assertEqual(response.status_code, 202)
                    return allowed

                stack.enter_context(patch.object(tasks, "google_job_can_start", side_effect=read))
                self.assertEqual(self._worker(mode).run(*args), "inactive-job")
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()

    def test_old_calendar_failure_cannot_overwrite_pending_successor_sync_or_schedule_retry(self):
        self.sync.external_event_id = "known-retry-fixture"
        self.sync.save(update_fields=["external_event_id"])
        job, args = self._failed("calendar")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["get"].side_effect = None
            sends["get"].return_value = self.response(403, {})
            retry = stack.enter_context(patch.object(tasks.sync_google_calendar, "retry"))
            original = tasks.fail_google_job
            accepted = []

            def fail(candidate, error):
                original(candidate, error)
                # This fixture has only a rejected GET, never a write. Model a
                # confirmed closed execution before accepting its successor.
                self.assertFalse(GoogleWriteRequest.objects.filter(execution__job_id_snapshot=job.pk).exists())
                finish_execution(candidate)
                self.assertEqual(
                    GoogleWriteExecution.objects.get(job_id_snapshot=job.pk).state,
                    GoogleWriteExecution.State.FINISHED,
                )
                response, _ = self._retry("calendar", job)
                self.assertEqual(response.status_code, 202)
                accepted.append(response.data["job_id"])

            stack.enter_context(patch.object(tasks, "fail_google_job", side_effect=fail))
            self.assertEqual(tasks.sync_google_calendar.run(*args), "inactive-job")
            retry.assert_not_called()
            self.sync.refresh_from_db()
            self.assertEqual(self.sync.status, GoogleCalendarSync.Status.PENDING)
            self.assertEqual(self.sync.last_error, "")
            self.assertEqual(len(accepted), 1)

    def test_worker_claim_without_successor_preserves_existing_failed_retry_behavior(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                self.assertTrue(claim_google_job_start(job))
                self.assertEqual(job.status, AsyncJob.Status.RUNNING)
                response, queue = self._retry(mode, job)
                self.assertEqual(response.status_code, 400)
                queue.assert_not_called()

    def test_superseded_source_cannot_publish_after_a_legacy_queued_reset(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args = self._failed(mode)
                outbox.persist_google_dispatch(job, list(args))
                response, _ = self._retry(mode, job)
                self.assertEqual(response.status_code, 202)
                AsyncJob.objects.filter(pk=job.pk).update(status=AsyncJob.Status.QUEUED)
                with (
                    patch.object(tasks, "_broker_available", return_value=True),
                    patch.object(
                        self._worker(mode), "delay", return_value=SimpleNamespace(id="isolated-old-source")
                    ) as delay,
                ):
                    self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                delay.assert_not_called()
                delivery = GoogleJobDispatch.objects.get(job=job)
                self.assertEqual(delivery.state, GoogleJobDispatch.State.DISCARDED)
                self.assertEqual(delivery.ciphertext, "")

    def test_superseded_source_cannot_mutate_job_or_sync_after_a_legacy_state_reset(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                with execution_scope():
                    self.assertTrue(claim_google_job_start(job))
                    fail_google_job(job, "合成試行の失敗")
                self.assertEqual(
                    GoogleWriteExecution.objects.get(job_id_snapshot=job.pk).state,
                    GoogleWriteExecution.State.FINISHED,
                )
                response, _ = self._retry(mode, job)
                self.assertEqual(response.status_code, 202)
                AsyncJob.objects.filter(pk=job.pk).update(status=AsyncJob.Status.RUNNING)
                before = AsyncJob.objects.filter(pk=job.pk).values().get()
                for mutate, args in (
                    (require_running_google_job, ()),
                    (set_google_job_progress, (50,)),
                    (fail_google_job, ("上書き不可",)),
                    (succeed_google_job, ({"retained": "上書き不可"},)),
                    (uncertain_google_job, ()),
                ):
                    with self.assertRaises(GoogleJobInactive):
                        mutate(job, *args)
                    self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                AsyncJob.objects.filter(pk=job.pk).update(status=AsyncJob.Status.QUEUED, started_at=None)
                sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                self.assertFalse(fail_unstarted_google_dispatch(job, "上書き不可", self.sync))
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)

    def test_successor_deletion_does_not_revive_source_or_allow_another_retry(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args = self._failed(mode)
                response, _ = self._retry(mode, job)
                self.assertEqual(response.status_code, 202)
                AsyncJob.objects.get(pk=response.data["job_id"]).delete()
                self._refuse_unchanged(mode, job, args)
                response, queue = self._retry(mode, job)
                self.assertEqual(response.status_code, 409)
                queue.assert_not_called()

    def test_saved_successor_marker_is_opaque_private_and_fail_closed_when_malformed(self):
        for marker in (None, "", [], {}, "unrecognized"):
            for mode in ("calendar", "sheets"):
                with self.subTest(mode=mode, marker=marker):
                    job, args = self._failed(mode)
                    job.payload["google_retry_successor"] = marker
                    job.save(update_fields=["payload"])
                    self._refuse_unchanged(mode, job, args)
                    response, queue = self._retry(mode, job)
                    self.assertEqual(response.status_code, 409)
                    queue.assert_not_called()
                    detail = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
                    self.assertNotIn("payload", detail.data)
                    self.assertNotIn("google_retry_successor", detail.data)

    def test_retry_transaction_rollback_restores_source_sync_and_discards_new_job(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                before = AsyncJob.objects.filter(pk=job.pk).values().get()
                syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
                with transaction.atomic():
                    response, _ = self._retry(mode, job)
                    self.assertEqual(response.status_code, 202)
                    self.assertFalse(google_job_can_start(job))
                    transaction.set_rollback(True)
                self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)
                self.assertFalse(AsyncJob.objects.filter(payload__retry_of=str(job.pk)).exists())
                self.assertTrue(google_job_can_start(job))

    def test_legacy_committed_successor_is_recorded_before_duplicate_retry_refusal(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args = self._failed(mode)
                successor = AsyncJob.objects.create(
                    owner=self.user, job_type=job.job_type, payload={"retry_of": str(job.pk)}, expires_at=job.expires_at
                )
                response, queue = self._retry(mode, job)
                self.assertEqual(response.status_code, 409)
                queue.assert_not_called()
                job.refresh_from_db()
                self.assertEqual(job.payload.get("google_retry_successor"), str(successor.pk))
                successor.delete()
                self._refuse_unchanged(mode, job, args)

    def test_legacy_successor_without_marker_prevents_outbox_publication_and_failure_update(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args = self._queue(mode)
                outbox.persist_google_dispatch(job, list(args))
                AsyncJob.objects.create(
                    owner=self.user, job_type=job.job_type, payload={"retry_of": str(job.pk)}, expires_at=job.expires_at
                )
                syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
                with (
                    patch.object(tasks, "_broker_available", return_value=True),
                    patch.object(self._worker(mode), "delay") as delay,
                ):
                    self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                delay.assert_not_called()
                self.assertFalse(fail_unstarted_google_dispatch(job, "上書き不可", self.sync))
                self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)
                delivery = GoogleJobDispatch.objects.get(job=job)
                self.assertEqual(delivery.state, GoogleJobDispatch.State.DISCARDED)
                self.assertEqual(delivery.ciphertext, "")

    def test_non_google_retry_is_not_retired_or_changed_by_google_successor_metadata(self):
        job = AsyncJob.objects.create(
            owner=self.user,
            job_type="statistics_export",
            status=AsyncJob.Status.FAILED,
            payload=[],
            expires_at=timezone.now() + timedelta(days=1),
        )
        AsyncJob.objects.create(
            owner=self.user, job_type=job.job_type, payload={"retry_of": str(job.pk)}, expires_at=job.expires_at
        )
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "この種類のジョブは再試行できません。"})
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の再試行競合検証")
class GoogleRetrySupersessionConcurrencyTest(GoogleRetrySupersessionFixtures, TransactionTestCase):
    def _request(self, mode, job, backend_ids):
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

    def test_two_real_requests_create_one_successor_after_the_source_lock_releases(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                # A held real row lock forces both HTTP handlers to inspect the same source.
                name = "queue_google_sheet_export" if mode == "sheets" else "queue_google_calendar_sync"
                entered = Event()
                release = Event()
                backend_ids = []

                def queued(*args):
                    entered.set()
                    self.assertTrue(release.wait(timeout=10))
                    return True

                with patch(f"schedules.job_views.{name}", side_effect=queued) as queue:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        first = pool.submit(self._request, mode, job, backend_ids)
                        try:
                            self.assertTrue(entered.wait(timeout=10))
                            second = pool.submit(self._request, mode, job, backend_ids)
                            # Release only after the second connection is observed waiting in PostgreSQL.
                            self._observe_retry_lock(backend_ids)
                        finally:
                            release.set()
                        results = [first.result(timeout=10), second.result(timeout=10)]
                self.assertCountEqual(results, [202, 409])
                queue.assert_called_once()
                self.assertEqual(AsyncJob.objects.filter(payload__retry_of=str(job.pk)).count(), 1)

    def _observe_retry_lock(self, backend_ids, timeout=5):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid = ANY(%s) AND wait_event_type='Lock' "
                    "AND query LIKE '%%schedules_asyncjob%%' AND query LIKE '%%FOR UPDATE%%'",
                    [backend_ids],
                )
                if cursor.fetchone()[0]:
                    return
            sleep(0.01)
        self.fail("実再試行のsource行ロック待機を観測できませんでした。")

    def test_lock_observation_timeout_is_bounded(self):
        with self.assertRaisesRegex(AssertionError, "行ロック待機"):
            self._observe_retry_lock([], timeout=0.02)

    def test_worker_claim_waits_for_accepting_retry_then_refuses_old_source(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                backend_ids = []

                def claim():
                    close_old_connections()
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT pg_backend_pid()")
                            backend_ids.append(cursor.fetchone()[0])
                        return claim_google_job_start(job)
                    finally:
                        close_old_connections()

                with ThreadPoolExecutor(max_workers=1) as pool:
                    with transaction.atomic():
                        AsyncJob.objects.select_for_update().get(pk=job.pk)
                        future = pool.submit(claim)
                        self._observe_retry_lock(backend_ids)
                        response, _ = self._retry(mode, job)
                        self.assertEqual(response.status_code, 202)
                    self.assertFalse(future.result(timeout=10))
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)

    def test_retry_waits_for_worker_claim_then_refuses_a_running_source(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                entered = Event()
                release = Event()
                backend_ids = []

                def claim():
                    close_old_connections()
                    try:
                        with transaction.atomic():
                            result = claim_google_job_start(job)
                            entered.set()
                            self.assertTrue(release.wait(timeout=10))
                            return result
                    finally:
                        close_old_connections()

                name = "queue_google_sheet_export" if mode == "sheets" else "queue_google_calendar_sync"
                with patch(f"schedules.job_views.{name}") as queue:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        worker = pool.submit(claim)
                        try:
                            self.assertTrue(entered.wait(timeout=10))
                            request = pool.submit(self._request, mode, job, backend_ids)
                            self._observe_retry_lock(backend_ids)
                        finally:
                            release.set()
                        self.assertTrue(worker.result(timeout=10))
                        self.assertEqual(request.result(timeout=10), 400)
                queue.assert_not_called()
                self.assertFalse(AsyncJob.objects.filter(payload__retry_of=str(job.pk)).exists())
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.RUNNING)
                self.assertNotIn("google_retry_successor", job.payload)


class GoogleRetryTransactionBoundaryTest(GoogleRetrySupersessionFixtures, TransactionTestCase):
    def test_real_outbox_retry_rollback_restores_existing_source_and_discards_callback(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, _ = self._failed(mode)
                before = AsyncJob.objects.filter(pk=job.pk).values().get()
                syncs = list(GoogleCalendarSync.objects.order_by("pk").values())
                with (
                    patch.object(tasks, "_broker_available", return_value=True) as broker,
                    patch.object(self._worker(mode), "delay") as delay,
                ):
                    with transaction.atomic():
                        response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                        self.assertEqual(response.status_code, 202)
                        self.assertFalse(response.data["queued"])
                        successor = AsyncJob.objects.get(pk=response.data["job_id"])
                        recorded = AsyncJob.objects.get(pk=job.pk)
                        self.assertEqual(recorded.payload["google_retry_successor"], str(successor.pk))
                        intent = GoogleJobDispatch.objects.get(job=successor)
                        self.assertEqual(intent.state, GoogleJobDispatch.State.PENDING)
                        self.assertEqual(intent.attempt_count, 0)
                        self.assertTrue(intent.ciphertext.startswith("v1."))
                        self.assertFalse(google_job_can_start(job))
                        transaction.set_rollback(True)
                    broker.assert_not_called()
                    delay.assert_not_called()
                self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                self.assertEqual(list(GoogleCalendarSync.objects.order_by("pk").values()), syncs)
                self.assertFalse(AsyncJob.objects.filter(pk=successor.pk).exists())
                self.assertFalse(GoogleJobDispatch.objects.filter(pk=intent.pk).exists())
                self.assertTrue(google_job_can_start(job))
