from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

import requests
from celery.exceptions import Retry
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules import tasks
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.test_google_job_start_claim import GoogleJobStartFixtures


class GoogleJobActiveGuardTest(GoogleJobStartFixtures, TestCase):
    reasons = ("expired", "deleted", "finished")

    def _sends(self, stack):
        sends, token = super()._sends(stack)
        sends["put"].side_effect = self.event_response
        return sends, token

    def _prepare(self, mode):
        self.session.status = "cancelled" if mode.startswith("cancel") else "planned"
        self.session.save(update_fields=["status"])
        self.sync.external_event_id = "known-active-fixture" if mode in ("update", "cancel-known") else ""
        self.sync.status = GoogleCalendarSync.Status.PENDING
        self.sync.last_error = "以前の記録"
        self.sync.synced_at = None
        self.sync.save(update_fields=["external_event_id", "status", "last_error", "synced_at"])
        job, args = self._queue("sheets" if mode == "sheets" else "calendar")
        return job, args, self._worker("sheets" if mode == "sheets" else "calendar")

    def _change(self, job, reason):
        query = AsyncJob.objects.filter(pk=job.pk)
        if reason == "expired":
            query.update(expires_at=timezone.now() - timedelta(seconds=1))
        elif reason == "deleted":
            query.delete()
        else:
            query.update(status=AsyncJob.Status.SUCCEEDED, result={"retained": "別の完了記録"}, progress=77)
        return list(query.values())

    def _assert_unchanged(self, job, saved):
        self.assertEqual(list(AsyncJob.objects.filter(pk=job.pk).values()), saved)

    def test_cleanup_between_start_update_and_refresh_stops_without_unhandled_error(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode), transaction.atomic(), ExitStack() as stack:
                job, args, worker = self._prepare(mode)
                before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                sends, token = self._sends(stack)
                original = AsyncJob.refresh_from_db

                def remove(instance, *args, **kwargs):
                    AsyncJob.objects.filter(pk=instance.pk).delete()
                    return original(instance, *args, **kwargs)

                stack.enter_context(patch.object(AsyncJob, "refresh_from_db", new=remove))
                self.assertEqual(worker.run(*args), "inactive-job")
                self.assertFalse(AsyncJob.objects.filter(pk=job.pk).exists())
                self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()

    def test_changed_owner_or_kind_after_token_read_cannot_authorize_send_or_save(self):
        for mode in ("sheets", "create"):
            for change in ({"owner_id": self.other.pk}, {"job_type": "statistics_export"}):
                with self.subTest(mode=mode, change=change), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    sends, token = self._sends(stack)
                    saved = []

                    def read(user):
                        AsyncJob.objects.filter(pk=job.pk).update(**change)
                        saved.extend(AsyncJob.objects.filter(pk=job.pk).values())
                        return "isolated-token"

                    token.side_effect = read
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    for send in sends.values():
                        send.assert_not_called()

    def test_change_during_token_read_stops_every_first_delivery_without_mutation(self):
        for mode in ("sheets", "create", "update", "cancel-known", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    sends, token = self._sends(stack)
                    saved = []

                    def read(user):
                        saved.extend(self._change(job, reason))
                        return "isolated-token"

                    token.side_effect = read
                    retry = stack.enter_context(patch.object(worker, "retry", side_effect=Retry()))
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                    for send in sends.values():
                        send.assert_not_called()
                    retry.assert_not_called()

    def test_change_during_last_credential_check_stops_before_http(self):
        for mode in ("sheets", "create"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    sends, _ = self._sends(stack)
                    saved = []

                    def check(*args):
                        saved.extend(self._change(job, reason))
                        return True

                    stack.enter_context(patch("schedules.tasks.google_credential_is_current", side_effect=check))
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    for send in sends.values():
                        send.assert_not_called()

    def test_calendar_change_between_requests_stops_conditional_or_conflict_followup(self):
        for mode in ("update", "cancel-known", "conflict-post", "conflict-get"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    sends, _ = self._sends(stack)
                    saved = []

                    def post(url, **kwargs):
                        if mode == "conflict-post":
                            saved.extend(self._change(job, reason))
                        return self.response(409, {})

                    def fetch(url, **kwargs):
                        saved.extend(self._change(job, reason))
                        return self.event_response(url, **kwargs)

                    sends["post"].side_effect = post
                    sends["get"].side_effect = fetch
                    retry = stack.enter_context(patch.object(worker, "retry", side_effect=Retry()))
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                    self.assertEqual(sends["post"].call_count, int(mode.startswith("conflict")))
                    self.assertEqual(sends["get"].call_count, int(mode != "conflict-post"))
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()

    def test_sheets_change_after_first_real_chunk_stops_remaining_and_preserves_record(self):
        characters = CharacterSheet.objects.bulk_create(
            [CharacterSheet(user=self.user, edition="7th") for _ in range(100)]
        )
        CharacterSheet7th.objects.bulk_create(
            [CharacterSheet7th(character_sheet=character, name="非公開の分割出力") for character in characters]
        )
        for reason in self.reasons:
            with self.subTest(reason=reason), transaction.atomic(), ExitStack() as stack:
                job, args, worker = self._prepare("sheets")
                self.assertEqual(len(args[-1]), 101)
                sends, _ = self._sends(stack)
                saved = []

                def put(url, **kwargs):
                    self.assertEqual(len(kwargs["json"]["values"]), 100)
                    saved.extend(self._change(job, reason))
                    return self.response(200, {"updatedCells": 100})

                sends["put"].side_effect = put
                retry = stack.enter_context(patch.object(worker, "retry", side_effect=Retry()))
                self.assertEqual(worker.run(*args), "inactive-job")
                self._assert_unchanged(job, saved)
                sends["put"].assert_called_once()
                retry.assert_not_called()

    def test_late_failure_cannot_overwrite_inactive_job_sync_or_schedule_retry(self):
        for mode in ("sheets", "create"):
            for phase in ("token", "http", "response"):
                for reason in self.reasons:
                    with (
                        self.subTest(mode=mode, phase=phase, reason=reason),
                        transaction.atomic(),
                        ExitStack() as stack,
                    ):
                        job, args, worker = self._prepare(mode)
                        before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                        sends, token = self._sends(stack)
                        saved = []

                        def fail(*args, **kwargs):
                            saved.extend(self._change(job, reason))
                            if phase == "token":
                                raise ValueError("合成token取得失敗")
                            if phase == "http":
                                raise requests.Timeout("合成応答喪失")
                            return self.response(200, [])

                        if phase == "token":
                            token.side_effect = fail
                        else:
                            sends["put" if mode == "sheets" else "post"].side_effect = fail
                        retry = stack.enter_context(patch.object(worker, "retry", side_effect=Retry()))
                        self.assertEqual(worker.run(*args), "inactive-job")
                        self._assert_unchanged(job, saved)
                        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                        retry.assert_not_called()

    def test_last_acknowledged_calendar_write_keeps_sync_but_does_not_recreate_or_overwrite_job(self):
        for mode, method in (("create", "post"), ("update", "put"), ("cancel-known", "delete")):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    sends, _ = self._sends(stack)
                    saved = []

                    def send(url, **kwargs):
                        saved.extend(self._change(job, reason))
                        return self.response(
                            204 if method == "delete" else 200,
                            {"id": kwargs["json"]["id"]} if method == "post" else {"id": "known-active-fixture"},
                        )

                    sends[method].side_effect = send
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    sends[method].assert_called_once()
                    self.sync.refresh_from_db()
                    self.assertEqual(
                        self.sync.status,
                        (
                            GoogleCalendarSync.Status.DELETED
                            if mode == "cancel-known"
                            else GoogleCalendarSync.Status.SYNCED
                        ),
                    )
                    self.assertEqual(self.sync.last_error, "")
                    self.assertIsNotNone(self.sync.synced_at)

    def test_late_authorization_failure_does_not_mutate_inactive_job_or_calendar_sync(self):
        for mode in ("sheets", "create"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), transaction.atomic(), ExitStack() as stack:
                    job, args, worker = self._prepare(mode)
                    before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    sends, token = self._sends(stack)
                    saved = []

                    def lookup(*args):
                        saved.extend(self._change(job, reason))
                        return None

                    stack.enter_context(
                        patch(
                            (
                                "schedules.tasks._google_sheets_export_integration"
                                if mode == "sheets"
                                else "schedules.tasks._google_calendar_sync_integration"
                            ),
                            side_effect=lookup,
                        )
                    )
                    self.assertEqual(worker.run(*args), "inactive-job")
                    self._assert_unchanged(job, saved)
                    self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                    token.assert_not_called()
                    for send in sends.values():
                        send.assert_not_called()
