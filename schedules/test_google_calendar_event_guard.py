import json
import threading
import uuid
from contextlib import ExitStack
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from allauth.socialaccount.models import SocialToken
from celery.exceptions import Retry
from django.test import TestCase
from django.utils import timezone

from schedules import test_google_calendar_delivery as delivery_tests
from schedules.google_job_lifecycle import GOOGLE_EXECUTION_UNCERTAIN_MESSAGE
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleIntegration
from schedules.tasks import sync_google_calendar


class GoogleCalendarEventGuardTest(TestCase):
    original_transport = staticmethod(requests.sessions.Session.request)
    job = delivery_tests.GoogleCalendarDeliveryTest.job
    response = delivery_tests.GoogleCalendarDeliveryTest.response
    mismatch = "Google Calendarの予定IDが一致しません。連携状態を確認してください。"
    malformed = "Google Calendarの応答形式を確認できません。連携状態を確認してください。"
    version_error = "Google Calendarの予定の更新情報を確認できません。連携状態を確認してください。"
    changed = "Google Calendarの予定が確認後に変更されました。予定を確認して再実行してください。"

    def setUp(self):
        delivery_tests.GoogleCalendarDeliveryTest.setUp(self)
        network = patch(
            "requests.sessions.Session.request", side_effect=AssertionError("Unmocked external HTTP in isolated test")
        )
        network.start()
        self.addCleanup(network.stop)

    def _event(self, mode):
        generated = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"https://tableno.jp/calendar-sync/{self.sync.pk}/{self.user.pk}/{self.session.pk}/{self.sync.created_at.isoformat()}",
        ).hex
        return {
            "id": generated if mode in ("conflict", "cancel-unknown") else "stored-event-fixture",
            "etag": '"isolated-event-version-1"',
            "extendedProperties": {
                "private": {"tableno_session_id": str(self.session.pk), "tableno_sync_key": generated}
            },
        }

    def _run(self, stack, mode, event, code=200, external_id="stored-event-fixture"):
        self.session.status = "cancelled" if mode.startswith("cancel") else "planned"
        self.session.save(update_fields=["status"])
        self.sync.external_event_id = "" if mode in ("conflict", "cancel-unknown") else external_id
        self.sync.status = GoogleCalendarSync.Status.PENDING
        self.sync.synced_at = None
        self.sync.save(update_fields=["external_event_id", "status", "synced_at"])
        self.current_job = self.job()
        sends = {
            method: stack.enter_context(patch(f"schedules.tasks.requests.{method}"))
            for method in ("get", "put", "delete", "post")
        }
        sends["get"].return_value = self.response(code, event)
        sends["post"].return_value = self.response(409, {})
        sends["put"].return_value = self.response(200, self._event(mode))
        sends["delete"].return_value = self.response(204, {})
        stack.enter_context(patch("schedules.tasks.get_google_access_token", return_value="isolated-token"))
        retry = stack.enter_context(patch.object(sync_google_calendar, "retry", side_effect=Retry()))
        return sends, retry

    def _execute(self):
        return sync_google_calendar.run(self.sync.pk, str(self.current_job.pk))

    def _failed(self, message):
        self.current_job.refresh_from_db()
        self.sync.refresh_from_db()
        self.assertEqual(self.current_job.status, AsyncJob.Status.FAILED)
        self.assertEqual(self.current_job.error, message)
        self.assertEqual(self.sync.last_error, message)
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.FAILED)
        self.assertIsNone(self.sync.synced_at)
        self.assertIsNotNone(self.current_job.finished_at)

    def test_saved_id_cannot_update_or_delete_an_unrelated_event(self):
        for mode in ("update", "cancel-known"):
            for change in ("id", "session", "key", "private", "properties"):
                with self.subTest(mode=mode, change=change), ExitStack() as stack:
                    event = self._event(mode)
                    if change == "id":
                        event["id"] = "unrelated-private-id"
                    elif change in ("session", "key"):
                        event["extendedProperties"]["private"][
                            "tableno_session_id" if change == "session" else "tableno_sync_key"
                        ] = "unrelated-private-marker"
                    elif change == "private":
                        event["extendedProperties"]["private"] = {}
                    else:
                        event.pop("extendedProperties")
                    sends, retry = self._run(stack, mode, event)
                    self.assertEqual(self._execute(), "invalid-response")
                    self._failed(self.mismatch)
                    sends["get"].assert_called_once()
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()

    def test_saved_id_malformed_lookup_never_mutates(self):
        for mode in ("update", "cancel-known"):
            for event in (None, [], "private body", {"extendedProperties": []}):
                with self.subTest(mode=mode, event=event), ExitStack() as stack:
                    sends, retry = self._run(stack, mode, event)
                    self.assertEqual(self._execute(), "invalid-response")
                    self._failed(self.malformed)
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()

    def test_missing_or_unsafe_etag_never_mutates_any_verified_path(self):
        for mode in ("update", "cancel-known", "conflict", "cancel-unknown"):
            for etag in (
                None,
                "missing",
                "",
                17,
                [],
                True,
                "*",
                'W/"weak"',
                '"a',
                'a"',
                '"a", "b"',
                '"version\r\nInjected: yes"',
            ):
                with self.subTest(mode=mode, etag=etag), ExitStack() as stack:
                    event = self._event(mode)
                    event["etag"] = etag
                    if etag == "missing":
                        event.pop("etag")
                    sends, retry = self._run(stack, mode, event)
                    self.assertEqual(self._execute(), "invalid-response")
                    self._failed(self.version_error)
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()

    def test_matching_event_is_mutated_only_with_its_exact_strong_etag(self):
        for mode in ("update", "cancel-known", "conflict", "cancel-unknown"):
            with self.subTest(mode=mode), ExitStack() as stack:
                event = self._event(mode)
                sends, retry = self._run(stack, mode, event)
                expected = (
                    GoogleCalendarSync.Status.DELETED if mode.startswith("cancel") else GoogleCalendarSync.Status.SYNCED
                )
                self.assertEqual(self._execute(), expected)
                write = sends["delete" if mode.startswith("cancel") else "put"]
                write.assert_called_once()
                self.assertEqual(write.call_args.kwargs["headers"].get("If-Match"), event["etag"])
                prepared = requests.Request(
                    "DELETE" if mode.startswith("cancel") else "PUT",
                    write.call_args.args[0],
                    headers=write.call_args.kwargs["headers"],
                ).prepare()
                self.assertEqual(prepared.headers["If-Match"], event["etag"])
                self.assertNotIn("If-Match", sends["get"].call_args.kwargs["headers"])
                self.current_job.refresh_from_db()
                self.assertEqual(self.current_job.status, AsyncJob.Status.SUCCEEDED)
                retry.assert_not_called()

    def test_revocation_during_identity_lookup_blocks_the_write(self):
        for mode in ("update", "cancel-known", "conflict", "cancel-unknown"):
            for reason in ("disabled", "deleted-token", "rotated-token", "reconnected"):
                with self.subTest(mode=mode, reason=reason), ExitStack() as stack:
                    event = self._event(mode)
                    sends, retry = self._run(stack, mode, event)

                    def fetch(url, **kwargs):
                        if reason == "disabled":
                            GoogleIntegration.objects.filter(user=self.user).update(calendar_enabled=False)
                        elif reason == "deleted-token":
                            SocialToken.objects.filter(account__user=self.user).delete()
                        elif reason == "rotated-token":
                            # Synthetic credential in this isolated TestCase only.
                            SocialToken.objects.filter(account__user=self.user).update(
                                token="isolated-replacement"
                            )  # nosec B106
                        else:
                            GoogleIntegration.objects.filter(user=self.user).update(
                                connected_at=timezone.now() + timedelta(seconds=1)
                            )
                        return self.response(200, event)

                    sends["get"].side_effect = fetch
                    self.assertEqual(
                        self._execute(), "not-authorized" if reason == "disabled" else "connection-changed"
                    )
                    self._failed(
                        "Google Calendar連携が無効、またはセッションを同期する権限がありません。"
                        if reason == "disabled"
                        else "Googleの連携設定が処理中に変更されました。接続先を確認して再試行してください。"
                    )
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                    retry.assert_not_called()
                    # Restore only this TestCase's isolated fixture for the next subtest.
                    integration = GoogleIntegration.objects.get(user=self.user)
                    integration.calendar_enabled = True
                    integration.save(update_fields=["calendar_enabled"])
                    account = self.user.socialaccount_set.get(provider="google")
                    SocialToken.objects.update_or_create(
                        account=account, defaults={"token": "isolated-token"}  # Synthetic fixture only. # nosec B105
                    )

    def test_saved_event_id_is_encoded_as_one_url_path_component(self):
        for mode in ("update", "cancel-known"):
            with self.subTest(mode=mode), ExitStack() as stack:
                event = self._event(mode)
                event["id"] = "private/path?query=value#fragment"
                sends, _ = self._run(stack, mode, event, external_id=event["id"])
                sends["put"].return_value = self.response(200, event)
                self.assertEqual(
                    self._execute(),
                    (
                        GoogleCalendarSync.Status.DELETED
                        if mode.startswith("cancel")
                        else GoogleCalendarSync.Status.SYNCED
                    ),
                )
                write = sends["delete" if mode.startswith("cancel") else "put"]
                for request in (sends["get"], write):
                    url = requests.Request("GET", request.call_args.args[0]).prepare().url
                    parsed = urlsplit(url)
                    self.assertEqual(
                        (parsed.scheme, parsed.netloc, parsed.query, parsed.fragment),
                        ("https", "www.googleapis.com", "", ""),
                    )
                    self.assertTrue(parsed.path.endswith("/private%2Fpath%3Fquery%3Dvalue%23fragment"))

    def test_saved_dot_segments_never_enter_a_provider_url(self):
        for mode in ("update", "cancel-known"):
            for event_id in (".", ".."):
                with self.subTest(mode=mode, event_id=event_id), ExitStack() as stack:
                    event = self._event(mode)
                    event["id"] = event_id
                    sends, retry = self._run(stack, mode, event, external_id=event_id)
                    self.assertEqual(self._execute(), "invalid-response")
                    self._failed("Google Calendarの予定IDを確認できません。連携状態を確認してください。")
                    for send in sends.values():
                        send.assert_not_called()
                    retry.assert_not_called()

    def test_changed_remote_version_is_not_retried_or_overwritten(self):
        for mode in ("update", "cancel-known", "conflict", "cancel-unknown"):
            with self.subTest(mode=mode), ExitStack() as stack:
                sends, retry = self._run(stack, mode, self._event(mode))
                write = sends["delete" if mode.startswith("cancel") else "put"]
                remote = {"version": '"isolated-event-version-2"', "body": "private concurrent edit"}

                def conditional_write(url, **kwargs):
                    self.assertNotEqual(kwargs["headers"].get("If-Match"), remote["version"])
                    return self.response(412, {"private body": remote["body"]})

                write.side_effect = conditional_write
                self.assertEqual(self._execute(), "invalid-response")
                self._failed(self.changed)
                write.assert_called_once()
                sends["get"].assert_called_once()
                retry.assert_not_called()
                self.assertEqual(remote["body"], "private concurrent edit")

    def test_already_missing_saved_event_cancellation_is_success_without_delete(self):
        for code in (404, 410):
            with self.subTest(code=code), ExitStack() as stack:
                sends, retry = self._run(stack, "cancel-known", {}, code)
                self.assertEqual(self._execute(), GoogleCalendarSync.Status.DELETED)
                sends["delete"].assert_not_called()
                self.current_job.refresh_from_db()
                self.assertEqual(self.current_job.status, AsyncJob.Status.SUCCEEDED)
                retry.assert_not_called()

    def test_cancelled_tombstone_is_not_mutated_and_wrong_id_is_rejected(self):
        for mode in ("cancel-known", "cancel-unknown"):
            for matching in (True, False):
                with self.subTest(mode=mode, matching=matching), ExitStack() as stack:
                    event = {
                        "id": self._event(mode)["id"] if matching else "unrelated-private-id",
                        "status": "cancelled",
                    }
                    sends, retry = self._run(stack, mode, event)
                    self.assertEqual(
                        self._execute(), GoogleCalendarSync.Status.DELETED if matching else "invalid-response"
                    )
                    sends["delete"].assert_not_called()
                    if not matching:
                        self._failed(self.mismatch)
                    retry.assert_not_called()

    def test_lookup_http_failure_retries_safely_without_mutation(self):
        for mode in ("update", "cancel-known"):
            with self.subTest(mode=mode), ExitStack() as stack:
                sends, retry = self._run(stack, mode, {"private body": "private diagnostic"}, 503)
                with self.assertRaises(Retry):
                    self._execute()
                self._failed("Google Calendar APIとの通信に失敗しました。連携状態を確認して再試行してください。")
                sends["put"].assert_not_called()
                sends["delete"].assert_not_called()
                retry.assert_called_once()

    def test_update_response_requires_matching_event_identity(self):
        for data in (None, [], "private body", {}, {"id": "another-private-id"}):
            with self.subTest(data=data), ExitStack() as stack:
                sends, retry = self._run(stack, "update", self._event("update"))
                sends["put"].return_value = self.response(200, data)
                self.assertEqual(self._execute(), "uncertain")
                self.current_job.refresh_from_db()
                self.assertEqual(self.current_job.status, AsyncJob.Status.UNCERTAIN)
                self.assertEqual(self.current_job.error, GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
                self.assertIsNotNone(self.current_job.finished_at)
                self.sync.refresh_from_db()
                self.assertEqual(self.sync.status, GoogleCalendarSync.Status.PENDING)
                self.assertIsNone(self.sync.synced_at)
                self.assertEqual(self.sync.last_error, "")
                sends["put"].assert_called_once()
                retry.assert_not_called()

    def test_real_loopback_http_keeps_if_match_and_stops_concurrent_writes(self):
        for mode in ("update", "cancel-known", "conflict", "cancel-unknown"):
            for changed in (False, True):
                with self.subTest(mode=mode, changed=changed), ExitStack() as stack:
                    event = self._event(mode)
                    real_sends = {method: getattr(requests, method) for method in ("get", "put", "delete", "post")}
                    sends, retry = self._run(stack, mode, event)
                    remote = {"etag": event["etag"], "writes": 0, "calls": [], "body": "private existing event"}

                    class Handler(BaseHTTPRequestHandler):
                        def log_message(self, *args):
                            pass

                        def reply(self, status, data):
                            body = json.dumps(data).encode("utf-8") if status != 204 else b""
                            self.send_response(status)
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Content-Length", str(len(body)))
                            self.end_headers()
                            self.wfile.write(body)

                        def do_GET(self):
                            remote["etag"] = '"isolated-event-version-2"' if changed else event["etag"]
                            self.reply(200, event)

                        def do_POST(self):
                            self.rfile.read(int(self.headers.get("Content-Length", "0")))
                            self.reply(409, {})

                        def write_event(self):
                            # Consume the request before replying/closing, including the PUT body.
                            # The separate lost-response fixture deliberately closes after applying.
                            self.rfile.read(int(self.headers.get("Content-Length", "0")))
                            remote["calls"].append((self.command, self.headers.get("If-Match")))
                            if self.headers.get("If-Match") != remote["etag"]:
                                self.reply(412, {"error": "private concurrent edit"})
                            else:
                                remote["writes"] += 1
                                remote["body"] = "deleted" if self.command == "DELETE" else "updated"
                                self.reply(204 if self.command == "DELETE" else 200, event)

                        do_PUT = write_event
                        do_DELETE = write_event

                    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
                    thread.start()
                    port = server.server_port

                    def cleanup():
                        server.shutdown()
                        server.server_close()
                        thread.join(timeout=3)
                        self.assertFalse(thread.is_alive())

                    stack.callback(cleanup)

                    def transport(session, method, url, **kwargs):
                        parsed = urlsplit(url)
                        self.assertEqual((parsed.scheme, parsed.hostname, parsed.port), ("http", "127.0.0.1", port))
                        session.trust_env = False
                        return self.original_transport(session, method, url, **kwargs)

                    def route(method):
                        def send(url, **kwargs):
                            parsed = urlsplit(url)
                            self.assertEqual((parsed.scheme, parsed.netloc), ("https", "www.googleapis.com"))
                            return real_sends[method](f"http://127.0.0.1:{port}{parsed.path}", **kwargs)

                        return send

                    stack.enter_context(
                        patch(
                            "requests.sessions.Session.request", autospec=self.original_transport, side_effect=transport
                        )
                    )
                    for method, send in sends.items():
                        send.side_effect = route(method)
                    expected = (
                        "invalid-response"
                        if changed
                        else (
                            GoogleCalendarSync.Status.DELETED
                            if mode.startswith("cancel")
                            else GoogleCalendarSync.Status.SYNCED
                        )
                    )
                    self.assertEqual(self._execute(), expected)
                    self.assertEqual(
                        remote["calls"], [("DELETE" if mode.startswith("cancel") else "PUT", event["etag"])]
                    )
                    self.assertEqual(remote["writes"], 0 if changed else 1)
                    self.assertEqual(
                        remote["body"],
                        "private existing event" if changed else "deleted" if mode.startswith("cancel") else "updated",
                    )
                    if changed:
                        self._failed(self.changed)
                    retry.assert_not_called()
