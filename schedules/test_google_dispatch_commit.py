from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.db import DatabaseError, close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from schedules import google_dispatch_outbox as outbox
from schedules import tasks
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleDispatchCommitTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _dispatch_current_job(self, route):
        before = list(AsyncJob.objects.values_list("pk", flat=True))
        response = self._dispatch(route)
        if response is None:
            job = AsyncJob.objects.exclude(pk__in=before).get()
        else:
            job = AsyncJob.objects.get(pk=response.data["job_id"])
        return job, response

    def test_outer_commit_checks_the_accepted_job_when_creation_times_tie(self):
        # A clock's resolution is not a job identity or an ordering guarantee.
        field = AsyncJob._meta.get_field("created_at")
        with patch.object(field, "_get_default", return_value=timezone.now()):
            self.test_all_producers_wait_for_outer_commit_without_claiming_delivery()
        self.assertEqual(AsyncJob.objects.values("created_at").distinct().count(), 1)
        self.assertEqual(AsyncJob.objects.count(), 7)

    def test_all_producers_wait_for_outer_commit_without_claiming_delivery(self):
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                mode = self._mode(route)
                broker = stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                delay = stack.enter_context(
                    patch.object(self._worker(mode), "delay", return_value=SimpleNamespace(id="committed-task"))
                )
                with transaction.atomic():
                    with transaction.atomic():
                        job, response = self._dispatch_current_job(route)
                    self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                    self.assertEqual(job.error, "")
                    self.assertEqual(job.celery_task_id, "")
                    if response is not None:
                        self.assertIs(response.data["queued"], False)
                    broker.assert_not_called()
                    delay.assert_not_called()
                delay.assert_called_once()
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertEqual(job.celery_task_id, "committed-task")

    def test_all_producers_discard_delivery_on_outer_rollback(self):
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                mode = self._mode(route)
                jobs_before = list(AsyncJob.objects.values())
                sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                broker = stack.enter_context(patch.object(tasks, "_broker_available"))
                delay = stack.enter_context(patch.object(self._worker(mode), "delay"))
                with transaction.atomic():
                    self._dispatch(route)
                    transaction.set_rollback(True)
                broker.assert_not_called()
                delay.assert_not_called()
                self.assertEqual(list(AsyncJob.objects.values()), jobs_before)
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)

    def test_nested_rollback_discards_only_its_delivery_callback(self):
        with (
            patch.object(tasks, "_broker_available", return_value=True),
            patch.object(
                tasks.sync_google_calendar, "delay", return_value=SimpleNamespace(id="outer-committed-task")
            ) as delay,
        ):
            with transaction.atomic():
                outer = self._dispatch("calendar")
                with transaction.atomic():
                    inner = self._dispatch("calendar")
                    transaction.set_rollback(True)
                delay.assert_not_called()
            delay.assert_called_once_with(self.sync.pk, str(outer.data["job_id"]))
            self.assertFalse(AsyncJob.objects.filter(pk=inner.data["job_id"]).exists())

    def test_deferred_broker_or_publish_failure_retains_pending_intent_after_commit_on_all_routes(self):
        for route in self.routes:
            for failure in ("broker", "publish"):
                with self.subTest(route=route, failure=failure), ExitStack() as stack:
                    mode = self._mode(route)
                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=failure != "broker"))
                    delay = stack.enter_context(
                        patch.object(self._worker(mode), "delay", side_effect=RuntimeError("synthetic private failure"))
                    )
                    with transaction.atomic():
                        job, _ = self._dispatch_current_job(route)
                        self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                        delay.assert_not_called()
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                    self.assertIsNone(job.started_at)
                    self.assertIsNone(job.finished_at)
                    self.assertEqual(job.error, "")
                    delivery = GoogleJobDispatch.objects.get(job=job)
                    self.assertEqual(delivery.state, GoogleJobDispatch.State.PENDING)
                    self.assertEqual(delivery.attempt_count, 1)
                    self.assertGreater(delivery.next_attempt_at, timezone.now())
                    if mode == "calendar":
                        self.sync.refresh_from_db()
                        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.PENDING)
                        self.assertEqual(self.sync.last_error, "")

    def test_changed_or_missing_job_is_not_published_after_commit(self):
        for mode in ("calendar", "sheets"):
            for change in (
                "deleted",
                "expired",
                "owner",
                "type",
                "running",
                "failed",
                "succeeded",
                "uncertain",
                "started",
            ):
                with self.subTest(mode=mode, change=change), ExitStack() as stack:
                    broker = stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    delay = stack.enter_context(patch.object(self._worker(mode), "delay"))
                    with transaction.atomic():
                        job, _ = self._dispatch_current_job(mode)
                        if change == "deleted":
                            job.delete()
                        else:
                            values = {
                                "expired": {"expires_at": timezone.now() - timedelta(seconds=1)},
                                "owner": {"owner_id": self.other.pk},
                                "type": {"job_type": "unknown"},
                                "started": {"started_at": timezone.now()},
                            }.get(change, {"status": change})
                            AsyncJob.objects.filter(pk=job.pk).update(**values)
                        before = list(AsyncJob.objects.values())
                        sync_before = list(GoogleCalendarSync.objects.values())
                    broker.assert_not_called()
                    delay.assert_not_called()
                    self.assertEqual(list(AsyncJob.objects.values()), before)
                    self.assertEqual(list(GoogleCalendarSync.objects.values()), sync_before)

    def test_sheet_arguments_are_frozen_at_registration_not_mutated_by_caller(self):
        job, args = self._queue("sheets")
        expected = deepcopy(args)
        with (
            patch.object(tasks, "_broker_available", return_value=True),
            patch.object(
                tasks.export_google_sheet, "delay", return_value=SimpleNamespace(id="frozen-sheet-task")
            ) as delay,
        ):
            with transaction.atomic():
                self.assertIsNone(tasks.queue_google_sheet_export(*args))
                args[-1][0][0] = "changed after registration"
                args[-1].append(["unexpected private row"])
                delay.assert_not_called()
            delay.assert_called_once_with(*expected)
        job.refresh_from_db()
        self.assertEqual(job.celery_task_id, "frozen-sheet-task")

    def test_eager_delivery_also_waits_for_commit_and_runs_once(self):
        job, args = self._queue("calendar")
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True), ExitStack() as stack:
            broker = stack.enter_context(patch.object(tasks, "_broker_available"))
            sends, _ = self._sends(stack)
            stack.enter_context(
                patch.object(
                    tasks.sync_google_calendar, "delay", side_effect=lambda *a: self._worker("calendar").run(*a)
                )
            )
            with transaction.atomic():
                self.assertIsNone(tasks.queue_google_calendar_sync(*args))
                for send in sends.values():
                    send.assert_not_called()
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
            self.assertEqual(sum(send.call_count for send in sends.values()), 1)
            broker.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_missing_job_never_registers_a_commit_delivery(self):
        job, args = self._queue("calendar")
        job.delete()
        with patch.object(tasks.sync_google_calendar, "delay") as delay, transaction.atomic():
            self.assertIs(tasks.queue_google_calendar_sync(*args), False)
        delay.assert_not_called()

    def test_manual_uncommitted_transaction_is_not_published(self):
        job, args = self._queue("calendar")
        try:
            connection.set_autocommit(False)
            with patch.object(tasks.sync_google_calendar, "delay") as delay:
                self.assertIs(tasks.queue_google_calendar_sync(*args), False)
                delay.assert_not_called()
        finally:
            connection.rollback()
            connection.set_autocommit(True)
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.QUEUED)

    def test_committed_failure_recording_error_is_private_and_does_not_raise_after_commit(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                stack.enter_context(patch.object(tasks, "_broker_available", return_value=False))
                stack.enter_context(patch.object(outbox, "_finish", side_effect=DatabaseError("private-db-value")))
                with self.assertLogs("schedules.tasks", level="WARNING") as logs:
                    with transaction.atomic():
                        job, _ = self._dispatch_current_job(mode)
                self.assertNotIn("private-db-value", " ".join(logs.output))
                self.assertIn("Unable to finish Google dispatch after database commit.", " ".join(logs.output))
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)

    def test_lost_commit_publish_response_cannot_overwrite_worker_or_recreated_sync(self):
        for mode in ("calendar", "sheets"):
            for outcome in ("running", "failed", "succeeded", "recreated-sync"):
                with self.subTest(mode=mode, outcome=outcome), ExitStack() as stack:
                    observed = []

                    def publish(*args):
                        job, sync = self._observe(mode, args)
                        if outcome == "recreated-sync":
                            original_pk, original_created = sync.pk, sync.created_at
                            sync.delete()
                            GoogleCalendarSync.objects.create(
                                pk=original_pk,
                                user=self.user,
                                session=self.session,
                                created_at=original_created + timedelta(seconds=1),
                                last_error="新しい同期の記録",
                            )
                        else:
                            job.mark_running(39)
                            if outcome == "failed":
                                job.mark_failed("worker側の失敗")
                            elif outcome == "succeeded":
                                job.mark_succeeded({"retained": True})
                        observed.append(
                            (
                                job.pk,
                                AsyncJob.objects.filter(pk=job.pk).values().get(),
                                GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(),
                            )
                        )
                        raise RuntimeError("synthetic lost commit publish response")

                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                    with transaction.atomic():
                        self._dispatch(mode)
                        self.assertEqual(observed, [])
                    job_id, job_before, sync_before = observed[0]
                    self.assertEqual(AsyncJob.objects.filter(pk=job_id).values().get(), job_before)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
                    self.sync.refresh_from_db()

    @skipUnless(connection.vendor == "postgresql", "PostgreSQL独立connectionのcommit可視性検証")
    def test_independent_worker_reads_committed_job_before_first_delivery(self):
        def read(job_id):
            close_old_connections()
            try:
                return AsyncJob.objects.filter(pk=job_id).exists()
            finally:
                close_old_connections()

        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ThreadPoolExecutor(max_workers=1) as pool, ExitStack() as stack:
                observed = []

                def publish(*args):
                    observed.append(pool.submit(read, args[0 if mode == "sheets" else 1]).result(timeout=5))
                    return SimpleNamespace(id="independently-visible-task")

                stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                with transaction.atomic():
                    job, _ = self._dispatch_current_job(mode)
                    self.assertFalse(pool.submit(read, str(job.pk)).result(timeout=5))
                    self.assertEqual(observed, [])
                self.assertEqual(observed, [True])
