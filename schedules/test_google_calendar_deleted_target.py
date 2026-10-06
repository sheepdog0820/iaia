from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

import requests
from celery.exceptions import Retry
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from schedules import tasks
from schedules.google_job_lifecycle import GOOGLE_EXECUTION_UNCERTAIN_MESSAGE
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleCalendarDeletedTargetFixtures(GoogleJobStartFixtures):
    message = (
        "Google Calendarの同期情報が削除されたか変更されました。"
        "予定が変更されている可能性があるため、Google Calendarを確認してください。"
    )

    def _prepare(self, mode):
        self.sync, _ = GoogleCalendarSync.objects.get_or_create(user=self.user, session=self.session)
        self.sync.external_event_id = "known-deleted-target" if mode in ("update", "cancel") else ""
        self.sync.save(update_fields=["external_event_id"])
        self.session.status = "cancelled" if mode == "cancel" else "planned"
        self.session.save(update_fields=["status"])
        return self._queue("calendar")

    def _sends(self, stack):
        sends, token = super()._sends(stack)
        sends["put"].side_effect = self.event_response
        retry = stack.enter_context(patch.object(tasks.sync_google_calendar, "retry", side_effect=Retry()))
        return sends, token, retry

    def _remove(self):
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).delete()

    def _assert_stopped(self, job, result, retry, message=None):
        self.assertEqual(result, "inactive-job")
        retry.assert_not_called()
        self.assertFalse(GoogleCalendarSync.objects.filter(pk=self.sync.pk).exists())
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(job.error, message or self.message)
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["error"], job.error)


