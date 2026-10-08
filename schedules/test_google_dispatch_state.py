from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError, close_old_connections, connection
from django.db.models.query import QuerySet
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from schedules import tasks
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch, TRPGSession
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleDispatchStateFixtures(GoogleJobStartFixtures):
    routes = ("calendar", "sheets", "retry-calendar", "retry-sheets", "session")

    def _fresh_dispatch_target(self):
        # Real commit callbacks must not be hidden behind a rollback savepoint.
        # Keep earlier queued/running journals intact and use new owned targets.
        self.session = TRPGSession.objects.create(
            title="独立した配送状態試験",
            group=self.session.group,
            created_by=self.user,
            gm=self.user,
            date=timezone.now() + timedelta(days=1),
        )
        self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)
        self.fixture_sheet_id = f"isolated-dispatch-{uuid4().hex}"

    def _dispatch(self, route):
        if route.startswith("retry-"):
            original, _ = self._queue(route.removeprefix("retry-"))
            original.mark_failed("元ジョブの失敗")
            before = AsyncJob.objects.filter(pk=original.pk).values().get()
            response = self.api.post(reverse("async-job-retry", kwargs={"pk": original.pk}))
            self.assertEqual(response.status_code, 202)
            before["payload"] = {**before["payload"], "google_retry_successor": str(response.data["job_id"])}
            self.assertEqual(AsyncJob.objects.filter(pk=original.pk).values().get(), before)
        elif route == "calendar":
            response = self.api.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
        elif route == "sheets":
            response = self.api.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": getattr(self, "fixture_sheet_id", "isolated-dispatch-state")},
                format="json",
            )
        else:
            tasks.schedule_session_google_syncs(self.session)
            return None
        self.assertEqual(response.status_code, 202)
        return response

    def _mode(self, route):
        return "sheets" if "sheets" in route else "calendar"

    def _observe(self, mode, args):
        job = AsyncJob.objects.get(pk=args[0 if mode == "sheets" else 1])
        return job, GoogleCalendarSync.objects.get(pk=self.sync.pk)

    def _assert_saved(self, job, before, sync_before):
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], before["status"])
        self.assertEqual(response.data["error"], before["error"])
        self.assertEqual(response.data["result"], before["result"])


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleDispatchStateTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def test_publish_exception_preserves_started_completed_and_worker_failed_jobs_on_all_routes(self):
        for route in self.routes:
            for outcome in ("running", "succeeded", "failed"):
                with self.subTest(route=route, outcome=outcome), ExitStack() as stack:
                    self._fresh_dispatch_target()
                    mode = self._mode(route)
                    self.sync.external_event_id = ""
                    self.sync.save(update_fields=["external_event_id"])
                    self._sends(stack)
                    observed = []

                    def publish(*args):
                        job, sync = self._observe(mode, args)
                        if outcome == "succeeded":
                            self.assertEqual(
                                self._worker(mode).run(*args), "exported" if mode == "sheets" else "synced"
                            )
                        else:
                            job.mark_running(39)
                            if outcome == "failed":
                                job.mark_failed("実行先の処理に失敗しました。")
                                if mode == "calendar":
                                    sync.status = GoogleCalendarSync.Status.FAILED
                                    sync.last_error = job.error
                                    sync.save(update_fields=["status", "last_error", "updated_at"])
                        observed.append(
                            (
                                job,
                                AsyncJob.objects.filter(pk=job.pk).values().get(),
                                GoogleCalendarSync.objects.filter(pk=sync.pk).values().get(),
                            )
                        )
                        raise RuntimeError("Synthetic publish response failure")

                    stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    response = self._dispatch(route)
                    if response is not None:
                        self.assertFalse(response.data["queued"])
                    self.assertEqual(len(observed), 1)
                    self._assert_saved(*observed[0])
                    if route == "calendar":
                        # Response is constructed before the commit callback runs.
                        self.assertEqual(response.data["sync_status"], GoogleCalendarSync.Status.PENDING)

    def test_accepted_publish_is_not_reported_failed_when_task_id_persistence_raises(self):
        original_update = QuerySet.update
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                mode = self._mode(route)
                observed = []

                def save(query, **values):
                    if "celery_task_id" in values:
                        self.assertEqual(set(values), {"celery_task_id"})
                        raise DatabaseError("Synthetic task ID persistence failure")
                    return original_update(query, **values)

                def publish(*args):
                    job, sync = self._observe(mode, args)
                    observed.append(
                        (
                            job,
                            AsyncJob.objects.filter(pk=job.pk).values().get(),
                            GoogleCalendarSync.objects.filter(pk=sync.pk).values().get(),
                        )
                    )
                    return SimpleNamespace(id="accepted-task-fixture")

                stack.enter_context(patch.object(QuerySet, "update", new=save))
                stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                response = self._dispatch(route)
                if response is not None:
                    self.assertFalse(response.data["queued"])
                self._assert_saved(*observed[0])

    def test_successful_publish_saves_task_id_and_keeps_normal_queued_state(self):
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                mode = self._mode(route)
                stack.enter_context(
                    patch.object(self._worker(mode), "delay", return_value=SimpleNamespace(id="saved-task-fixture"))
                )
                stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                response = self._dispatch(route)
                job = AsyncJob.objects.first()
                self.assertEqual(job.celery_task_id, "saved-task-fixture")
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertIsNone(job.started_at)
                self.assertIsNone(job.finished_at)
                self.assertEqual(job.error, "")
                if response is not None:
                    self.assertFalse(response.data["queued"])

    def test_unavailable_broker_retains_durable_intent_without_failing_or_creating_another_job(self):
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                mode = self._mode(route)
                delay = stack.enter_context(patch.object(self._worker(mode), "delay"))
                stack.enter_context(patch.object(tasks, "_broker_available", return_value=False))
                response = self._dispatch(route)
                delay.assert_not_called()
                job = AsyncJob.objects.first()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertIsNone(job.started_at)
                self.assertIsNone(job.finished_at)
                self.assertEqual(job.error, "")
                delivery = GoogleJobDispatch.objects.get(job=job)
                self.assertEqual(delivery.state, GoogleJobDispatch.State.PENDING)
                self.assertEqual(delivery.attempt_count, 1)
                self.assertGreater(delivery.next_attempt_at, timezone.now())
                self.assertTrue(delivery.ciphertext)
                if mode == "calendar":
                    self.sync.refresh_from_db()
                    self.assertEqual(self.sync.status, GoogleCalendarSync.Status.PENDING)
                    self.assertEqual(self.sync.last_error, "")
                if response is not None:
                    self.assertFalse(response.data["queued"])

    def test_publish_exception_after_job_or_sync_deletion_does_not_recreate_or_save_missing_rows(self):
        for route in self.routes:
            for target in ("job", "sync"):
                with self.subTest(route=route, target=target), ExitStack() as stack:
                    mode = self._mode(route)
                    observed = []

                    def publish(*args):
                        job, sync = self._observe(mode, args)
                        observed.append(job.pk)
                        (job if target == "job" else sync).delete()
                        raise RuntimeError("Synthetic deletion before publish response")

                    stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    self._dispatch(route)
                    if target == "job":
                        self.assertFalse(AsyncJob.objects.filter(pk=observed[0]).exists())
                    else:
                        self.assertFalse(GoogleCalendarSync.objects.filter(pk=self.sync.pk).exists())
                        self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)

    def test_expired_and_previously_started_queued_jobs_are_not_overwritten(self):
        for mode in ("sheets", "calendar"):
            for change in ("expired", "started"):
                with self.subTest(mode=mode, change=change), ExitStack() as stack:
                    observed = []

                    def publish(*args):
                        job, sync = self._observe(mode, args)
                        if change == "expired":
                            job.expires_at = timezone.now() - timedelta(seconds=1)
                            job.save(update_fields=["expires_at"])
                        else:
                            job.started_at = timezone.now()
                            job.save(update_fields=["started_at"])
                        observed.append(
                            (
                                job,
                                AsyncJob.objects.filter(pk=job.pk).values().get(),
                                GoogleCalendarSync.objects.filter(pk=sync.pk).values().get(),
                            )
                        )
                        raise RuntimeError("Synthetic state change before publish response")

                    stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    self._dispatch(mode)
                    self._assert_saved(*observed[0])

    def test_changed_job_owner_or_type_preserves_both_job_and_sync(self):
        for mode in ("sheets", "calendar"):
            for change in ("owner", "type"):
                with self.subTest(mode=mode, change=change), ExitStack() as stack:
                    observed = []

                    def publish(*args):
                        job, sync = self._observe(mode, args)
                        field, value = ("owner_id", self.other.pk) if change == "owner" else ("job_type", "unknown")
                        AsyncJob.objects.filter(pk=job.pk).update(**{field: value})
                        observed.append(
                            (
                                job,
                                AsyncJob.objects.filter(pk=job.pk).values().get(),
                                GoogleCalendarSync.objects.filter(pk=sync.pk).values().get(),
                            )
                        )
                        raise RuntimeError("Synthetic dispatch identity change")

                    stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                    stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                    self._dispatch(mode)
                    job, before, sync_before = observed[0]
                    self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)

    def test_calendar_failure_does_not_overwrite_completed_or_recreated_sync(self):
        for change in ("completed", "recreated"):
            with self.subTest(change=change), ExitStack() as stack:
                observed = []

                def publish(*args):
                    job, sync = self._observe("calendar", args)
                    if change == "recreated":
                        original_pk, original_created = sync.pk, sync.created_at
                        sync.delete()
                        sync = GoogleCalendarSync.objects.create(
                            pk=original_pk,
                            user=self.user,
                            session=self.session,
                            created_at=original_created + timedelta(seconds=1),
                            last_error="新同期の記録",
                        )
                    else:
                        sync.status = GoogleCalendarSync.Status.SYNCED
                        sync.external_event_id = "retained-completed-event"
                        sync.save(update_fields=["status", "external_event_id", "updated_at"])
                    observed.append((job, GoogleCalendarSync.objects.filter(pk=sync.pk).values().get()))
                    raise RuntimeError("Synthetic target change before publish response")

                stack.enter_context(patch.object(tasks.sync_google_calendar, "delay", side_effect=publish))
                stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                response = self._dispatch("calendar")
                job, sync_before = observed[0]
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
                self.assertEqual(response.data["sync_status"], GoogleCalendarSync.Status.PENDING)
                self.sync.refresh_from_db()


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の投入応答とworker開始の競合検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleDispatchStateConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def test_real_worker_starts_or_finishes_before_publish_response_is_lost(self):
        for mode in ("sheets", "calendar"):
            for phase in ("running", "finished"):
                with self.subTest(mode=mode, phase=phase), ExitStack() as stack:
                    reached, release = Event(), Event()
                    self.sync.external_event_id = ""
                    self.sync.save(update_fields=["external_event_id"])
                    sends, token = self._sends(stack)
                    observed, futures = [], []

                    def read(user):
                        reached.set()
                        self.assertTrue(release.wait(timeout=5))
                        return "isolated-token"

                    def run(args):
                        close_old_connections()
                        try:
                            return self._worker(mode).run(*args)
                        finally:
                            close_old_connections()

                    with ThreadPoolExecutor(max_workers=1) as pool:

                        def publish(*args):
                            job, sync = self._observe(mode, args)
                            future = pool.submit(run, args)
                            futures.append(future)
                            if phase == "running":
                                self.assertTrue(reached.wait(timeout=5))
                            else:
                                self.assertEqual(
                                    future.result(timeout=10), "exported" if mode == "sheets" else "synced"
                                )
                            observed.append(
                                (
                                    job,
                                    AsyncJob.objects.filter(pk=job.pk).values().get(),
                                    GoogleCalendarSync.objects.filter(pk=sync.pk).values().get(),
                                )
                            )
                            raise RuntimeError("Synthetic response lost after independent worker")

                        if phase == "running":
                            token.side_effect = read
                        stack.enter_context(patch.object(self._worker(mode), "delay", side_effect=publish))
                        stack.enter_context(patch.object(tasks, "_broker_available", return_value=True))
                        try:
                            response = self._dispatch(mode)
                            self.assertFalse(response.data["queued"])
                            self._assert_saved(*observed[0])
                        finally:
                            release.set()
                        self.assertEqual(futures[0].result(timeout=10), "exported" if mode == "sheets" else "synced")
                    self.assertEqual(sum(send.call_count for send in sends.values()), 1)
                    observed[0][0].refresh_from_db()
                    self.assertEqual(observed[0][0].status, AsyncJob.Status.SUCCEEDED)
