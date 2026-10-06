import uuid
from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.google_oauth import store_google_integration_grant
from accounts.models import Group
from schedules.google_job_connection import google_connection_binding
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration, TRPGSession
from schedules.tasks import export_google_sheet, sync_google_calendar
from tests.utils.google_sheet_fixtures import run_sheet_fixture


class GoogleConnectionGuardTest(TestCase):
    reasons = ("same-account", "other-account", "recreated-integration")
    access_fixture = "isolated-original-access"
    replacement_fixture = "isolated-replacement-access"
    refresh_fixture = "isolated-refresh-value"
    message = "Googleの連携設定が処理中に変更されました。接続先を確認して再試行してください。"

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="google-connection-guard-fixture")
        group = Group.objects.create(name="Connection guard fixture", created_by=self.user)
        self.session = TRPGSession.objects.create(
            title="Connection guard fixture", group=group, created_by=self.user, date=timezone.now() + timedelta(days=1)
        )
        self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)

    def _prepare(self, mode="sheets"):
        SocialAccount.objects.filter(user=self.user).delete()
        self.account = SocialAccount.objects.create(user=self.user, provider="google", uid="guard-initial-identity")
        self.token = SocialToken.objects.create(
            account=self.account,
            token=self.access_fixture,
            token_secret=self.refresh_fixture,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.integration, _ = GoogleIntegration.objects.update_or_create(
            user=self.user,
            defaults={
                "calendar_enabled": True,
                "sheets_enabled": True,
                "scopes": [GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE],
                "connected_at": timezone.now() - timedelta(minutes=1),
            },
        )
        TRPGSession.objects.filter(pk=self.session.pk).update(
            status="cancelled" if mode.startswith("cancel") else "planned"
        )
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(
            status=GoogleCalendarSync.Status.PENDING,
            external_event_id="existing-event-fixture" if mode in ("update", "cancel-known") else "",
            last_error="",
            synced_at=None,
        )
        return AsyncJob.objects.create(
            owner=self.user,
            job_type="google_sheets_export" if mode == "sheets" else "google_calendar_sync",
            payload={
                "sync_id": self.sync.pk,
                "spreadsheet_id": "private-sheet-fixture",
                "range": "A1",
                "google_connection": google_connection_binding(self.integration),
            },
            expires_at=timezone.now() + timedelta(days=1),
        )

    def _change(self, reason):
        if reason == "recreated-integration":
            integration = GoogleIntegration.objects.get(user=self.user)
            connected_at = integration.connected_at
            integration.delete()
            GoogleIntegration.objects.create(
                user=self.user,
                calendar_enabled=True,
                sheets_enabled=True,
                scopes=[GoogleIntegration.REQUIRED_CALENDAR_SCOPE, GoogleIntegration.REQUIRED_SHEETS_SCOPE],
                connected_at=connected_at,
            )
        else:
            account = self.account
            if reason == "other-account":
                account, _ = SocialAccount.objects.get_or_create(
                    user=self.user, provider="google", uid="guard-other-identity"
                )
            login = SocialLogin(
                account=account,
                user=self.user,
                token=SocialToken(
                    account=account,
                    token=self.replacement_fixture,
                    token_secret=self.refresh_fixture,
                    expires_at=timezone.now() + timedelta(hours=2),
                ),
            )
            login.state = {"process": "connect"}
            login.google_integration_scopes = [
                GoogleIntegration.REQUIRED_CALENDAR_SCOPE,
                GoogleIntegration.REQUIRED_SHEETS_SCOPE,
            ]
            store_google_integration_grant(
                sender=SocialLogin, request=SimpleNamespace(user=self.user), sociallogin=login
            )
        integration = GoogleIntegration.objects.get(user=self.user)
        self.assertTrue(integration.calendar_enabled and integration.sheets_enabled)
        self.assertTrue(integration.has_scope(GoogleIntegration.REQUIRED_CALENDAR_SCOPE))
        self.assertTrue(integration.has_scope(GoogleIntegration.REQUIRED_SHEETS_SCOPE))

    def _response(self, code=200, data=None):
        response = Mock(status_code=code)
        response.json.return_value = data or {}
        return response

    def _fetch_event(self, url, **kwargs):
        event_id = url.rsplit("/", 1)[1]
        sync_key = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"https://tableno.jp/calendar-sync/{self.sync.pk}/{self.user.pk}/{self.session.pk}/{self.sync.created_at.isoformat()}",
        ).hex
        return self._response(
            data={
                "id": event_id,
                "etag": '"isolated-event-version"',
                "extendedProperties": {
                    "private": {"tableno_session_id": str(self.session.pk), "tableno_sync_key": sync_key}
                },
            }
        )

    def _sends(self, stack):
        sends = {
            method: stack.enter_context(patch(f"schedules.tasks.requests.{method}"))
            for method in ("post", "get", "put", "delete")
        }
        sends["post"].side_effect = lambda url, **kwargs: self._response(data=kwargs["json"])
        sends["get"].side_effect = self._fetch_event
        sends["put"].side_effect = lambda url, **kwargs: self._response(
            data={"updatedCells": 100, "id": url.rsplit("/", 1)[1]}
        )
        sends["delete"].return_value = self._response(204)
        return sends

    def _assert_failed(self, result, job, partial=False, message=None):
        self.assertEqual(result, "connection-changed")
        job.refresh_from_db()
        expected = (message or self.message) + (
            "途中まで出力されている可能性があります。出力先を確認してください。" if partial else ""
        )
        self.assertEqual(job.error, expected)
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(job.result, {})
        self.assertNotIn(self.access_fixture, job.error)
        self.assertNotIn(self.replacement_fixture, job.error)
        if job.job_type == "google_calendar_sync":
            self.sync.refresh_from_db()
            self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
            self.assertEqual(self.sync.last_error, expected)
            self.assertIsNone(self.sync.synced_at)

    def test_sheets_connection_change_after_token_read_blocks_first_send(self):
        for reason in self.reasons:
            with self.subTest(reason=reason), ExitStack() as stack:
                job = self._prepare()
                sends = self._sends(stack)

                def read(user):
                    self._change(reason)
                    return self.access_fixture

                stack.enter_context(patch("schedules.tasks.get_google_access_token", side_effect=read))
                retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
                result = run_sheet_fixture(str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [])
                self._assert_failed(result, job)
                for send in sends.values():
                    send.assert_not_called()
                retry.assert_not_called()

    def test_sheets_connection_change_between_chunks_blocks_remaining_sends(self):
        for reason in self.reasons:
            with self.subTest(reason=reason), ExitStack() as stack:
                job = self._prepare()
                sends = self._sends(stack)

                def put(url, **kwargs):
                    self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {self.access_fixture}")
                    self._change(reason)
                    return self._response(data={"updatedCells": 100})

                sends["put"].side_effect = put
                retry = stack.enter_context(patch.object(export_google_sheet, "retry"))
                result = run_sheet_fixture(
                    str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [[row] for row in range(201)]
                )
                self._assert_failed(result, job, partial=True)
                self.assertEqual(job.progress, 49)
                sends["put"].assert_called_once()
                retry.assert_not_called()

    def test_calendar_connection_change_after_token_read_blocks_each_first_request(self):
        for mode in ("create", "update", "cancel-known", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job = self._prepare(mode)
                    sends = self._sends(stack)

                    def read(user):
                        self._change(reason)
                        return self.access_fixture

                    stack.enter_context(patch("schedules.tasks.get_google_access_token", side_effect=read))
                    retry = stack.enter_context(patch.object(sync_google_calendar, "retry"))
                    result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                    self._assert_failed(result, job)
                    for send in sends.values():
                        send.assert_not_called()
                    retry.assert_not_called()

    def test_calendar_connection_change_between_requests_blocks_conflict_and_cancel(self):
        for mode in ("conflict-post", "conflict-get", "cancel-unknown"):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job = self._prepare(mode)
                    sends = self._sends(stack)

                    def post(url, **kwargs):
                        if mode == "conflict-post":
                            self._change(reason)
                        return self._response(409)

                    def fetch(url, **kwargs):
                        self._change(reason)
                        return self._fetch_event(url, **kwargs)

                    sends["post"].side_effect = post
                    sends["get"].side_effect = fetch
                    retry = stack.enter_context(patch.object(sync_google_calendar, "retry"))
                    result = sync_google_calendar.run(self.sync.pk, str(job.pk))
                    self._assert_failed(result, job)
                    self.assertEqual(sends["post"].call_count, int(mode != "cancel-unknown"))
                    self.assertEqual(sends["get"].call_count, int(mode != "conflict-post"))
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()

    def test_connection_change_after_last_acknowledged_write_does_not_undo_it(self):
        for mode, method in (("sheets", "put"), ("create", "post"), ("update", "put"), ("cancel-known", "delete")):
            for reason in self.reasons:
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    job = self._prepare(mode)
                    sends = self._sends(stack)

                    def send(url, **kwargs):
                        self._change(reason)
                        return self._response(
                            204 if method == "delete" else 200,
                            {
                                **kwargs.get("json", {}),
                                "id": url.rsplit("/", 1)[1] if mode == "update" else kwargs.get("json", {}).get("id"),
                            },
                        )

                    sends[method].side_effect = send
                    if mode == "sheets":
                        self.assertEqual(
                            run_sheet_fixture(str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [[1]]),
                            "exported",
                        )
                    else:
                        self.assertEqual(
                            sync_google_calendar.run(self.sync.pk, str(job.pk)),
                            (
                                GoogleCalendarSync.Status.DELETED
                                if method == "delete"
                                else GoogleCalendarSync.Status.SYNCED
                            ),
                        )
                    sends[method].assert_called_once()
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    # Isolated settings, not production credentials.
    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="fixture-client", GOOGLE_OAUTH_CLIENT_SECRET="fixture-secret"
    )  # nosec B106
    def test_normal_token_refresh_does_not_change_connection_or_stop_delivery(self):
        for mode in ("sheets", "create"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job = self._prepare(mode)
                SocialToken.objects.filter(pk=self.token.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
                sends = self._sends(stack)
                credentials = Mock(
                    token=self.replacement_fixture,
                    refresh_token=self.refresh_fixture,
                    expiry=timezone.now() + timedelta(hours=1),
                )
                stack.enter_context(patch("schedules.google_tokens.Credentials", return_value=credentials))
                if mode == "sheets":
                    self.assertEqual(
                        run_sheet_fixture(
                            str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [[row] for row in range(101)]
                        ),
                        "exported",
                    )
                    self.assertEqual(sends["put"].call_count, 2)
                else:
                    self.assertEqual(
                        sync_google_calendar.run(self.sync.pk, str(job.pk)), GoogleCalendarSync.Status.SYNCED
                    )
                    sends["post"].assert_called_once()
                credentials.refresh.assert_called_once()
                self.integration.refresh_from_db()
                self.assertLess(self.integration.connected_at, timezone.now() - timedelta(seconds=30))

    def test_saving_unchanged_preferences_does_not_replace_connection_or_stop_delivery(self):
        client = APIClient()
        client.force_authenticate(self.user)
        for mode in ("sheets", "conflict"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job = self._prepare(mode)
                connected_at = self.integration.connected_at
                sends = self._sends(stack)

                def save_preferences():
                    response = client.put(
                        "/api/google/integration/", {"calendar_enabled": True, "sheets_enabled": True}, format="json"
                    )
                    self.assertEqual(response.status_code, 200)

                def put(url, **kwargs):
                    save_preferences()
                    return self._response(data={"updatedCells": 100})

                def post(url, **kwargs):
                    save_preferences()
                    return self._response(409)

                if mode == "sheets":
                    sends["put"].side_effect = put
                    result = run_sheet_fixture(
                        str(job.pk), self.user.pk, "private-sheet-fixture", "A1", [[row] for row in range(101)]
                    )
                    self.assertEqual(result, "exported")
                    self.assertEqual(sends["put"].call_count, 2)
                else:
                    sends["post"].side_effect = post
                    sends["put"].side_effect = self._fetch_event
                    self.assertEqual(
                        sync_google_calendar.run(self.sync.pk, str(job.pk)), GoogleCalendarSync.Status.SYNCED
                    )
                    sends["get"].assert_called_once()
                    sends["put"].assert_called_once()
                self.integration.refresh_from_db()
                self.assertEqual(self.integration.connected_at, connected_at)