class GoogleCalendarDeletedTargetTest(GoogleCalendarDeletedTargetFixtures, TestCase):
    def test_deleted_target_after_claim_stops_before_token_or_http(self):
        for mode in ("create", "update", "cancel"):
            with self.subTest(mode=mode), transaction.atomic(), ExitStack() as stack:
                job, args = self._prepare(mode)
                sends, token, retry = self._sends(stack)
                original = tasks.claim_google_job_start

                def claim(job):
                    claimed = original(job)
                    self._remove()
                    return claimed

                stack.enter_context(patch.object(tasks, "claim_google_job_start", side_effect=claim))
                self._assert_stopped(job, tasks.sync_google_calendar.run(*args), retry)
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()

    def test_deleted_target_during_token_or_last_credential_check_never_sends(self):
        for mode in ("create", "update", "cancel"):
            for phase in ("token", "credential"):
                with self.subTest(mode=mode, phase=phase), transaction.atomic(), ExitStack() as stack:
                    job, args = self._prepare(mode)
                    sends, token, retry = self._sends(stack)

                    def remove(*args):
                        self._remove()
                        return "isolated-token" if phase == "token" else True

                    if phase == "token":
                        token.side_effect = remove
                    else:
                        stack.enter_context(patch.object(tasks, "google_credential_is_current", side_effect=remove))
                    self._assert_stopped(job, tasks.sync_google_calendar.run(*args), retry)
                    for send in sends.values():
                        send.assert_not_called()

    def test_deletion_between_requests_stops_update_cancel_and_conflict_followup(self):
        for mode in ("update", "cancel", "conflict-post", "conflict-get"):
            with self.subTest(mode=mode), transaction.atomic(), ExitStack() as stack:
                job, args = self._prepare(mode)
                sends, _, retry = self._sends(stack)

                def post(url, **kwargs):
                    if mode == "conflict-post":
                        self._remove()
                    return self.response(409, {})

                def fetch(url, **kwargs):
                    response = self.event_response(url, **kwargs)
                    self._remove()
                    return response

                sends["post"].side_effect = post
                sends["get"].side_effect = fetch
                self._assert_stopped(job, tasks.sync_google_calendar.run(*args), retry)
                self.assertEqual(sends["post"].call_count, int(mode.startswith("conflict")))
                self.assertEqual(sends["get"].call_count, int(mode != "conflict-post"))
                sends["put"].assert_not_called()
                sends["delete"].assert_not_called()

    def test_accepted_last_write_never_recreates_deleted_sync_or_retries(self):
        for mode, method in (("create", "post"), ("update", "put"), ("cancel", "delete")):
            with self.subTest(mode=mode), transaction.atomic(), ExitStack() as stack:
                job, args = self._prepare(mode)
                sends, _, retry = self._sends(stack)

                def send(url, **kwargs):
                    response = (
                        self.response(200, {"id": kwargs["json"]["id"]})
                        if method == "post"
                        else self.event_response(url, **kwargs)
                    )
                    if method == "delete":
                        response = self.response(204, {})
                    self._remove()
                    return response

                sends[method].side_effect = send
                self._assert_stopped(job, tasks.sync_google_calendar.run(*args), retry)
                sends[method].assert_called_once()

    def test_deleted_target_during_failure_finishes_without_save_error_or_retry(self):
        reasons = {
            "authorization": tasks.GOOGLE_CALENDAR_NOT_AUTHORIZED_MESSAGE,
            "refresh": "合成token取得失敗",
            "http": tasks.GOOGLE_CALENDAR_DELIVERY_FAILED_MESSAGE,
            "response": "Google Calendarの応答形式を確認できません。連携状態を確認してください。",
            "undated": "開催日時が未設定のセッションはGoogle Calendarへ同期できません。",
        }
        for phase, message in reasons.items():
            with self.subTest(phase=phase), transaction.atomic(), ExitStack() as stack:
                if phase == "undated":
                    self.session.date = None
                    self.session.save(update_fields=["date"])
                job, args = self._prepare("create")
                sends, token, retry = self._sends(stack)

                def fail(*args, **kwargs):
                    self._remove()
                    if phase == "refresh":
                        raise ValueError(message)
                    if phase == "http":
                        raise requests.Timeout("合成の非公開応答喪失")
                    if phase == "response":
                        return self.response(200, [])
                    return None if phase == "authorization" else "isolated-token"

                if phase == "authorization":
                    stack.enter_context(patch.object(tasks, "_google_calendar_sync_integration", side_effect=fail))
                elif phase in ("refresh", "undated"):
                    token.side_effect = fail
                else:
                    sends["post"].side_effect = fail
                result = tasks.sync_google_calendar.run(*args)
                if phase in ("http", "response"):
                    # Deleting the local target does not undo a possibly accepted remote write.
                    self.assertEqual(result, "uncertain")
                    retry.assert_not_called()
                    self.assertFalse(GoogleCalendarSync.objects.filter(pk=self.sync.pk).exists())
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.UNCERTAIN)
                    self.assertEqual(job.error, GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
                    self.assertIsNotNone(job.finished_at)
                    count = AsyncJob.objects.count()
                    response = self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk}))
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(AsyncJob.objects.count(), count)
                else:
                    self._assert_stopped(job, result, retry, message)

    def test_replaced_same_pk_sync_is_not_used_or_overwritten(self):
        for phase in ("claim", "accepted"):
            with self.subTest(phase=phase), transaction.atomic(), ExitStack() as stack:
                job, args = self._prepare("create")
                sends, token, retry = self._sends(stack)
                saved = []
                original = tasks.claim_google_job_start

                def replace():
                    self._remove()
                    GoogleCalendarSync.objects.create(
                        pk=self.sync.pk,
                        user=self.user,
                        session=self.session,
                        created_at=self.sync.created_at + timedelta(seconds=1),
                        external_event_id="replacement-event",
                        last_error="新しい同期の記録",
                    )
                    saved.append(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get())

                def claim(job):
                    result = original(job)
                    replace()
                    return result

                def send(url, **kwargs):
                    replace()
                    return self.response(200, {"id": kwargs["json"]["id"]})

                if phase == "claim":
                    stack.enter_context(patch.object(tasks, "claim_google_job_start", side_effect=claim))
                else:
                    sends["post"].side_effect = send
                self.assertEqual(tasks.sync_google_calendar.run(*args), "inactive-job")
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), saved[0])
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(job.error, self.message)
                retry.assert_not_called()
                self.assertEqual(sends["post"].call_count, int(phase == "accepted"))
                self.assertEqual(token.call_count, int(phase == "accepted"))

    def test_normal_current_targets_keep_successful_results(self):
        for mode in ("create", "update", "cancel"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._prepare(mode)
                _, _, retry = self._sends(stack)
                created = self.sync.created_at
                self.assertEqual(tasks.sync_google_calendar.run(*args), "deleted" if mode == "cancel" else "synced")
                self.sync.refresh_from_db()
                job.refresh_from_db()
                self.assertEqual(self.sync.created_at, created)
                self.assertIsNotNone(self.sync.synced_at)
                self.assertEqual(self.sync.last_error, "")
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)
                self.assertEqual(job.result["external_event_id"], self.sync.external_event_id)
                retry.assert_not_called()


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の同期情報削除競合検証")
class GoogleCalendarDeletedTargetConcurrencyTest(GoogleCalendarDeletedTargetFixtures, TransactionTestCase):
    def test_committed_delete_while_real_worker_waits_stops_send_or_save(self):
        for phase in ("token", "http"):
            with self.subTest(phase=phase), ExitStack() as stack:
                job, args = self._prepare("create")
                sends, token, retry = self._sends(stack)
                entered = Event()
                release = Event()

                def wait(*args, **kwargs):
                    entered.set()
                    self.assertTrue(release.wait(timeout=5), "合成の削除競合待機が終了しませんでした。")
                    return "isolated-token" if phase == "token" else self.response(200, {"id": kwargs["json"]["id"]})

                def run():
                    close_old_connections()
                    try:
                        return tasks.sync_google_calendar.run(*args)
                    finally:
                        close_old_connections()

                if phase == "token":
                    token.side_effect = wait
                else:
                    sends["post"].side_effect = wait
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(run)
                    try:
                        self.assertTrue(entered.wait(timeout=5))
                        self._remove()  # Separate connection commits while the worker is outside a DB transaction.
                    finally:
                        release.set()
                    result = future.result(timeout=10)
                self._assert_stopped(job, result, retry)
                self.assertEqual(sends["post"].call_count, int(phase == "http"))
