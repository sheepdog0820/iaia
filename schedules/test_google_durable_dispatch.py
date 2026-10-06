import base64
import json
import secrets
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack
from datetime import timedelta
from importlib import import_module
from io import StringIO
from threading import Barrier, Event
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from schedules import google_dispatch_outbox as outbox
from schedules import tasks
from schedules import test_google_sheets_content_binding as content_tests
from schedules.google_job_lifecycle import claim_google_job_start
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleJobDispatch
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleDurableDispatchTest(GoogleDispatchStateFixtures, TransactionTestCase):
    _character = content_tests.GoogleSheetsContentBindingTest._character

    def _intent(self, mode="sheets"):
        job, args = self._queue(mode)
        return job, args, outbox.persist_google_dispatch(job, list(args))

    def _due(self, row):
        GoogleJobDispatch.objects.filter(pk=row.pk).update(next_attempt_at=timezone.now() - timedelta(seconds=1))

    def test_ciphertext_binds_job_owner_type_payload_and_preserves_exact_sheet_values(self):
        self._character("暗号化する非公開のキャラクター名フィクスチャ")
        job, args, row = self._intent()
        self.assertEqual(outbox.open_google_dispatch(row), list(args))
        self.assertTrue(row.ciphertext.startswith("v1."))
        self.assertNotIn("暗号化する非公開のキャラクター名フィクスチャ", row.ciphertext)
        self.assertNotIn("Characters!A1", row.ciphertext)
        self.assertNotIn("isolated-content-sheet", row.ciphertext)
        self.assertNotIn("isolated-token", repr(row))
        other_job, _, other = self._intent()
        other.ciphertext = row.ciphertext
        with self.assertRaises(outbox.InvalidGoogleDispatch):
            outbox.open_google_dispatch(other)
        self.assertNotEqual(job.pk, other_job.pk)
        for change in ("owner_id_snapshot", "job_type_snapshot", "payload_digest", "job_created_at"):
            with self.subTest(change=change):
                row.refresh_from_db()
                setattr(
                    row,
                    change,
                    {
                        "owner_id_snapshot": self.other.pk,
                        "job_type_snapshot": "different",
                        "payload_digest": "0" * 64,
                        "job_created_at": timezone.now() + timedelta(days=1),
                    }[change],
                )
                with self.assertRaises(outbox.InvalidGoogleDispatch):
                    outbox.open_google_dispatch(row)
        row.refresh_from_db()
        with override_settings(SECRET_KEY=secrets.token_urlsafe(32)):
            with self.assertRaises(outbox.InvalidGoogleDispatch):
                outbox.open_google_dispatch(row)

    def test_all_producers_commit_job_and_intent_together_when_callback_is_lost(self):
        for route in self.routes:
            with self.subTest(route=route), patch("django.db.transaction.on_commit") as callback:
                response = self._dispatch(route)
                job = AsyncJob.objects.first()
                row = GoogleJobDispatch.objects.get(job=job)
                self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)
                self.assertEqual(row.attempt_count, 0)
                self.assertEqual(job.status, AsyncJob.Status.QUEUED)
                self.assertTrue(outbox.open_google_dispatch(row))
                callback.assert_called_once()
                if response is not None:
                    self.assertIs(response.data["queued"], False)

    def test_intent_persistence_failure_rolls_back_all_producers_before_publish(self):
        for route in self.routes:
            with self.subTest(route=route), ExitStack() as stack:
                before = list(AsyncJob.objects.values())
                rows_before = list(GoogleJobDispatch.objects.values())
                stack.enter_context(
                    patch.object(outbox, "persist_google_dispatch", side_effect=RuntimeError("fixture"))
                )
                publisher = stack.enter_context(patch.object(tasks, "_publish_google_calendar_sync"))
                sheets = stack.enter_context(patch.object(tasks, "_publish_google_sheet_export"))
                if route == "session":
                    with self.assertRaises(RuntimeError):
                        self._dispatch(route)
                else:
                    response = (
                        self.api.post(
                            (
                                f"/api/sessions/{self.session.pk}/google-calendar/sync/"
                                if route == "calendar"
                                else "/api/character-sheets/google-sheets/export/"
                            ),
                            {"spreadsheet_id": "isolated-durable-sheet"},
                            format="json",
                        )
                        if not route.startswith("retry-")
                        else None
                    )
                    if response is None:
                        original, _ = self._queue(self._mode(route))
                        original.mark_failed("元の失敗")
                        before = list(AsyncJob.objects.values())
                        response = self.api.post(f"/api/jobs/{original.pk}/retry/")
                    self.assertEqual(response.status_code, 500)
                self.assertEqual(list(AsyncJob.objects.values()), before)
                self.assertEqual(list(GoogleJobDispatch.objects.values()), rows_before)
                publisher.assert_not_called()
                sheets.assert_not_called()

    def test_rollback_discards_both_intent_and_delivery_on_all_routes(self):
        for route in self.routes:
            with (
                self.subTest(route=route),
                patch.object(tasks, "_publish_google_calendar_sync") as cal,
                patch.object(tasks, "_publish_google_sheet_export") as sheets,
            ):
                before = list(AsyncJob.objects.values())
                rows_before = list(GoogleJobDispatch.objects.values())
                with transaction.atomic():
                    self._dispatch(route)
                    transaction.set_rollback(True)
                self.assertEqual(list(AsyncJob.objects.values()), before)
                self.assertEqual(list(GoogleJobDispatch.objects.values()), rows_before)
                cal.assert_not_called()
                sheets.assert_not_called()

    def test_publish_failure_retries_same_job_without_failed_or_new_job(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args, row = self._intent(mode)
                before = AsyncJob.objects.filter(pk=job.pk).values().get()
                target = "_publish_google_calendar_sync" if mode == "calendar" else "_publish_google_sheet_export"
                with patch.object(tasks, target, return_value=False) as publish:
                    self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                    publish.assert_called_once_with(*args)
                row.refresh_from_db()
                self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)
                self.assertEqual(row.attempt_count, 1)
                self.assertGreater(row.next_attempt_at, timezone.now())
                self.assertTrue(row.ciphertext)
                self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                self._due(row)
                with patch.object(tasks, target, return_value=True) as publish:
                    self.assertTrue(outbox.dispatch_google_job(str(job.pk)))
                    publish.assert_called_once_with(*args)
                row.refresh_from_db()
                self.assertEqual(row.attempt_count, 2)
                self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)
                self.assertIsNotNone(row.published_at)
                self.assertTrue(row.ciphertext)

    def test_accepted_but_unconsumed_message_remains_recoverable_after_broker_loss(self):
        job, args, row = self._intent()
        with patch.object(tasks, "_publish_google_sheet_export", return_value=True) as publish:
            self.assertTrue(outbox.dispatch_google_job(str(job.pk)))
            self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
            self.assertEqual(publish.call_count, 1)
            self._due(row)
            self.assertTrue(outbox.dispatch_google_job(str(job.pk)))
            self.assertEqual(publish.call_args.args, args)
            self.assertEqual(publish.call_count, 2)
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).count(), 1)
        self.assertTrue(claim_google_job_start(job))
        row.refresh_from_db()
        self.assertEqual(row.state, GoogleJobDispatch.State.DELIVERED)
        self.assertEqual(row.ciphertext, "")
        self.assertIsNone(row.claim_token)
        self.assertIsNone(row.claim_until)
        self._due(row)
        with patch.object(tasks, "_publish_google_sheet_export") as publish:
            self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
            publish.assert_not_called()

    def test_expired_relay_claim_is_recovered_but_live_claim_cannot_be_taken_twice(self):
        job, args, row = self._intent()
        with patch.object(tasks, "_publish_google_sheet_export", return_value=True) as publish:

            def abandoned(*unused):
                raise SystemExit("synthetic relay death")

            publish.side_effect = abandoned
            with self.assertRaises(SystemExit):
                outbox.dispatch_google_job(str(job.pk))
            row.refresh_from_db()
            self.assertEqual(row.state, GoogleJobDispatch.State.CLAIMED)
            token = row.claim_token
            self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
            self.assertEqual(publish.call_count, 1)
            GoogleJobDispatch.objects.filter(pk=row.pk).update(claim_until=timezone.now() - timedelta(seconds=1))
            publish.side_effect = None
            self.assertTrue(outbox.dispatch_google_job(str(job.pk)))
            self.assertEqual(publish.call_args.args, args)
            row.refresh_from_db()
            self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)
            self.assertIsNone(row.claim_token)
            self.assertIsNotNone(token)

    def test_running_completed_uncertain_failed_expired_and_changed_jobs_never_relay(self):
        for mode in ("calendar", "sheets"):
            for change in (
                "running",
                "succeeded",
                "uncertain",
                "failed",
                "expired",
                "owner",
                "type",
                "payload",
                "started",
            ):
                with self.subTest(mode=mode, change=change):
                    job, _, row = self._intent(mode)
                    update = {
                        "expired": {"expires_at": timezone.now() - timedelta(seconds=1)},
                        "owner": {"owner_id": self.other.pk},
                        "type": {"job_type": "unknown"},
                        "payload": {"payload": {"changed": True}},
                        "started": {"started_at": timezone.now()},
                    }.get(change, {"status": change})
                    AsyncJob.objects.filter(pk=job.pk).update(**update)
                    before = AsyncJob.objects.filter(pk=job.pk).values().get()
                    with (
                        patch.object(tasks, "_publish_google_calendar_sync") as cal,
                        patch.object(tasks, "_publish_google_sheet_export") as sheets,
                    ):
                        self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                        cal.assert_not_called()
                        sheets.assert_not_called()
                    self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
                    row.refresh_from_db()
                    self.assertEqual(row.state, GoogleJobDispatch.State.DISCARDED)
                    self.assertEqual(row.ciphertext, "")

    def test_corrupt_or_changed_key_envelope_fails_closed_with_safe_japanese_error(self):
        for ciphertext in ("", "v0.bad", "v1.not-base64!", "v1.AAAA"):
            with self.subTest(ciphertext=ciphertext):
                job, _, row = self._intent()
                GoogleJobDispatch.objects.filter(pk=row.pk).update(ciphertext=ciphertext)
                with patch.object(tasks, "_publish_google_sheet_export") as publish:
                    self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                    publish.assert_not_called()
                job.refresh_from_db()
                row.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.FAILED)
                self.assertEqual(job.error, outbox.INVALID_DISPATCH_MESSAGE)
                self.assertEqual(row.state, GoogleJobDispatch.State.FAILED)
                self.assertEqual(row.ciphertext, "")

    def test_worker_receipt_during_lost_publish_response_is_not_reset_by_relay(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode), ExitStack() as stack:
                job, args, row = self._intent(mode)
                sends, _ = self._sends(stack)
                target = "_publish_google_calendar_sync" if mode == "calendar" else "_publish_google_sheet_export"

                def publish(*received):
                    self.assertEqual(received, args)
                    self.assertEqual(self._worker(mode).run(*received), "exported" if mode == "sheets" else "synced")
                    return False

                stack.enter_context(patch.object(tasks, target, side_effect=publish))
                self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                self.assertEqual(sum(send.call_count for send in sends.values()), 1)
                row.refresh_from_db()
                self.assertEqual(row.state, GoogleJobDispatch.State.DELIVERED)
                self.assertEqual(row.ciphertext, "")
                self.assertIsNone(row.claim_token)
                job.refresh_from_db()
                self.assertEqual(job.status, AsyncJob.Status.SUCCEEDED)

    def test_deleted_job_cascades_envelope_and_never_recreates_or_sends(self):
        job, _, row = self._intent()
        job_id = str(job.pk)
        job.delete()
        self.assertFalse(GoogleJobDispatch.objects.filter(pk=row.pk).exists())
        with patch.object(tasks, "_publish_google_sheet_export") as publish:
            self.assertFalse(outbox.dispatch_google_job(job_id))
            publish.assert_not_called()

    def test_bounded_relay_batch_and_bad_limits_or_job_ids_do_not_dispatch(self):
        for bad in (None, True, 0, -1, 1001, "1"):
            with self.subTest(limit=bad):
                with self.assertRaises(ValueError):
                    outbox.dispatch_google_jobs(limit=bad)
        for bad in (None, True, [], {}, "private", "\ud800"):
            with self.subTest(job_id=repr(bad)), self.assertNumQueries(0):
                self.assertFalse(outbox.dispatch_google_job(bad))
                self.assertFalse(tasks.queue_google_calendar_sync(self.sync.pk, bad))
        for unused in range(3):
            self._intent()
        with patch.object(tasks, "_publish_google_sheet_export", return_value=True) as publish:
            self.assertEqual(outbox.dispatch_google_jobs(limit=2), {"attempted": 2, "published": 2})
            self.assertEqual(publish.call_count, 2)
            self.assertEqual(outbox.dispatch_google_jobs(limit=2), {"attempted": 1, "published": 1})

    def test_claim_or_job_change_while_opening_envelope_suppresses_publication(self):
        for change in ("token", "deadline", "deleted", "job-running", "job-payload"):
            with self.subTest(change=change):
                job, _, row = self._intent()
                original = outbox.open_google_dispatch

                def changed(claim):
                    args = original(claim)
                    if change == "token":
                        import uuid

                        GoogleJobDispatch.objects.filter(pk=row.pk).update(claim_token=uuid.uuid4())
                    elif change == "deadline":
                        GoogleJobDispatch.objects.filter(pk=row.pk).update(
                            claim_until=timezone.now() - timedelta(seconds=1)
                        )
                    elif change == "deleted":
                        job.delete()
                    else:
                        AsyncJob.objects.filter(pk=job.pk).update(
                            **(
                                {"status": AsyncJob.Status.RUNNING}
                                if change == "job-running"
                                else {"payload": {"changed": True}}
                            )
                        )
                    return args

                with (
                    patch.object(outbox, "open_google_dispatch", side_effect=changed),
                    patch.object(tasks, "_publish_google_sheet_export") as publish,
                ):
                    self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                    publish.assert_not_called()

    def test_repeated_registration_does_not_change_ciphertext_or_resurrect_worker_receipt(self):
        job, args, row = self._intent()
        first_cipher = row.ciphertext
        self.assertEqual(outbox.persist_google_dispatch(job, list(args)).pk, row.pk)
        row.refresh_from_db()
        self.assertEqual(row.ciphertext, first_cipher)
        self.assertTrue(claim_google_job_start(job))
        self.assertEqual(outbox.persist_google_dispatch(job, list(args)).pk, row.pk)
        row.refresh_from_db()
        self.assertEqual(row.state, GoogleJobDispatch.State.DELIVERED)
        self.assertEqual(row.ciphertext, "")

    def test_old_application_raw_job_delete_cascades_encrypted_intent(self):
        job, _, row = self._intent()
        identity = str(job.pk) if connection.vendor == "postgresql" else job.pk.hex
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM schedules_asyncjob WHERE id = %s", [identity])
        self.assertFalse(GoogleJobDispatch.objects.filter(pk=row.pk).exists())

    def test_task_command_and_beat_use_bounded_relay_with_japanese_diagnostics(self):
        from django.conf import settings

        output = StringIO()
        with patch.object(outbox, "dispatch_google_jobs", return_value={"attempted": 2, "published": 1}) as relay:
            self.assertEqual(tasks.dispatch_google_jobs.run(), {"attempted": 2, "published": 1})
            relay.assert_called_once_with()
        call_command("dispatch_google_jobs", limit=1, stdout=output)
        self.assertIn("対象 0 件、投入確認 0 件", output.getvalue())
        with self.assertRaisesMessage(CommandError, "配送件数は1〜1000の整数で指定してください。"):
            call_command("dispatch_google_jobs", limit=0)
        self.assertEqual(
            settings.CELERY_BEAT_SCHEDULE["dispatch-google-jobs"],
            {"task": "schedules.tasks.dispatch_google_jobs", "schedule": 60.0},
        )

    def test_migration_reverse_forward_preserves_job_and_removes_old_sqlite_trigger(self):
        job, _, row = self._intent()
        original_job = AsyncJob.objects.filter(pk=job.pk).values().get()
        try:
            MigrationExecutor(connection).migrate([("schedules", "0056_asyncjob_execution_outcome")])
            self.assertNotIn("schedules_googlejobdispatch", connection.introspection.table_names())
            self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), original_job)
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM schedules_asyncjob WHERE id = %s",
                    [str(job.pk) if connection.vendor == "postgresql" else job.pk.hex],
                )
        finally:
            MigrationExecutor(connection).migrate([("schedules", "0058_google_dispatch_delete_cascade")])
        self.assertIn("schedules_googlejobdispatch", connection.introspection.table_names())
        self.assertFalse(GoogleJobDispatch.objects.filter(pk=row.pk).exists())

    def test_migration_rejects_unsupported_backend_or_unexpected_fk_before_changing_constraints(self):
        migration = import_module("schedules.migrations.0058_google_dispatch_delete_cascade")
        with self.assertRaisesMessage(RuntimeError, "Google配送はSQLiteまたはPostgreSQLのDBを使用してください。"):
            migration.install_delete_cascade(None, SimpleNamespace(connection=SimpleNamespace(vendor="unknown")))
        with self.assertRaisesMessage(RuntimeError, "Google配送はSQLiteまたはPostgreSQLのDBを使用してください。"):
            migration.remove_delete_cascade(None, SimpleNamespace(connection=SimpleNamespace(vendor="unknown")))
        with patch("django.db.connection.cursor"):
            fake = SimpleNamespace(
                connection=SimpleNamespace(
                    vendor="postgresql",
                    cursor=connection.cursor,
                    introspection=SimpleNamespace(get_constraints=lambda *a: {}),
                )
            )
            with self.assertRaisesMessage(RuntimeError, "Google配送の参照制約を確認できません。"):
                migration.install_delete_cascade(None, fake)
        fake = SimpleNamespace(
            connection=SimpleNamespace(
                vendor="postgresql",
                cursor=connection.cursor,
                introspection=SimpleNamespace(
                    get_constraints=lambda *a: {
                        "fixture_job_fk": {"foreign_key": ("schedules_asyncjob", "id"), "columns": ["job_id"]}
                    }
                ),
            ),
            quote_name=connection.ops.quote_name,
            execute=Mock(),
        )
        migration.install_delete_cascade(None, fake)
        self.assertEqual(fake.execute.call_count, 2)
        self.assertIn("ON DELETE CASCADE", fake.execute.call_args.args[0])
        self.assertIn("DEFERRABLE INITIALLY DEFERRED", fake.execute.call_args.args[0])
        fake.execute.reset_mock()
        migration.remove_delete_cascade(None, fake)
        self.assertEqual(fake.execute.call_count, 2)
        self.assertNotIn("ON DELETE CASCADE", fake.execute.call_args.args[0])

    @skipUnless(connection.vendor == "postgresql", "PostgreSQL独立relayの同時claim検証")
    def test_independent_relays_publish_only_one_live_claim(self):
        for mode in ("calendar", "sheets"):
            with self.subTest(mode=mode):
                job, args, row = self._intent(mode)
                start, reached, release = Barrier(2), Event(), Event()
                target = "_publish_google_calendar_sync" if mode == "calendar" else "_publish_google_sheet_export"

                def publish(*received):
                    self.assertEqual(received, args)
                    reached.set()
                    self.assertTrue(release.wait(timeout=10))
                    return True

                def run():
                    close_old_connections()
                    try:
                        start.wait(timeout=5)
                        return outbox.dispatch_google_job(str(job.pk))
                    finally:
                        close_old_connections()

                with (
                    patch.object(tasks, target, side_effect=publish) as publisher,
                    ThreadPoolExecutor(max_workers=2) as pool,
                ):
                    futures = [pool.submit(run) for unused in range(2)]
                    try:
                        self.assertTrue(reached.wait(timeout=5))
                        completed, _ = wait(futures, timeout=5, return_when=FIRST_COMPLETED)
                        self.assertEqual(len(completed), 1)
                        self.assertFalse(next(iter(completed)).result())
                        self.assertEqual(publisher.call_count, 1)
                    finally:
                        release.set()
                    self.assertEqual(sorted(future.result(timeout=10) for future in futures), [False, True])
                row.refresh_from_db()
                self.assertEqual(row.attempt_count, 1)
                self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)

    def _sealed_for(self, row, value):
        nonce = secrets.token_bytes(12)
        return "v1." + base64.b64encode(
            nonce + outbox._cipher().encrypt(nonce, json.dumps(value).encode("utf-8"), outbox._aad(row))
        ).decode("ascii")

    def test_invalid_saved_args_and_bad_registration_cannot_publish_or_change_another_job(self):
        for mode in ("calendar", "sheets"):
            for saved in ([], {}, None, ["wrong-private-job"]):
                with self.subTest(mode=mode, saved=repr(saved)):
                    job, _, row = self._intent(mode)
                    GoogleJobDispatch.objects.filter(pk=row.pk).update(ciphertext=self._sealed_for(row, saved))
                    with (
                        patch.object(tasks, "_publish_google_calendar_sync") as cal,
                        patch.object(tasks, "_publish_google_sheet_export") as sheets,
                    ):
                        self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
                        cal.assert_not_called()
                        sheets.assert_not_called()
                    job.refresh_from_db()
                    self.assertEqual(job.error, outbox.INVALID_DISPATCH_MESSAGE)
        job, args, row = self._intent()
        for invalid in (None, {}, [], ["another-job", *args[1:]]):
            with self.subTest(invalid=repr(invalid)), self.assertRaises(outbox.InvalidGoogleDispatch):
                outbox.persist_google_dispatch(job, invalid)
        job.job_type = "unknown"
        with self.assertRaises(outbox.InvalidGoogleDispatch):
            outbox.persist_google_dispatch(job, list(args))
        row.refresh_from_db()
        self.assertTrue(row.ciphertext)

    def test_repeated_registration_rejects_changed_snapshots_or_authenticated_different_args(self):
        job, args, row = self._intent()
        GoogleJobDispatch.objects.filter(pk=row.pk).update(owner_id_snapshot=self.other.pk)
        with self.assertRaises(outbox.InvalidGoogleDispatch):
            outbox.persist_google_dispatch(job, list(args))
        GoogleJobDispatch.objects.filter(pk=row.pk).update(owner_id_snapshot=job.owner_id)
        row.refresh_from_db()
        GoogleJobDispatch.objects.filter(pk=row.pk).update(ciphertext=self._sealed_for(row, ["changed-private-data"]))
        with self.assertRaises(outbox.InvalidGoogleDispatch):
            outbox.persist_google_dispatch(job, list(args))

    def test_unexpected_publish_exception_has_safe_log_and_retains_retry(self):
        job, _, row = self._intent()
        with patch.object(tasks, "_publish_google_sheet_export", side_effect=RuntimeError("private-cell-value")):
            with self.assertLogs("schedules.google_dispatch_outbox", level="WARNING") as logs:
                self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
        self.assertNotIn("private-cell-value", " ".join(logs.output))
        row.refresh_from_db()
        self.assertEqual(row.state, GoogleJobDispatch.State.PENDING)
        self.assertTrue(row.ciphertext)

    def test_claim_without_deadline_can_be_recovered_without_sending_started_job(self):
        job, args, row = self._intent()
        GoogleJobDispatch.objects.filter(pk=row.pk).update(state=GoogleJobDispatch.State.CLAIMED, claim_until=None)
        with patch.object(tasks, "_publish_google_sheet_export", return_value=True) as publish:
            self.assertTrue(outbox.dispatch_google_job(str(job.pk)))
            publish.assert_called_once_with(*args)

    def test_batch_recovers_claim_without_deadline(self):
        job, args, row = self._intent()
        GoogleJobDispatch.objects.filter(pk=row.pk).update(state=GoogleJobDispatch.State.CLAIMED, claim_until=None)
        with patch.object(tasks, "_publish_google_sheet_export", return_value=True) as publish:
            self.assertEqual(outbox.dispatch_google_jobs(), {"attempted": 1, "published": 1})
            publish.assert_called_once_with(*args)

    def test_deleted_calendar_target_discards_intent_before_publish(self):
        job, _, row = self._intent("calendar")
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        GoogleCalendarSync.objects.filter(pk=job.payload["sync_id"]).delete()
        with patch.object(tasks, "_publish_google_calendar_sync") as publish:
            self.assertFalse(outbox.dispatch_google_job(str(job.pk)))
            publish.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.state, GoogleJobDispatch.State.DISCARDED)
        self.assertEqual(row.ciphertext, "")
        self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
