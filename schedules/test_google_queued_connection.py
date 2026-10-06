import json
from contextlib import ExitStack
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from schedules import test_google_connection_guard as connection_tests
from schedules import test_google_credential_guard as credential_tests
from schedules.google_tokens import get_google_access_token
from schedules.models import AsyncJob, GoogleCalendarSync, TRPGSession
from schedules.tasks import export_google_sheet, schedule_session_google_syncs, sync_google_calendar


class GoogleQueuedConnectionTest(TestCase):
    access_fixture = connection_tests.GoogleConnectionGuardTest.access_fixture
    replacement_fixture = connection_tests.GoogleConnectionGuardTest.replacement_fixture
    refresh_fixture = connection_tests.GoogleConnectionGuardTest.refresh_fixture
    message = "ジョブ作成時のGoogle接続先を確認できません。接続先を確認して再実行してください。"
    reasons = connection_tests.GoogleConnectionGuardTest.reasons + tuple(
        reason for reason in credential_tests.GoogleCredentialGuardTest.reasons if reason != "access-rotated"
    )
    setUp = connection_tests.GoogleConnectionGuardTest.setUp
    _response = connection_tests.GoogleConnectionGuardTest._response
    _fetch_event = connection_tests.GoogleConnectionGuardTest._fetch_event
    _sends = connection_tests.GoogleConnectionGuardTest._sends
    _assert_failed = connection_tests.GoogleConnectionGuardTest._assert_failed
    _disconnect = credential_tests.GoogleCredentialGuardTest._disconnect

    def _prepare(self, mode="sheets"):
        SocialAccount.objects.filter(uid__startswith="guard-").delete()
        return connection_tests.GoogleConnectionGuardTest._prepare(self, mode)

    def _change(self, reason):
        if reason in connection_tests.GoogleConnectionGuardTest.reasons:
            connection_tests.GoogleConnectionGuardTest._change(self, reason)
        else:
            credential_tests.GoogleCredentialGuardTest._change(self, reason)

    def _queue(self, origin, mode):
        self._prepare(mode)
        client = APIClient()
        client.force_authenticate(self.user)
        if origin == "automatic":
            TRPGSession.objects.filter(pk=self.session.pk).update(gm=self.user)
            self.session.refresh_from_db()
            with patch("schedules.tasks.queue_google_calendar_sync", return_value=True) as queue:
                schedule_session_google_syncs(self.session)
        elif mode == "sheets":
            with patch("schedules.integration_views.queue_google_sheet_export", return_value=True) as queue:
                response = client.post(
                    "/api/character-sheets/google-sheets/export/",
                    {"spreadsheet_id": "private-sheet-fixture"},
                    format="json",
                )
            self.assertEqual(response.status_code, 202)
        else:
            with patch("schedules.integration_views.queue_google_calendar_sync", return_value=True) as queue:
                response = client.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
            self.assertEqual(response.status_code, 202)
        queue.assert_called_once()
        args = queue.call_args.args
        job = AsyncJob.objects.get(pk=args[0] if mode == "sheets" else args[1])
        return job, args

    def _run(self, mode, args):
        return export_google_sheet.run(*args) if mode == "sheets" else sync_google_calendar.run(*args)

    def test_api_waiting_jobs_reject_connection_changes_before_lookup(self):
        for mode in ("sheets", "create", "update", "cancel-known", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job, args = self._queue("api", mode)
                    self._change(reason)
                    sends = self._sends(stack)
                    token = stack.enter_context(
                        patch("schedules.tasks.get_google_access_token", wraps=get_google_access_token)
                    )
                    retry = stack.enter_context(
                        patch.object(export_google_sheet if mode == "sheets" else sync_google_calendar, "retry")
                    )
                    self._assert_failed(self._run(mode, args), job)
                    token.assert_not_called()
                    retry.assert_not_called()
                    for send in sends.values():
                        send.assert_not_called()

    def test_automatic_waiting_jobs_reject_connection_changes_before_lookup(self):
        for reason in self.reasons:
            with self.subTest(reason=reason), ExitStack() as stack:
                job, args = self._queue("automatic", "create")
                self._change(reason)
                sends = self._sends(stack)
                token = stack.enter_context(
                    patch("schedules.tasks.get_google_access_token", wraps=get_google_access_token)
                )
                self._assert_failed(self._run("create", args), job)
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()

    def test_unchanged_api_and_automatic_jobs_still_deliver(self):
        for origin, mode in (
            ("api", "sheets"),
            ("api", "create"),
            ("api", "update"),
            ("api", "cancel-known"),
            ("api", "cancel-unknown"),
            ("automatic", "create"),
        ):
            with self.subTest(origin=origin, mode=mode), ExitStack() as stack:
                job, args = self._queue(origin, mode)
                self._sends(stack)
                result = self._run(mode, args)
                expected = (
                    "exported"
                    if mode == "sheets"
                    else (
                        GoogleCalendarSync.Status.DELETED
                        if mode.startswith("cancel")
                        else GoogleCalendarSync.Status.SYNCED
                    )
                )
                self.assertEqual(result, expected)
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_queue_binding_is_opaque_and_has_no_credentials_or_uid(self):
        for origin, mode in (("api", "sheets"), ("api", "create"), ("automatic", "create")):
            with self.subTest(origin=origin, mode=mode):
                job, _ = self._queue(origin, mode)
                self.assertRegex(job.payload.get("google_connection", ""), r"^[0-9a-f]{64}$")
                stored = json.dumps(job.payload)
                for private in (self.access_fixture, self.refresh_fixture, self.account.uid):
                    self.assertNotIn(private, stored)

    def test_access_rotation_while_waiting_keeps_the_same_target(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue("api", mode)
                self._change("access-rotated")
                sends = self._sends(stack)
                self.assertEqual(
                    self._run(mode, args), "exported" if mode == "sheets" else GoogleCalendarSync.Status.SYNCED
                )
                send = sends["put" if mode == "sheets" else "post"]
                self.assertEqual(
                    send.call_args.kwargs["headers"]["Authorization"], f"Bearer {self.replacement_fixture}"
                )

    def test_legacy_or_malformed_binding_never_delivers(self):
        payloads = (
            [],
            {},
            {"google_connection": None},
            {"google_connection": []},
            {"google_connection": True},
            {"google_connection": "wrong"},
        )
        for mode in ("sheets", "create"):
            for payload in payloads:
                with self.subTest(mode=mode, payload=payload), ExitStack() as stack:
                    job, args = self._queue("api", mode)
                    job.payload = (
                        {"sync_id": args[0], **payload} if mode == "create" and isinstance(payload, dict) else payload
                    )
                    job.save(update_fields=["payload"])
                    before_sync = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    sends = self._sends(stack)
                    token = stack.enter_context(
                        patch("schedules.tasks.get_google_access_token", wraps=get_google_access_token)
                    )
                    result = self._run(mode, args)
                    if mode == "create" and not isinstance(payload, dict):
                        self.assertEqual(result, "invalid-target")
                        job.refresh_from_db()
                        self.assertEqual(job.status, AsyncJob.Status.FAILED)
                        self.assertEqual(
                            job.error, "ジョブの処理対象が一致しません。連携設定から新しく実行してください。"
                        )
                        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), before_sync)
                    else:
                        self._assert_failed(result, job)
                    token.assert_not_called()
                    for send in sends.values():
                        send.assert_not_called()

    def test_new_job_after_reconnect_uses_new_binding_and_delivers(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode), ExitStack() as stack:
                first, first_args = self._queue("api", mode)
                self._change("other-account")
                self._sends(stack)
                self._assert_failed(self._run(mode, first_args), first)
                client = APIClient()
                client.force_authenticate(self.user)
                if mode == "sheets":
                    with patch("schedules.integration_views.queue_google_sheet_export", return_value=True) as queue:
                        response = client.post(
                            "/api/character-sheets/google-sheets/export/",
                            {"spreadsheet_id": "private-sheet-fixture"},
                            format="json",
                        )
                else:
                    with patch("schedules.integration_views.queue_google_calendar_sync", return_value=True) as queue:
                        response = client.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
                self.assertEqual(response.status_code, 202)
                second = AsyncJob.objects.get(pk=response.data["job_id"])
                self.assertNotEqual(first.payload.get("google_connection"), second.payload.get("google_connection"))
                self.assertEqual(
                    self._run(mode, queue.call_args.args),
                    "exported" if mode == "sheets" else GoogleCalendarSync.Status.SYNCED,
                )

    def test_missing_credential_rejects_remote_jobs_but_keeps_local_preview(self):
        self._prepare()
        SocialToken.objects.filter(pk=self.token.pk).delete()
        client = APIClient()
        client.force_authenticate(self.user)
        initial = AsyncJob.objects.count()
        with (
            patch("schedules.integration_views.queue_google_sheet_export", return_value=True) as sheets,
            patch("schedules.integration_views.queue_google_calendar_sync", return_value=True) as calendar,
        ):
            response = client.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": "private-sheet-fixture"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["detail"], "Google Sheets連携を確認できません。Googleを再連携してください。")
            response = client.post(f"/api/sessions/{self.session.pk}/google-calendar/sync/")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.data["detail"], "Google Calendar連携を確認できません。Googleを再連携してください。"
            )
            response = client.post("/api/character-sheets/google-sheets/export/", {}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(AsyncJob.objects.count(), initial)
            sheets.assert_not_called()
            calendar.assert_not_called()

    def test_api_ignores_client_supplied_connection_binding(self):
        self._prepare()
        client = APIClient()
        client.force_authenticate(self.user)
        supplied = "a" * 64
        with patch("schedules.integration_views.queue_google_sheet_export", return_value=True):
            response = client.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": "private-sheet-fixture", "google_connection": supplied},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        self.assertNotEqual(job.payload["google_connection"], supplied)
        self.assertRegex(job.payload["google_connection"], r"^[0-9a-f]{64}$")

    def test_signing_key_change_requires_new_job_without_token_lookup(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args = self._queue("api", mode)
                sends = self._sends(stack)
                token = stack.enter_context(patch("schedules.tasks.get_google_access_token"))
                # Synthetic key rotation only; never a production settings update.
                stack.enter_context(override_settings(SECRET_KEY="isolated-rotated-fixture-key"))  # nosec B106
                self._assert_failed(self._run(mode, args), job)
                token.assert_not_called()
                for send in sends.values():
                    send.assert_not_called()
