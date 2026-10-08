"""Different jobs must share execution rights, not just their own claim rows."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack
from datetime import timedelta
from importlib import import_module
from threading import Barrier, Event
from time import monotonic, sleep
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

import requests
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.query import QuerySet
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules import tasks
from schedules.google_dispatch_outbox import open_google_dispatch
from schedules.models import (
    AsyncJob,
    GoogleCalendarSync,
    GoogleIntegration,
    GoogleJobDispatch,
    GoogleWriteAdmission,
    GoogleWriteExecution,
    GoogleWriteExecutionTarget,
    GoogleWriteRequest,
    GoogleWriteTarget,
)
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures
from tests.utils.google_subcases import rollback_google_subcase


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleTargetExecutionTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _accepted(self, mode):
        # Exercise the real API -> admission -> encrypted outbox transaction.
        # Only the external broker is unavailable; workers are never mocked.
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self._dispatch(mode)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        return job, open_google_dispatch(job.google_dispatch)

    def _accepted_sheet(self, spreadsheet_id, range_name):
        with patch.object(tasks, "_broker_available", return_value=False):
            response = self.api.post(
                "/api/character-sheets/google-sheets/export/",
                {"spreadsheet_id": spreadsheet_id, "range": range_name},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        job = AsyncJob.objects.get(pk=response.data["job_id"])
        return job, open_google_dispatch(job.google_dispatch)

    def _waiting(self, mode, job, args):
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
        self.assertTrue(delivery["ciphertext"])
        self.assertEqual(delivery["state"], GoogleJobDispatch.State.PENDING)

    def test_newer_calendar_cannot_start_before_earlier_accepted_job(self):
        first, first_args = self._accepted("calendar")
        second, second_args = self._accepted("calendar")
        self._waiting("calendar", second, second_args)
        with ExitStack() as stack:
            self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*first_args), "synced")
            self.assertEqual(tasks.sync_google_calendar.run(*second_args), "synced")
        self.assertEqual(AsyncJob.objects.filter(status=AsyncJob.Status.SUCCEEDED).count(), 2)

    def test_calendar_busy_holder_keeps_other_job_and_dispatch_unstarted(self):
        first, first_args = self._accepted("calendar")
        second, second_args = self._accepted("calendar")
        observed = []

        def applied(url, **kwargs):
            self._waiting("calendar", second, second_args)
            observed.append("blocked")
            return self.response(200, {"id": kwargs["json"]["id"]})

        with ExitStack() as stack:
            sends, token = self._sends(stack)
            sends["post"].side_effect = applied
            self.assertEqual(tasks.sync_google_calendar.run(*first_args), "synced")
            token.assert_called_once()
            sends["post"].assert_called_once()
        self.assertEqual(observed, ["blocked"])
        first.refresh_from_db()
        self.assertEqual(first.status, AsyncJob.Status.SUCCEEDED)

    def test_calendar_receipt_preserves_newer_pending_and_known_event_id(self):
        first, args = self._accepted("calendar")
        accepted = []

        def applied(url, **kwargs):
            accepted.append(self._accepted("calendar"))
            return self.response(200, {"id": kwargs["json"]["id"]})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["post"].side_effect = applied
            self.assertEqual(tasks.sync_google_calendar.run(*args), "synced")
            event_id = sends["post"].call_args.kwargs["json"]["id"]
        self.sync.refresh_from_db()
        first.refresh_from_db()
        newer, _ = accepted[0]
        newer.refresh_from_db()
        self.assertEqual(first.status, AsyncJob.Status.SUCCEEDED)
        self.assertEqual(newer.status, AsyncJob.Status.QUEUED)
        self.assertEqual(self.sync.external_event_id, event_id)
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.PENDING)

    def test_sheet_unknown_is_not_bypassed_by_new_job_expiry_or_source_deletion(self):
        first, args = self._accepted("sheets")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = requests.Timeout("Synthetic response loss")
            self.assertEqual(tasks.export_google_sheet.run(*args), "uncertain")
            sends["put"].assert_called_once()
        second, second_args = self._accepted("sheets")
        self._waiting("sheets", second, second_args)
        AsyncJob.objects.filter(pk=first.pk).update(expires_at=timezone.now() - timedelta(days=8))
        self.assertEqual(tasks.expire_async_jobs.run(), 1)
        self.assertFalse(AsyncJob.objects.filter(pk=first.pk).exists())
        self._waiting("sheets", second, second_args)

    def test_sheet_holder_is_not_released_between_chunks(self):
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(character_sheet=character, name="分割中の非公開行")
        first, args = self._accepted("sheets")
        accepted = []

        def applied(url, **kwargs):
            if not accepted:
                accepted.append(self._accepted("sheets"))
                self._waiting("sheets", *accepted[0])
            return self.response(200, {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = applied
            stack.enter_context(patch.object(tasks, "SHEETS_EXPORT_CHUNK_ROWS", 1))
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
            self.assertEqual(sends["put"].call_count, 2)
        with ExitStack() as stack:
            self._sends(stack)
            self.assertEqual(tasks.export_google_sheet.run(*accepted[0][1]), "exported")

    def test_intent_is_visible_before_http_and_known_receipt_closes_holder(self):
        job, args = self._accepted("sheets")

        def applied(url, **kwargs):
            job.refresh_from_db()
            execution = GoogleWriteExecution.objects.get(token=job.execution_token)
            request = execution.requests.get()
            self.assertEqual(execution.state, GoogleWriteExecution.State.ACTIVE)
            self.assertEqual(request.state, GoogleWriteRequest.State.INTENT)
            self.assertEqual(request.ordinal, 1)
            self.assertIsNone(request.response_status)
            self.assertRegex(request.request_digest, r"^[0-9a-f]{64}$")
            self.assertEqual(
                list(execution.allocations.values_list("target__active_execution_token", flat=True)), [execution.pk]
            )
            return self.response(200, {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = applied
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
        request = execution.requests.get()
        self.assertEqual(execution.state, GoogleWriteExecution.State.FINISHED)
        self.assertIsNotNone(execution.closed_at)
        self.assertEqual((request.state, request.response_status), (GoogleWriteRequest.State.KNOWN, 200))
        self.assertFalse(GoogleWriteTarget.objects.exclude(active_execution_token=None).exists())

    def test_receipt_database_failure_keeps_independent_intent_and_blocks_other_job(self):
        job, args = self._accepted("sheets")
        original_update = QuerySet.update

        def save(query, **values):
            if query.model is GoogleWriteRequest:
                raise DatabaseError("Synthetic receipt persistence failure")
            return original_update(query, **values)

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            stack.enter_context(patch.object(QuerySet, "update", new=save))
            with self.assertRaises(DatabaseError):
                tasks.export_google_sheet.run(*args)
            sends["put"].assert_called_once()
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_source_deleted_after_http_keeps_known_receipt_but_never_silently_unlocks(self):
        job, args = self._accepted("sheets")
        source_id = job.pk

        def applied(url, **kwargs):
            AsyncJob.objects.filter(pk=source_id).delete()
            return self.response(200, {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = applied
            self.assertEqual(tasks.export_google_sheet.run(*args), "inactive-job")
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=source_id)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.KNOWN)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_calendar_source_cleanup_retains_verified_id_without_recreating_job_or_unlocking(self):
        job, args = self._accepted("calendar")
        source_id = job.pk
        applied_id = []

        def applied(url, **kwargs):
            AsyncJob.objects.filter(pk=source_id).delete()
            applied_id.append(kwargs["json"]["id"])
            return self.response(200, {"id": applied_id[0]})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["post"].side_effect = applied
            self.assertEqual(tasks.sync_google_calendar.run(*args), "inactive-job")
            sends["post"].assert_called_once()
        self.assertFalse(AsyncJob.objects.filter(pk=source_id).exists())
        self.sync.refresh_from_db()
        self.assertEqual(self.sync.external_event_id, applied_id[0])
        self.assertEqual(self.sync.status, GoogleCalendarSync.Status.SYNCED)
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=source_id)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.KNOWN)
        self._waiting("calendar", *self._accepted("calendar"))

    def test_whole_sheet_is_shared_across_owner_connection_and_nonoverlapping_range(self):
        first, args = self._accepted_sheet("shared-target-fixture", "First!A1")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = requests.Timeout("Synthetic uncertainty")
            self.assertEqual(tasks.export_google_sheet.run(*args), "uncertain")
        account = SocialAccount.objects.create(user=self.other, provider="google", uid="different-google-fixture")
        SocialToken.objects.create(account=account, token=SocialToken.objects.get(account__user=self.user).token)
        GoogleIntegration.objects.create(
            user=self.other, sheets_enabled=True, scopes=[GoogleIntegration.REQUIRED_SHEETS_SCOPE]
        )
        self.api.force_authenticate(self.other)
        second, second_args = self._accepted_sheet("shared-target-fixture", "Unrelated!Z99")
        self._waiting("sheets", second, second_args)
        response = self.api.get(reverse("async-job-detail", kwargs={"pk": second.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(str(first.pk), str(response.data))
        independent, independent_args = self._accepted_sheet("independent-target-fixture", "First!A1")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.export_google_sheet.run(*independent_args), "exported")
            sends["put"].assert_called_once()
        independent.refresh_from_db()
        self.assertEqual(independent.status, AsyncJob.Status.SUCCEEDED)

    def test_older_failed_job_cannot_restart_after_later_sequence_started(self):
        first, args = self._accepted("sheets")
        with ExitStack() as stack:
            self._sends(stack)
            stack.enter_context(
                patch.object(tasks, "get_google_access_token", side_effect=ValueError("試験用の認可拒否"))
            )
            self.assertEqual(tasks.export_google_sheet.run(*args), "missing-token")
        second, second_args = self._accepted("sheets")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.export_google_sheet.run(*second_args), "exported")
            sends["put"].assert_called_once()
        before = AsyncJob.objects.filter(pk=first.pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(tasks.export_google_sheet.run(*args), "inactive-job")
            token.assert_not_called()
            sends["put"].assert_not_called()
        self.assertEqual(AsyncJob.objects.filter(pk=first.pk).values().get(), before)

    def test_forged_execution_token_does_not_create_request_or_unlock_target(self):
        from uuid import uuid4

        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        original_token = job.execution_token
        job.execution_token = uuid4()
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
        self.assertFalse(GoogleWriteRequest.objects.exists())
        self.assertEqual(GoogleWriteTarget.objects.get().active_execution_token, original_token)

    def test_altered_allocation_and_matching_target_sequence_cannot_authorize_http(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        allocation = GoogleWriteExecutionTarget.objects.get(execution_id=job.execution_token)
        GoogleWriteExecutionTarget.objects.filter(pk=allocation.pk).update(sequence=allocation.sequence + 1)
        GoogleWriteTarget.objects.filter(pk=allocation.target_id).update(last_started_sequence=allocation.sequence + 1)
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
        self.assertFalse(GoogleWriteRequest.objects.exists())

    def test_remapped_allocation_cannot_authorize_another_target_even_with_matching_marker(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        allocation = GoogleWriteExecutionTarget.objects.get(execution_id=job.execution_token)
        replacement = GoogleWriteTarget.objects.create(
            resource_key="f" * 64, last_sequence=1, last_started_sequence=1, active_execution_token=job.execution_token
        )
        GoogleWriteExecutionTarget.objects.filter(pk=allocation.pk).update(target=replacement)
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
        self.assertFalse(GoogleWriteRequest.objects.exists())

    def test_missing_marker_after_http_preserves_unknown_without_masking_inactive_result(self):
        job, args = self._accepted("sheets")

        def applied(url, **kwargs):
            GoogleWriteTarget.objects.update(active_execution_token=None)
            return self.response(200, {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = applied
            self.assertEqual(tasks.export_google_sheet.run(*args), "inactive-job")
            sends["put"].assert_called_once()
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertIsNone(execution.closed_at)
        self.assertEqual(execution.requests.get().state, GoogleWriteRequest.State.INTENT)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_unknown_execution_blocks_later_job_when_target_marker_is_missing(self):
        first, args = self._accepted("sheets")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = requests.Timeout("Synthetic response uncertainty")
            self.assertEqual(tasks.export_google_sheet.run(*args), "uncertain")
        GoogleWriteTarget.objects.update(active_execution_token=None)
        self._waiting("sheets", *self._accepted("sheets"))
        self.assertEqual(
            GoogleWriteExecution.objects.get(job_id_snapshot=first.pk).state, GoogleWriteExecution.State.UNKNOWN
        )

    def test_claim_update_rejection_rolls_back_holder_and_keeps_encrypted_dispatch(self):
        from schedules.google_job_lifecycle import claim_google_job_start

        job, _ = self._accepted("sheets")
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        delivery = GoogleJobDispatch.objects.filter(job=job).values().get()
        with patch.object(QuerySet, "update", return_value=0) as reject:
            self.assertFalse(claim_google_job_start(job))
        reject.assert_called_once()
        self.assertEqual(reject.call_args.kwargs["status"], AsyncJob.Status.RUNNING)
        self.assertFalse(GoogleWriteExecution.objects.exists())
        self.assertFalse(GoogleWriteTarget.objects.exclude(active_execution_token=None).exists())
        self.assertEqual(GoogleWriteTarget.objects.get().last_started_sequence, 0)
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        self.assertEqual(GoogleJobDispatch.objects.filter(job=job).values().get(), delivery)

    def test_claim_refresh_source_deletion_preserves_unknown_without_recreating_job(self):
        from schedules.google_job_lifecycle import claim_google_job_start

        job, _ = self._accepted("sheets")
        original = AsyncJob.refresh_from_db

        def remove(instance, *args, **kwargs):
            AsyncJob.objects.filter(pk=instance.pk).delete()
            return original(instance, *args, **kwargs)

        with patch.object(AsyncJob, "refresh_from_db", new=remove):
            self.assertFalse(claim_google_job_start(job))
        self.assertFalse(AsyncJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(GoogleJobDispatch.objects.filter(job_id=job.pk).exists())
        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertIsNone(execution.closed_at)
        self.assertEqual(GoogleWriteTarget.objects.get().active_execution_token, execution.pk)
        self.assertFalse(GoogleWriteRequest.objects.exists())
        self._waiting("sheets", *self._accepted("sheets"))

    def test_matching_admission_and_execution_binding_tamper_cannot_authorize_http(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        GoogleWriteAdmission.objects.filter(job=job).update(snapshot_binding="a" * 64)
        GoogleWriteExecution.objects.filter(token=job.execution_token).update(admission_binding="a" * 64)
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
        self.assertFalse(GoogleWriteRequest.objects.exists())

    def test_changed_allocation_cannot_close_holder_even_with_terminal_source(self):
        from schedules.google_job_lifecycle import claim_google_job_start
        from schedules.google_target_execution import finish_execution

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        allocation = GoogleWriteExecutionTarget.objects.get(execution_id=job.execution_token)
        GoogleWriteExecutionTarget.objects.filter(pk=allocation.pk).update(sequence=allocation.sequence + 1)
        GoogleWriteTarget.objects.filter(pk=allocation.target_id).update(last_started_sequence=allocation.sequence + 1)
        AsyncJob.objects.filter(pk=job.pk).update(status=AsyncJob.Status.FAILED)
        finish_execution(job)
        execution = GoogleWriteExecution.objects.get(token=job.execution_token)
        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
        self.assertIsNone(execution.closed_at)
        self.assertEqual(GoogleWriteTarget.objects.get().active_execution_token, job.execution_token)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_other_job_execution_token_cannot_change_or_close_that_holder(self):
        from schedules.google_job_lifecycle import claim_google_job_start
        from schedules.google_target_execution import finish_execution

        first, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(first))
        second, _ = self._accepted("sheets")
        second.execution_token = first.execution_token
        before = GoogleWriteExecution.objects.values().get()
        finish_execution(second)
        self.assertEqual(GoogleWriteExecution.objects.values().get(), before)
        self.assertEqual(GoogleWriteTarget.objects.get().active_execution_token, first.execution_token)

    def test_unavailable_signing_material_stops_http_and_retains_unknown_holder(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request, finish_execution

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        with override_settings(SECRET_KEY=None), ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
            finish_execution(job)
        self.assertEqual(GoogleWriteExecution.objects.get().state, GoogleWriteExecution.State.UNKNOWN)
        self.assertFalse(GoogleWriteRequest.objects.exists())
        self._waiting("sheets", *self._accepted("sheets"))

    def test_removed_or_changed_admission_cannot_authorize_existing_execution(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import execution_write_request, finish_execution

        for alteration in ("removed", "changed"):
            with self.subTest(alteration=alteration):
                job, _ = self._accepted_sheet(f"admission-{alteration}", "A1")
                self.assertTrue(claim_google_job_start(job))
                query = GoogleWriteAdmission.objects.filter(job=job)
                if alteration == "removed":
                    query.delete()
                else:
                    query.update(snapshot_binding="b" * 64)
                with ExitStack() as stack:
                    sends, _ = self._sends(stack)
                    with self.assertRaises(GoogleJobInactive):
                        execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
                    sends["put"].assert_not_called()
                finish_execution(job)
                self.assertEqual(
                    GoogleWriteExecution.objects.get(token=job.execution_token).state,
                    GoogleWriteExecution.State.UNKNOWN,
                )
        self.assertFalse(GoogleWriteRequest.objects.exists())

    def test_existing_unclosed_intent_stops_another_send_for_the_same_holder(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import _begin_request, execution_write_request, finish_execution

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        intent = _begin_request(job, "PUT", "https://example.invalid/isolated", {})
        before = GoogleWriteRequest.objects.values().get()
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            with self.assertRaises(GoogleJobInactive):
                execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            sends["put"].assert_not_called()
        self.assertEqual(GoogleWriteRequest.objects.values().get(), before)
        self.assertEqual(intent.state, GoogleWriteRequest.State.INTENT)
        finish_execution(job)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_duplicate_receipt_cannot_replace_a_known_response(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_target_execution import _receive_request, execution_write_request, finish_execution

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            response = execution_write_request(job, "PUT", sends["put"], "https://example.invalid/isolated")
            self.assertEqual(response.status_code, 200)
            sends["put"].assert_called_once()
        receipt = GoogleWriteRequest.objects.get()
        before = GoogleWriteRequest.objects.values().get()
        with self.assertRaises(GoogleJobInactive):
            _receive_request(job, receipt, 403)
        self.assertEqual(GoogleWriteRequest.objects.values().get(), before)
        finish_execution(job)
        self._waiting("sheets", *self._accepted("sheets"))

    def test_legacy_source_cleanup_at_refresh_creates_no_execution_or_replacement(self):
        from schedules.google_job_lifecycle import claim_google_job_start

        job, _ = self._accepted("sheets")
        GoogleWriteAdmission.objects.filter(job=job).delete()
        original = AsyncJob.refresh_from_db

        def remove(instance, *args, **kwargs):
            AsyncJob.objects.filter(pk=instance.pk).delete()
            return original(instance, *args, **kwargs)

        with patch.object(AsyncJob, "refresh_from_db", new=remove):
            self.assertFalse(claim_google_job_start(job))
        self.assertFalse(AsyncJob.objects.exists())
        self.assertFalse(GoogleWriteExecution.objects.exists())
        self.assertFalse(GoogleWriteTarget.objects.exclude(active_execution_token=None).exists())


class GoogleExecutionJournalBackendTest(SimpleTestCase):
    def test_reverse_refuses_an_unverified_database_backend_before_accessing_records(self):
        migration = import_module("schedules.migrations.0061_google_shared_execution")
        editor = SimpleNamespace(connection=SimpleNamespace(vendor="unverified"))
        with self.assertRaisesRegex(RuntimeError, "Google.*実行記録.*逆移行"):
            migration.protect_execution_journal(None, editor)


class GoogleExecutionJournalMigrationTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _accepted = GoogleTargetExecutionTest._accepted

    def _assert_reverse_prohibited(self, job):
        before = GoogleWriteExecution.objects.filter(job_id_snapshot=job.pk).values().get()
        allocations = list(GoogleWriteExecutionTarget.objects.values())
        requests_before = list(GoogleWriteRequest.objects.values())
        original_targets = MigrationExecutor(connection).loader.graph.leaf_nodes("schedules")
        try:
            with self.assertRaisesRegex(RuntimeError, "Google.*実行記録.*逆移行"):
                MigrationExecutor(connection).migrate([("schedules", "0060_google_write_delete_cascade")])
            self.assertEqual(GoogleWriteExecution.objects.values().get(), before)
            self.assertEqual(list(GoogleWriteExecutionTarget.objects.values()), allocations)
            self.assertEqual(list(GoogleWriteRequest.objects.values()), requests_before)
        finally:
            MigrationExecutor(connection).migrate(original_targets)

    def test_reverse_cannot_drop_an_active_journal(self):
        from schedules.google_job_lifecycle import claim_google_job_start

        job, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        self._assert_reverse_prohibited(job)

    def test_reverse_cannot_drop_an_unknown_journal_and_request(self):
        job, args = self._accepted("sheets")
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = requests.Timeout("Synthetic uncertain migration fixture")
            self.assertEqual(tasks.export_google_sheet.run(*args), "uncertain")
        self._assert_reverse_prohibited(job)

    def test_reverse_cannot_drop_a_finished_journal_without_a_retention_decision(self):
        job, args = self._accepted("sheets")
        with ExitStack() as stack:
            self._sends(stack)
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
        self._assert_reverse_prohibited(job)


class GoogleSubcaseIsolationTest(GoogleDispatchStateFixtures, TestCase):
    _accepted = GoogleTargetExecutionTest._accepted

    def test_independent_subcases_rollback_unknown_journals_without_unlocking_them(self):
        for _ in range(2):
            with rollback_google_subcase(), ExitStack() as stack:
                job, args = self._accepted("sheets")
                sends, _ = self._sends(stack)
                sends["put"].side_effect = requests.Timeout("Synthetic unknown subcase")
                self.assertEqual(tasks.export_google_sheet.run(*args), "uncertain")
                execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
                self.assertEqual(GoogleWriteTarget.objects.get().active_execution_token, execution.pk)
            self.assertFalse(AsyncJob.objects.exists())
            self.assertFalse(GoogleWriteExecution.objects.exists())
            self.assertFalse(GoogleWriteTarget.objects.exists())

    def test_subcase_rollback_is_retained_after_assertion_or_fixture_exception(self):
        with self.assertRaisesRegex(ValueError, "Synthetic subcase failure"):
            with rollback_google_subcase():
                self._accepted("calendar")
                raise ValueError("Synthetic subcase failure")
        self.assertFalse(AsyncJob.objects.exists())
        self.assertFalse(GoogleWriteTarget.objects.exists())


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の保存SQL障害検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleTargetDatabaseFailureTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _accepted = GoogleTargetExecutionTest._accepted
    _waiting = GoogleTargetExecutionTest._waiting

    def test_server_errors_before_and_after_save_sql_never_release_unknown_writes(self):
        boundaries = (
            ("intent", GoogleWriteRequest, "INSERT", None),
            ("receipt", GoogleWriteRequest, "UPDATE", None),
            ("completion", AsyncJob, "UPDATE", AsyncJob.Status.SUCCEEDED),
            ("journal", GoogleWriteExecution, "UPDATE", GoogleWriteExecution.State.FINISHED),
            ("unlock", GoogleWriteTarget, "UPDATE", None),
        )
        for mode in ("calendar", "sheets"):
            for phase, model, verb, value in boundaries:
                for position in ("before", "after"):
                    with self.subTest(mode=mode, phase=phase, position=position), ExitStack() as stack:
                        self._fresh_dispatch_target()
                        job, args = self._accepted(mode)
                        sends, _ = self._sends(stack)
                        injected = []
                        executed = []

                        def fail_statement(execute, sql, params, many, context):
                            statement = sql.upper()
                            matches = statement.startswith(
                                f'{verb} {"INTO " if verb == "INSERT" else ""}"{model._meta.db_table.upper()}"'
                            )
                            if phase == "unlock":
                                matches = matches and (
                                    '"ACTIVE_EXECUTION_TOKEN" = NULL' in statement or params[0] is None
                                )
                            elif value is not None:
                                matches = matches and value in params
                            if injected or not matches:
                                return execute(sql, params, many, context)
                            self.assertFalse(many)
                            self.assertTrue(connection.in_atomic_block)
                            injected.append(phase)
                            if position == "after":
                                execute(sql, params, many, context)
                                executed.append(phase)
                            # PostgreSQL itself aborts the real transaction. Do
                            # not substitute an ORM-raised synthetic exception.
                            return execute("SELECT 1 / 0", (), False, context)

                        with connection.execute_wrapper(fail_statement):
                            with self.assertRaises(DatabaseError) as raised:
                                self._worker(mode).run(*args)
                        cause = raised.exception.__cause__
                        self.assertEqual(getattr(cause, "sqlstate", getattr(cause, "pgcode", None)), "22012")
                        self.assertEqual(injected, [phase])
                        self.assertEqual(executed, [phase] if position == "after" else [])
                        write = sends["post" if mode == "calendar" else "put"]
                        self.assertEqual(write.call_count, 0 if phase == "intent" else 1)
                        job.refresh_from_db()
                        self.assertEqual(job.status, AsyncJob.Status.RUNNING)
                        self.assertGreater(job.execution_deadline, timezone.now())
                        self.assertEqual(job.error, "")
                        execution = GoogleWriteExecution.objects.get(job_id_snapshot=job.pk)
                        self.assertEqual(execution.state, GoogleWriteExecution.State.UNKNOWN)
                        self.assertIsNone(execution.closed_at)
                        self.assertTrue(execution.allocations.exists())
                        self.assertFalse(
                            execution.allocations.exclude(target__active_execution_token=execution.pk).exists()
                        )
                        if phase == "intent":
                            self.assertFalse(execution.requests.exists())
                        else:
                            request = execution.requests.get()
                            expected = (
                                GoogleWriteRequest.State.INTENT
                                if phase == "receipt"
                                else GoogleWriteRequest.State.KNOWN
                            )
                            self.assertEqual(request.state, expected)
                            self.assertEqual(request.response_status, None if phase == "receipt" else 200)
                        self._refuse_unchanged(mode, job, args)
                        self._waiting(mode, *self._accepted(mode))
                        self.assertEqual(GoogleWriteExecution.objects.filter(job_id_snapshot=job.pk).count(), 1)
                        print(
                            f"GOOGLE_DB_BOUNDARY mode={mode} phase={phase} position={position} sqlstate=22012 http={write.call_count}"
                        )


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の共有対象実ロック検証")
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleTargetExecutionConcurrencyTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _accepted = GoogleTargetExecutionTest._accepted

    def test_rollback_subcase_helper_rejects_real_commit_tests(self):
        self.assertRaisesRegex(RuntimeError, "TestCase内だけ", rollback_google_subcase().__enter__)

    def test_two_real_calendar_workers_wait_for_same_targets_and_only_one_can_send(self):
        first, first_args = self._accepted("calendar")
        second, second_args = self._accepted("calendar")
        ready = Barrier(3)
        pids = []
        sent = Event()
        release = Event()

        def run(args):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids.append(cursor.fetchone()[0])
                ready.wait(timeout=5)
                return tasks.sync_google_calendar.run(*args)
            finally:
                close_old_connections()

        def applied(url, **kwargs):
            self.assertFalse(connection.in_atomic_block, "HTTP中にDB lockを保持しています。")
            sent.set()
            self.assertTrue(release.wait(8), "独立workerの送信待機が終了しませんでした。")
            return self.response(200, {"id": kwargs["json"]["id"]})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["post"].side_effect = applied
            with ThreadPoolExecutor(max_workers=2) as pool:
                try:
                    with transaction.atomic():
                        list(GoogleWriteTarget.objects.select_for_update().order_by("pk"))
                        futures = [pool.submit(run, args) for args in (first_args, second_args)]
                        ready.wait(timeout=5)
                        deadline = monotonic() + 5
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT pg_backend_pid()")
                            blocker = cursor.fetchone()[0]
                            while True:
                                # Activity's cached query text can still be the
                                # initial PID read while wait events are live.
                                cursor.execute("SELECT pg_stat_clear_snapshot()")
                                cursor.execute(
                                    "SELECT pid,pg_blocking_pids(pid),query LIKE '%%schedules_googlewritetarget%%' FROM pg_stat_activity WHERE pid=ANY(%s) AND wait_event_type='Lock'",
                                    [pids],
                                )
                                observed = cursor.fetchall()
                                # Tuple-lock waiters can form A -> main, B -> A.
                                # Verify both are querying targets and every
                                # wait chain reaches the held main transaction.
                                rooted = {blocker}
                                for _ in range(2):
                                    rooted.update(row[0] for row in observed if any(pid in rooted for pid in row[1]))
                                if len(observed) == 2 and all(row[2] and row[0] in rooted for row in observed):
                                    print(f"GOOGLE_EXECUTION_TARGET_LOCK worker_pids={pids} blocker={blocker}")
                                    break
                                self.assertLess(
                                    monotonic(),
                                    deadline,
                                    f"両workerの実PG lock待機を観測できませんでした。workers={observed}, blocker={blocker}",
                                )
                                sleep(0.02)
                    self.assertTrue(sent.wait(5))
                    done, pending = wait(futures, timeout=5, return_when=FIRST_COMPLETED)
                    self.assertEqual(len(done), 1)
                    self.assertEqual(next(iter(done)).result(), "target-waiting")
                    self.assertEqual(len(pending), 1)
                    self.assertEqual(
                        GoogleWriteExecution.objects.filter(state=GoogleWriteExecution.State.ACTIVE).count(), 1
                    )
                    self.assertEqual(AsyncJob.objects.filter(status=AsyncJob.Status.RUNNING).count(), 1)
                    second.refresh_from_db()
                    self.assertEqual(second.status, AsyncJob.Status.QUEUED)
                    self.assertTrue(second.google_dispatch.ciphertext)
                    sends["post"].assert_called_once()
                finally:
                    release.set()
                self.assertCountEqual([future.result(timeout=8) for future in futures], ["synced", "target-waiting"])

    def test_intent_commit_is_visible_to_independent_connection_before_send(self):
        job, args = self._accepted("sheets")

        def inspect():
            close_old_connections()
            try:
                request = GoogleWriteRequest.objects.get()
                return request.state, request.execution.state, request.execution.job_id_snapshot
            finally:
                close_old_connections()

        def applied(url, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            with ThreadPoolExecutor(max_workers=1) as pool:
                observed = pool.submit(inspect).result(timeout=5)
            self.assertEqual(observed, (GoogleWriteRequest.State.INTENT, GoogleWriteExecution.State.ACTIVE, job.pk))
            return self.response(200, {"updatedCells": 17})

        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            sends["put"].side_effect = applied
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
