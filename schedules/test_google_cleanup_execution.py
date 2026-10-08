"""Cleanup during a write cannot erase its independent request boundary."""

from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import requests
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.billing_deletion import delete_account_after_billing_check
from schedules import tasks
from schedules.google_dispatch_outbox import open_google_dispatch
from schedules.google_job_lifecycle import mark_stalled_google_jobs
from schedules.models import (
    AsyncJob,
    GoogleCalendarSync,
    GoogleIntegration,
    GoogleJobDispatch,
    GoogleWriteAdmission,
    GoogleWriteExecution,
    GoogleWriteExecutionTarget,
    GoogleWriteRequest,
    GoogleWriteReservation,
    GoogleWriteTarget,
    TRPGSession,
)
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleCleanupExecutionTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _accepted(self, mode):
        # Real API, sealed admission and outbox; only the broker is unavailable.
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self._dispatch(mode)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        return job, open_google_dispatch(job.google_dispatch)

    def _delete_owner(self, job):
        owner_id = job.owner_id
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            delete_account_after_billing_check(self.user)
            stripe.assert_not_called()
        self.assertFalse(get_user_model().objects.filter(pk=owner_id).exists())
        self.assertFalse(SocialAccount.objects.filter(user_id=owner_id).exists())
        self.assertFalse(GoogleIntegration.objects.filter(user_id=owner_id).exists())

    def _delete_job(self, job):
        AsyncJob.objects.filter(pk=job.pk).delete()

    def _expire_job(self, job):
        AsyncJob.objects.filter(pk=job.pk).update(expires_at=timezone.now() - timedelta(days=8))
        self.assertEqual(tasks.expire_async_jobs.run(), 1)

    def _delete_session(self, job):
        TRPGSession.objects.filter(pk=self.session.pk).delete()
        self.assertFalse(GoogleCalendarSync.objects.filter(pk=self.sync.pk).exists())

    def _delete_sync(self, job):
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).delete()

    def _expire_execution(self, job):
        AsyncJob.objects.filter(pk=job.pk).update(execution_deadline=timezone.now() - timedelta(seconds=1))
        self.assertEqual(mark_stalled_google_jobs(AsyncJob.objects.filter(pk=job.pk)), 1)

    def _journal(self):
        return (
            list(GoogleWriteExecution.objects.order_by("token").values()),
            list(GoogleWriteExecutionTarget.objects.order_by("pk").values()),
            list(GoogleWriteRequest.objects.order_by("pk").values()),
            list(GoogleWriteTarget.objects.order_by("pk").values()),
        )

    def _waiting(self, mode):
        job, args = self._accepted(mode)
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        delivery = GoogleJobDispatch.objects.filter(job=job).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(self._worker(mode).run(*args), "target-waiting")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        self.assertEqual(GoogleJobDispatch.objects.filter(job=job).values().get(), delivery)
        self.assertEqual(delivery["state"], GoogleJobDispatch.State.PENDING)
        self.assertTrue(delivery["ciphertext"])
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_state"], "target_waiting")
        self.assertFalse(response.data["can_retry"])
        return response.data

    def _follow_after_cleanup(self, mode, cleanup, source_id, execution_token):
        if mode == "sheets":
            # A genuinely different owner/Google identity and the same sheet.
            account = SocialAccount.objects.create(user=self.other, provider="google", uid="cleanup-other-google")
            SocialToken.objects.create(account=account, token="isolated-token")  # Synthetic fixture. # nosec B106
            GoogleIntegration.objects.create(
                user=self.other, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
            )
            self.api.force_authenticate(self.other)
        else:
            if cleanup == "session":
                self.session = TRPGSession.objects.create(
                    pk=self.session.pk,
                    title="削除後に作成した別世代の予定",
                    group=self.session.group,
                    gm=self.user,
                    date=timezone.now() + timedelta(days=1),
                )
            if cleanup in {"session", "sync"}:
                self.sync = GoogleCalendarSync.objects.create(user=self.user, session=self.session)
            self.api.force_authenticate(self.user)
        data = self._waiting(mode)
        for private in (str(source_id), str(execution_token), "allocation_binding", "active_execution_token"):
            self.assertNotIn(private, str(data))

    def _during_cleanup(self, mode, cleanup, known):
        self.fixture_sheet_id = "cleanup-shared-sheet-fixture"
        job, args = self._accepted(mode)
        source_id = job.pk
        source_gone = cleanup in {"owner", "job", "expiry"}
        closed = known and cleanup in {"session", "sync"}
        captured = []

        def response_after_cleanup(url, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            job.refresh_from_db()
            execution = GoogleWriteExecution.objects.get(token=job.execution_token)
            request = execution.requests.get()
            allocations = list(execution.allocations.order_by("target_id").values_list("target_id", "sequence"))
            self.assertEqual(len(allocations), 2 if mode == "calendar" else 1)
            self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
            self.assertEqual((request.state, request.response_status), (GoogleWriteRequest.State.INTENT, None))
            self.assertRegex(request.request_digest, r"^[0-9a-f]{64}$")
            captured.append((execution, request, allocations))
            cleanup_action = {
                "owner": self._delete_owner,
                "job": self._delete_job,
                "expiry": self._expire_job,
                "session": self._delete_session,
                "sync": self._delete_sync,
                "deadline": self._expire_execution,
            }[cleanup]
            cleanup_action(job)
            if not known:
                raise requests.Timeout("Synthetic response loss after cleanup")
            return self.response(200, {"id": kwargs["json"]["id"]} if mode == "calendar" else {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            method = "post" if mode == "calendar" else "put"
            sends[method].side_effect = response_after_cleanup
            expected = "uncertain" if not known and cleanup in {"session", "sync"} else "inactive-job"
            self.assertEqual(self._worker(mode).run(*args), expected)
            sends[method].assert_called_once()
            for other_method in set(sends) - {method}:
                sends[other_method].assert_not_called()
        self.assertEqual(len(captured), 1)
        execution, request, allocations = captured[0]
        identity = (
            execution.job_id_snapshot,
            execution.admission_binding,
            execution.allocation_binding,
            execution.created_at,
        )
        digest = (request.pk, request.request_digest, request.ordinal, request.created_at)
        execution.refresh_from_db()
        request.refresh_from_db()
        self.assertEqual(
            (
                execution.job_id_snapshot,
                execution.admission_binding,
                execution.allocation_binding,
                execution.created_at,
            ),
            identity,
        )
        self.assertEqual((request.pk, request.request_digest, request.ordinal, request.created_at), digest)
        self.assertEqual(
            (request.state, request.response_status),
            (GoogleWriteRequest.State.KNOWN, 200) if known else (GoogleWriteRequest.State.UNKNOWN, None),
        )
        self.assertIsNotNone(request.received_at)
        self.assertEqual(
            list(execution.allocations.order_by("target_id").values_list("target_id", "sequence")), allocations
        )
        if closed:
            # Known response + failed current source + no further sends is the
            # existing proven-terminal rule, not cleanup or a timer unlocking.
            self.assertEqual(execution.state, GoogleWriteExecution.State.FINISHED)
            self.assertIsNotNone(execution.closed_at)
        else:
            self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
            self.assertIsNone(execution.closed_at)
        for target_id, sequence in allocations:
            target = GoogleWriteTarget.objects.get(pk=target_id)
            self.assertRegex(target.resource_key, r"^[0-9a-f]{64}$")
            self.assertEqual(target.last_started_sequence, sequence)
            self.assertEqual(target.active_execution_token, None if closed else execution.pk)
        if cleanup == "owner":
            self.assertFalse(get_user_model().objects.filter(pk=job.owner_id).exists())
            self.assertFalse(GoogleCalendarSync.objects.filter(user_id=job.owner_id).exists())
            self.assertFalse(SocialToken.objects.filter(account__user_id=job.owner_id).exists())
        if cleanup == "session":
            self.assertFalse(TRPGSession.objects.filter(pk=self.session.pk).exists())
        if cleanup in {"session", "sync"}:
            self.assertFalse(GoogleCalendarSync.objects.filter(pk=self.sync.pk).exists())
        if source_gone:
            self.assertFalse(AsyncJob.objects.filter(pk=source_id).exists())
            self.assertFalse(GoogleJobDispatch.objects.filter(job_id=source_id).exists())
            self.assertFalse(GoogleWriteAdmission.objects.filter(job_id=source_id).exists())
            self.assertFalse(GoogleWriteReservation.objects.exists())
        else:
            job.refresh_from_db()
            self.assertEqual(job.status, AsyncJob.Status.FAILED if closed else AsyncJob.Status.UNCERTAIN)
            self.assertTrue(job.google_write_admission.ciphertext)
            self.assertEqual(job.google_dispatch.ciphertext, "")
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get(reverse("async-job-detail", kwargs={"pk": source_id})).status_code, 404)
        journal = self._journal()
        for plaintext in ("isolated-token", "Initial title", "delivery-fixture", "cleanup-shared-sheet-fixture"):
            self.assertNotIn(plaintext, repr(journal))
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            expected = "invalid-job" if source_gone or cleanup in {"session", "sync"} else "inactive-job"
            self.assertEqual(self._worker(mode).run(*args), expected)
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(self._journal(), journal)
        if not closed and (mode == "sheets" or cleanup != "owner"):
            execution_before = GoogleWriteExecution.objects.filter(pk=execution.pk).values().get()
            request_before = GoogleWriteRequest.objects.filter(pk=request.pk).values().get()
            self._follow_after_cleanup(mode, cleanup, source_id, execution.pk)
            self.assertEqual(GoogleWriteExecution.objects.filter(pk=execution.pk).values().get(), execution_before)
            self.assertEqual(GoogleWriteRequest.objects.filter(pk=request.pk).values().get(), request_before)

    def test_calendar_owner_cleanup_known_response(self):
        self._during_cleanup("calendar", "owner", True)

    def test_calendar_owner_cleanup_lost_response(self):
        self._during_cleanup("calendar", "owner", False)

    def test_calendar_job_cleanup_known_response(self):
        self._during_cleanup("calendar", "job", True)

    def test_calendar_job_cleanup_lost_response(self):
        self._during_cleanup("calendar", "job", False)

    def test_calendar_expiry_cleanup_known_response(self):
        self._during_cleanup("calendar", "expiry", True)

    def test_calendar_expiry_cleanup_lost_response(self):
        self._during_cleanup("calendar", "expiry", False)

    def test_calendar_session_cleanup_known_response(self):
        self._during_cleanup("calendar", "session", True)

    def test_calendar_session_cleanup_lost_response(self):
        self._during_cleanup("calendar", "session", False)

    def test_calendar_sync_cleanup_known_response(self):
        self._during_cleanup("calendar", "sync", True)

    def test_calendar_sync_cleanup_lost_response(self):
        self._during_cleanup("calendar", "sync", False)

    def test_calendar_execution_deadline_known_response(self):
        self._during_cleanup("calendar", "deadline", True)

    def test_calendar_execution_deadline_lost_response(self):
        self._during_cleanup("calendar", "deadline", False)

    def test_sheets_owner_cleanup_known_response(self):
        self._during_cleanup("sheets", "owner", True)

    def test_sheets_owner_cleanup_lost_response(self):
        self._during_cleanup("sheets", "owner", False)

    def test_sheets_job_cleanup_known_response(self):
        self._during_cleanup("sheets", "job", True)

    def test_sheets_job_cleanup_lost_response(self):
        self._during_cleanup("sheets", "job", False)

    def test_sheets_expiry_cleanup_known_response(self):
        self._during_cleanup("sheets", "expiry", True)

    def test_sheets_expiry_cleanup_lost_response(self):
        self._during_cleanup("sheets", "expiry", False)

    def test_sheets_execution_deadline_known_response(self):
        self._during_cleanup("sheets", "deadline", True)

    def test_sheets_execution_deadline_lost_response(self):
        self._during_cleanup("sheets", "deadline", False)


class GoogleCleanupCiTest(SimpleTestCase):
    def test_production_database_job_selects_cleanup_boundaries(self):
        workflow = (Path(settings.BASE_DIR) / ".github/workflows/django-ci.yml").read_text(encoding="utf-8")
        production_job = workflow.split("  production-database:", 1)[1].split("  playwright:", 1)[0]
        self.assertIn("schedules/test_google_cleanup_execution.py", production_job)
