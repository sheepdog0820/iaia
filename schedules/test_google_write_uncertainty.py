import json
import socket
import threading
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from celery.exceptions import Retry
from django.test import TestCase

from schedules import tasks
from schedules import test_google_calendar_event_guard as event_guard_tests
from schedules.google_job_lifecycle import GOOGLE_EXECUTION_UNCERTAIN_MESSAGE
from schedules.models import AsyncJob, GoogleCalendarSync
from schedules.test_google_job_start_claim import GoogleJobStartFixtures
from tests.utils.google_sheet_fixtures import run_sheet_fixture
from tests.utils.google_subcases import rollback_google_subcase


class GoogleWriteUncertaintyTest(GoogleJobStartFixtures, TestCase):
    def _assert_uncertain(self, job, mode, args, retry, sync_before):
        retry.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.UNCERTAIN)
        self.assertEqual(job.error, GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(job.execution_token)
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get(), sync_before)
        count = AsyncJob.objects.count()
        response = self.api.post(f"/api/jobs/{job.pk}/retry/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)
        self.assertEqual(AsyncJob.objects.count(), count)
        self._refuse_unchanged(mode, job, args)

    def _calendar_mode(self, operation):
        self.session.status = "cancelled" if operation == "delete" else "planned"
        self.session.save(update_fields=["status"])
        self.sync.external_event_id = "existing-write-fixture" if operation in ("put", "delete") else ""
        self.sync.save(update_fields=["external_event_id"])

    def test_lost_write_responses_and_server_errors_are_not_automatically_reapplied(self):
        for operation in ("post", "put", "delete", "conflict-put", "sheets"):
            for failure in ("timeout", "disconnect", "server", "request-timeout"):
                with (
                    self.subTest(operation=operation, failure=failure),
                    rollback_google_subcase(),
                    ExitStack() as stack,
                ):
                    mode = "sheets" if operation == "sheets" else "calendar"
                    self._calendar_mode(operation)
                    job, args = self._queue(mode)
                    sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    self._sends(stack)
                    if operation == "conflict-put":
                        stack.enter_context(patch("schedules.tasks.requests.post", return_value=self.response(409, {})))
                    send = "put" if operation in ("sheets", "conflict-put") else operation
                    applied = []

                    def write(*args, **kwargs):
                        # Fake provider has applied the mutation before its response is lost/invalid.
                        applied.append(kwargs)
                        if failure in ("server", "request-timeout"):
                            return self.response(503 if failure == "server" else 408, {"private": "診断"})
                        raise (requests.Timeout if failure == "timeout" else requests.ConnectionError)(
                            "private provider response / token / target"
                        )

                    stack.enter_context(patch(f"schedules.tasks.requests.{send}", side_effect=write))
                    retry = stack.enter_context(patch.object(self._worker(mode), "retry", side_effect=Retry()))
                    self.assertEqual(self._worker(mode).run(*args), "uncertain")
                    self.assertEqual(len(applied), 1)
                    self._assert_uncertain(job, mode, args, retry, sync_before)

    def test_malformed_successful_write_acknowledgement_is_not_retryable(self):
        for mode in ("calendar", "sheets"):
            for body in (None, [], "private response", {"id": "wrong"}, ValueError("private invalid JSON")):
                with self.subTest(mode=mode, body=body), rollback_google_subcase(), ExitStack() as stack:
                    self._calendar_mode("post")
                    job, args = self._queue(mode)
                    sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                    self._sends(stack)
                    response = self.response(200, body)
                    if isinstance(body, ValueError):
                        response.json.side_effect = body
                    elif mode == "sheets" and isinstance(body, dict):
                        response.json.return_value = {"updatedCells": "private invalid count"}
                    stack.enter_context(
                        patch(
                            f"schedules.tasks.requests.{'put' if mode == 'sheets' else 'post'}", return_value=response
                        )
                    )
                    retry = stack.enter_context(patch.object(self._worker(mode), "retry", side_effect=Retry()))
                    self.assertEqual(self._worker(mode).run(*args), "uncertain")
                    self._assert_uncertain(job, mode, args, retry, sync_before)

    def test_read_failure_still_uses_existing_safe_read_retry(self):
        self._calendar_mode("put")
        job, args = self._queue("calendar")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            stack.enter_context(patch("schedules.tasks.requests.get", side_effect=requests.Timeout("private read")))
            retry = stack.enter_context(patch.object(tasks.sync_google_calendar, "retry", side_effect=Retry()))
            with self.assertRaises(Retry):
                tasks.sync_google_calendar.run(*args)
            retry.assert_called_once()
            sends["put"].assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.FAILED)
        self.assertNotIn("private read", job.error)

    def test_partial_sheet_write_is_not_replayed_after_later_rejection(self):
        job, _ = self._queue("sheets")
        with ExitStack() as stack:
            self._sends(stack)
            put = stack.enter_context(
                patch(
                    "schedules.tasks.requests.put",
                    side_effect=[self.response(200, {"updatedCells": 1700}), self.response(403, {})],
                )
            )
            retry = stack.enter_context(patch.object(tasks.export_google_sheet, "retry", side_effect=Retry()))
            self.assertEqual(
                run_sheet_fixture(
                    str(job.pk), self.user.pk, "isolated-content-sheet", "Characters!A1", [[row] for row in range(201)]
                ),
                "uncertain",
            )
            self.assertEqual(put.call_count, 2)
            retry.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, AsyncJob.Status.UNCERTAIN)
        self.assertEqual(job.progress, 49)
        self.assertEqual(job.result, {})
        self.assertEqual(job.error, GOOGLE_EXECUTION_UNCERTAIN_MESSAGE)

    def test_explicit_first_write_rejection_keeps_existing_failure_handling(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                self._calendar_mode("post")
                job, args = self._queue(mode)
                self._sends(stack)
                stack.enter_context(
                    patch(
                        f"schedules.tasks.requests.{'put' if mode == 'sheets' else 'post'}",
                        return_value=self.response(403, {}),
                    )
                )
                retry = stack.enter_context(patch.object(self._worker(mode), "retry", side_effect=Retry()))
                with self.assertRaises(Retry):
                    self._worker(mode).run(*args)
                retry.assert_called_once()
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)

    def test_real_loopback_applied_then_response_lost_never_retries_or_resends(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                self._calendar_mode("post")
                job, args = self._queue(mode)
                sync_before = GoogleCalendarSync.objects.filter(pk=self.sync.pk).values().get()
                writes = []

                class Provider(BaseHTTPRequestHandler):
                    def apply(self):
                        body = self.rfile.read(int(self.headers["Content-Length"]))
                        writes.append((self.command, self.path, json.loads(body)))
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()

                    do_POST = apply
                    do_PUT = apply

                    def log_message(self, *args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:

                    def transport(session, method, url, **kwargs):
                        parsed = urlsplit(url)
                        if parsed.scheme != "https" or parsed.netloc not in {
                            "www.googleapis.com",
                            "sheets.googleapis.com",
                        }:
                            raise AssertionError("External provider HTTP forbidden")
                        self.assertEqual(method.lower(), "put" if mode == "sheets" else "post")
                        # This is real Requests HTTP, confined to this dynamically bound loopback server.
                        session.trust_env = False
                        return event_guard_tests.GoogleCalendarEventGuardTest.original_transport(
                            session,
                            method,
                            f"http://127.0.0.1:{server.server_port}{parsed.path}",
                            **kwargs,
                        )

                    with (
                        patch("requests.sessions.Session.request", new=transport),
                        patch("schedules.tasks.get_google_access_token", return_value="isolated-token"),
                        patch.object(self._worker(mode), "retry", side_effect=Retry()) as retry,
                    ):
                        self.assertEqual(self._worker(mode).run(*args), "uncertain")
                        self.assertEqual(len(writes), 1)
                        self._assert_uncertain(job, mode, args, retry, sync_before)
                        self.assertEqual(len(writes), 1)
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
