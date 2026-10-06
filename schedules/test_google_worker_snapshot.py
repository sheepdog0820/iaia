"""Workers must use authenticated admission content, never reconstruct missing intent."""

import base64
import os
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from accounts.character_models import CharacterSheet7th
from accounts.models import CharacterSheet
from schedules import google_write_ledger as ledger
from schedules import tasks
from schedules.google_job_lifecycle import GOOGLE_EXECUTION_UNCERTAIN_MESSAGE
from schedules.google_tokens import google_credential_identity
from schedules.google_worker_snapshot import read_worker_snapshot
from schedules.google_write_ledger import (
    INVALID_ADMISSION_MESSAGE,
    InvalidGoogleWriteAdmission,
    open_google_write_snapshot,
    register_google_write,
)
from schedules.models import AsyncJob, GoogleCalendarSync, GoogleWriteAdmission
from schedules.test_google_dispatch_state import GoogleDispatchStateFixtures


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class GoogleWorkerSnapshotTest(GoogleDispatchStateFixtures, TransactionTestCase):
    def _accepted(self, mode):
        job, args = self._queue(mode)
        return job, args, open_google_write_snapshot(job.google_write_admission)

    def _replace_snapshot(self, job, snapshot):
        row = job.google_write_admission
        keys = list(row.reservations.values_list("target_id", flat=True))
        row.delete()
        return register_google_write(job, keys, snapshot)

    def _reseal_existing_row(self, job, snapshot):
        # Deliberately synthesize a correctly authenticated but replaced intent.
        # Crypto authenticity alone must not replace the worker's frozen copy.
        row = GoogleWriteAdmission.objects.get(job_id=job.pk)
        row.snapshot_binding = ledger._snapshot_binding(snapshot)
        nonce = os.urandom(12)
        row.ciphertext = "v1." + base64.b64encode(
            nonce + ledger._cipher().encrypt(nonce, ledger._json(snapshot), ledger._aad(row))
        ).decode("ascii")
        row.save(update_fields=["snapshot_binding", "ciphertext"])

    def test_authenticated_replacement_during_get_cannot_replace_the_fixed_worker_body(self):
        for mode in ("update", "cancel", "conflict"):
            with self.subTest(mode=mode):
                self.sync.external_event_id = "known-private-event" if mode in ("update", "cancel") else ""
                self.sync.save(update_fields=["external_event_id"])
                self.session.status = "cancelled" if mode == "cancel" else "planned"
                self.session.save(update_fields=["status"])
                job, args, snapshot = self._accepted("calendar")

                def fetch(url, **kwargs):
                    response = self.event_response(url, **kwargs)
                    changed = deepcopy(snapshot)
                    if mode == "cancel":
                        changed["calendar"]["operation"] = "upsert"
                    else:
                        changed["calendar"]["event"]["summary"] = "認証済みだが差し替えられた非公開本文"
                    self._reseal_existing_row(job, changed)
                    return response

                with ExitStack() as stack:
                    sends, _ = self._sends(stack)
                    sends["get"].side_effect = fetch
                    if mode == "conflict":
                        sends["post"].return_value = self.response(409, {})
                    self.assertEqual(tasks.sync_google_calendar.run(*args), "inactive-job")
                    sends["get"].assert_called_once()
                    sends["put"].assert_not_called()
                    sends["delete"].assert_not_called()
                job.refresh_from_db()
                self.assertEqual((job.status, job.error), (AsyncJob.Status.FAILED, INVALID_ADMISSION_MESSAGE))

    def test_missing_running_cache_is_not_reconstructed_from_the_database(self):
        from schedules.google_job_lifecycle import GoogleJobInactive, claim_google_job_start
        from schedules.google_worker_snapshot import require_worker_snapshot

        job, _, _ = self._accepted("sheets")
        self.assertTrue(claim_google_job_start(job))
        with self.assertRaises(GoogleJobInactive):
            require_worker_snapshot(job)
        job.refresh_from_db()
        self.assertEqual((job.status, job.error), (AsyncJob.Status.FAILED, INVALID_ADMISSION_MESSAGE))

    def test_snapshot_shape_and_target_allocations_are_checked_even_when_authenticated(self):
        changes = (
            ("calendar", lambda snapshot: snapshot.update(extra_private=True)),
            ("calendar", lambda snapshot: snapshot.update(kind="google_sheets_export")),
            ("calendar", lambda snapshot: snapshot.update(google_connection="different-private-binding")),
            ("calendar", lambda snapshot: snapshot.update(sync=None)),
            ("calendar", lambda snapshot: snapshot.update(calendar=None)),
            ("calendar", lambda snapshot: snapshot["calendar"].update(calendar_id="not-primary")),
            ("calendar", lambda snapshot: snapshot["calendar"].update(known_event=1)),
            ("calendar", lambda snapshot: snapshot["calendar"].update(operation="unknown")),
            ("calendar", lambda snapshot: snapshot["calendar"].update(operation="cancel")),
            ("calendar", lambda snapshot: snapshot["calendar"].update(event=[])),
            ("calendar", lambda snapshot: snapshot["calendar"]["event"].update(status="cancelled")),
            ("calendar", lambda snapshot: snapshot["calendar"]["event"].update(extendedProperties={})),
            ("sheets", lambda snapshot: snapshot.update(sheets=None)),
            ("sheets", lambda snapshot: snapshot["sheets"].update(range="Different!B2")),
            ("sheets", lambda snapshot: snapshot["sheets"].update(values=[["private-injected-cell"]])),
        )
        for index, (mode, change) in enumerate(changes):
            with self.subTest(change=index):
                job, args, snapshot = self._accepted(mode)
                change(snapshot)
                self._replace_snapshot(job, snapshot)
                with ExitStack() as stack:
                    sends, token = self._sends(stack)
                    self.assertEqual(self._worker(mode).run(*args), "invalid-admission")
                    token.assert_not_called()
                    for send in sends.values():
                        send.assert_not_called()
        job, _, snapshot = self._accepted("sheets")
        job.google_write_admission.delete()
        register_google_write(job, [ledger.sheet_target_key("another-private-sheet")], snapshot)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            read_worker_snapshot(job, snapshot["credential"])
        job, _, snapshot = self._accepted("calendar")
        with self.assertRaises(InvalidGoogleWriteAdmission):
            read_worker_snapshot(job, snapshot["credential"])

    def test_credential_identity_rejects_bool_and_secret_fields_but_allows_real_app_id(self):
        from allauth.socialaccount.models import SocialApp, SocialToken

        app = SocialApp.objects.create(provider="google", name="Synthetic snapshot app", client_id="fixture")
        SocialToken.objects.filter(account__user=self.user).update(app=app)
        job, _, snapshot = self._accepted("sheets")
        self.assertEqual(read_worker_snapshot(job, snapshot["credential"]), snapshot)
        for field, value in (
            ("pk", True),
            ("account_id", 0),
            ("app_id", False),
            ("account__uid", ""),
            ("token", "fixture"),
        ):
            with self.subTest(field=field):
                credential = {**snapshot["credential"], field: value}
                with self.assertRaises(InvalidGoogleWriteAdmission):
                    read_worker_snapshot(job, credential)

    def test_prior_deterministic_id_receipt_does_not_change_the_accepted_create_intent(self):
        job, args, snapshot = self._accepted("calendar")
        GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(external_event_id=snapshot["calendar"]["event_id"])
        self.session.date = None
        self.session.save(update_fields=["date"])
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "synced")
            sends["post"].assert_called_once()
            sends["put"].assert_not_called()
        self.assertEqual(sends["post"].call_args.kwargs["json"]["summary"], snapshot["calendar"]["event"]["summary"])

    def test_authenticated_calendar_body_with_extra_fields_or_invalid_types_is_refused(self):
        changes = (
            lambda event: event.update(attendees=[{"email": "private-injected@example.invalid"}]),
            lambda event: event.pop("summary"),
            lambda event: event.update(summary=True),
            lambda event: event.update(description=[]),
            lambda event: event.update(location=None),
            lambda event: event.update(start={"date": "2026-10-07"}),
            lambda event: event.update(end={"dateTime": "invalid-private-datetime"}),
            lambda event: event.update(start={"dateTime": 123}),
            lambda event: event["start"].update(timeZone="unaccepted-zone"),
        )
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                job, args, snapshot = self._accepted("calendar")
                change(snapshot["calendar"]["event"])
                self._replace_snapshot(job, snapshot)
                with ExitStack() as stack:
                    sends, token = self._sends(stack)
                    self.assertEqual(tasks.sync_google_calendar.run(*args), "invalid-admission")
                    token.assert_not_called()
                    for send in sends.values():
                        send.assert_not_called()

    def test_missing_or_malformed_credential_cannot_be_an_authenticated_worker_identity(self):
        for mode in ("calendar", "sheets"):
            for credential in (None, {}, [], {"account__uid": "private-identity"}):
                with self.subTest(mode=mode, credential_type=type(credential).__name__):
                    job, _, snapshot = self._accepted(mode)
                    snapshot["credential"] = credential
                    self._replace_snapshot(job, snapshot)
                    with self.assertRaises(InvalidGoogleWriteAdmission):
                        read_worker_snapshot(job, credential, self.sync if mode == "calendar" else None)

    def test_new_calendar_id_must_be_the_deterministic_accepted_sync_key(self):
        job, args, snapshot = self._accepted("calendar")
        snapshot["calendar"]["event_id"] = "different-private-new-event"
        from schedules.google_write_ledger import calendar_event_target_key, calendar_session_target_key

        job.google_write_admission.delete()
        register_google_write(
            job,
            [
                calendar_session_target_key(self.user.pk, self.session.pk),
                calendar_event_target_key(snapshot["credential"]["account__uid"], snapshot["calendar"]["event_id"]),
            ],
            snapshot,
        )
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "invalid-admission")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()

    def test_undated_acceptance_does_not_become_a_new_event_after_date_is_added(self):
        self.session.date = None
        self.session.save(update_fields=["date"])
        job, args, snapshot = self._accepted("calendar")
        self.session.date = timezone.now() + timedelta(days=1)
        self.session.save(update_fields=["date"])
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "undated")
            for send in sends.values():
                send.assert_not_called()
        self.assertIsNone(snapshot["calendar"]["event"])

    def test_known_event_uses_frozen_body_but_checks_the_current_external_id(self):
        for change_id in (False, True):
            with self.subTest(change_id=change_id):
                self.sync.external_event_id = "accepted-private-existing-event"
                self.sync.save(update_fields=["external_event_id"])
                job, args, accepted = self._accepted("calendar")
                self.session.title = "受付後の非公開題名"
                self.session.save(update_fields=["title"])
                if change_id:
                    GoogleCalendarSync.objects.filter(pk=self.sync.pk).update(external_event_id="different-private-id")
                with ExitStack() as stack:
                    sends, token = self._sends(stack)
                    sends["put"].return_value = self.response(200, {"id": accepted["calendar"]["event_id"]})
                    self.assertEqual(
                        tasks.sync_google_calendar.run(*args), "invalid-admission" if change_id else "synced"
                    )
                    if change_id:
                        token.assert_not_called()
                        for send in sends.values():
                            send.assert_not_called()
                    else:
                        self.assertEqual(sends["put"].call_args.kwargs["json"], accepted["calendar"]["event"])
                        sends["post"].assert_not_called()

    def test_admission_change_during_token_lookup_prevents_the_first_http(self):
        for mode in ("calendar", "sheets"):
            for change in ("delete", "cipher", "payload", "allocation"):
                with self.subTest(mode=mode, change=change):
                    job, args, _ = self._accepted(mode)

                    def lookup(*unused):
                        row = GoogleWriteAdmission.objects.get(job_id=job.pk)
                        if change == "delete":
                            row.delete()
                        elif change == "cipher":
                            GoogleWriteAdmission.objects.filter(pk=row.pk).update(ciphertext="v1.invalid")
                        elif change == "payload":
                            AsyncJob.objects.filter(pk=job.pk).update(payload={**job.payload, "private_change": True})
                        else:
                            row.reservations.update(sequence=9999)
                        return "isolated-token"

                    with ExitStack() as stack:
                        sends, token = self._sends(stack)
                        token.side_effect = lookup
                        self.assertEqual(self._worker(mode).run(*args), "inactive-job")
                        for send in sends.values():
                            send.assert_not_called()
                    job.refresh_from_db()
                    self.assertEqual((job.status, job.error), (AsyncJob.Status.FAILED, INVALID_ADMISSION_MESSAGE))

    def test_sheets_chunks_are_frozen_when_original_rows_change_after_first_put(self):
        for index in range(3):
            character = CharacterSheet.objects.create(user=self.user, edition="7th")
            CharacterSheet7th.objects.create(character_sheet=character, name=f"受付時の非公開名{index}")
        job, args, snapshot = self._accepted("sheets")
        received = []

        def put(url, **kwargs):
            received.extend(deepcopy(kwargs["json"]["values"]))
            for row in args[-1][1:]:
                row[1] = "変更された非公開名"
            return self.response(200, {"updatedCells": 0})

        with ExitStack() as stack, patch("schedules.tasks.SHEETS_EXPORT_CHUNK_ROWS", 2):
            sends, _ = self._sends(stack)
            sends["put"].side_effect = put
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
            self.assertEqual(sends["put"].call_count, 2)
        self.assertEqual(received, snapshot["sheets"]["values"])

    def test_admission_loss_after_accepted_sheet_chunk_preserves_uncertainty_not_retryable_failure(self):
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(character_sheet=character, name="途中まで受付済みの非公開名")
        job, args, _ = self._accepted("sheets")

        def put(url, **kwargs):
            GoogleWriteAdmission.objects.filter(job_id=job.pk).delete()
            return self.response(200, {"updatedCells": 1})

        with ExitStack() as stack, patch("schedules.tasks.SHEETS_EXPORT_CHUNK_ROWS", 1):
            sends, _ = self._sends(stack)
            sends["put"].side_effect = put
            self.assertEqual(tasks.export_google_sheet.run(*args), "inactive-job")
            sends["put"].assert_called_once()
        job.refresh_from_db()
        self.assertEqual((job.status, job.error), (AsyncJob.Status.UNCERTAIN, GOOGLE_EXECUTION_UNCERTAIN_MESSAGE))
        from django.urls import reverse

        self.assertEqual(self.api.post(reverse("async-job-retry", kwargs={"pk": job.pk})).status_code, 400)

    def test_wrong_source_instance_is_never_used_to_open_an_admission(self):
        with self.assertRaises(InvalidGoogleWriteAdmission):
            read_worker_snapshot(None, None)
        for change in ("owner", "kind", "created_at", "payload-type"):
            with self.subTest(change=change):
                job, _, _ = self._accepted("calendar")
                credential = google_credential_identity(self.user.pk)
                if change == "owner":
                    job.owner_id = self.other.pk
                elif change == "kind":
                    job.job_type = "google_sheets_export"
                elif change == "created_at":
                    job.created_at += timedelta(seconds=1)
                else:
                    AsyncJob.objects.filter(pk=job.pk).update(payload=[])
                with self.assertRaises(InvalidGoogleWriteAdmission):
                    read_worker_snapshot(job, credential, self.sync)

    def test_calendar_sends_the_accepted_event_after_session_edit_and_cancellation(self):
        job, args, accepted = self._accepted("calendar")
        self.session.title = "後続編集の非公開題名"
        self.session.description = "後続編集の非公開本文"
        self.session.status = "cancelled"
        self.session.date += timedelta(days=2)
        self.session.save(update_fields=["title", "description", "status", "date"])
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "synced")
        self.assertEqual(
            sends["post"].call_args.kwargs["json"],
            {**accepted["calendar"]["event"], "id": accepted["calendar"]["event_id"]},
        )
        sends["delete"].assert_not_called()

    def test_calendar_keeps_an_accepted_cancellation_after_the_session_is_reopened(self):
        self.session.status = "cancelled"
        self.session.save(update_fields=["status"])
        job, args, accepted = self._accepted("calendar")
        self.session.status = "planned"
        self.session.save(update_fields=["status"])
        with ExitStack() as stack:
            sends, _ = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "deleted")
        sends["delete"].assert_called_once()
        sends["post"].assert_not_called()
        sends["put"].assert_not_called()
        self.assertEqual(accepted["calendar"]["operation"], "cancel")

    def test_sheets_uses_frozen_rows_when_the_callers_values_change_during_token_lookup(self):
        character = CharacterSheet.objects.create(user=self.user, edition="7th")
        CharacterSheet7th.objects.create(character_sheet=character, name="受付時の非公開名")
        job, args, accepted = self._accepted("sheets")

        def token_lookup(*unused):
            args[-1][1][1] = "受付後に差し替えた非公開名"
            return "isolated-token"

        with ExitStack() as stack:
            sends, token = self._sends(stack)
            token.side_effect = token_lookup
            self.assertEqual(tasks.export_google_sheet.run(*args), "exported")
        self.assertEqual(sends["put"].call_args.kwargs["json"]["values"], accepted["sheets"]["values"])

    def test_missing_or_tampered_admission_is_rejected_before_token_lookup_or_any_http(self):
        for mode in ("calendar", "sheets"):
            for change in ("missing", "cipher", "allocation", "payload"):
                with self.subTest(mode=mode, change=change):
                    job, args, _ = self._accepted(mode)
                    row = job.google_write_admission
                    if change == "missing":
                        row.delete()
                    elif change == "cipher":
                        GoogleWriteAdmission.objects.filter(pk=row.pk).update(ciphertext="v1.invalid")
                    elif change == "allocation":
                        row.reservations.update(sequence=9999)
                    else:
                        AsyncJob.objects.filter(pk=job.pk).update(payload={**job.payload, "private_changed": True})
                    with ExitStack() as stack:
                        sends, token = self._sends(stack)
                        self.assertEqual(self._worker(mode).run(*args), "invalid-admission")
                        token.assert_not_called()
                        for send in sends.values():
                            send.assert_not_called()
                    job.refresh_from_db()
                    self.assertEqual(job.status, AsyncJob.Status.FAILED)
                    self.assertEqual(job.error, INVALID_ADMISSION_MESSAGE)

    def test_same_pk_replacement_sync_cannot_consume_the_old_admission(self):
        job, args, _ = self._accepted("calendar")
        old_pk = self.sync.pk
        self.sync.delete()
        replacement = GoogleCalendarSync.objects.create(
            pk=old_pk, user=self.user, session=self.session, created_at=timezone.now() + timedelta(seconds=1)
        )
        self.sync = replacement
        before = GoogleCalendarSync.objects.filter(pk=old_pk).values().get()
        with ExitStack() as stack:
            sends, token = self._sends(stack)
            self.assertEqual(tasks.sync_google_calendar.run(*args), "invalid-admission")
            token.assert_not_called()
            for send in sends.values():
                send.assert_not_called()
        self.assertEqual(GoogleCalendarSync.objects.filter(pk=replacement.pk).values().get(), before)

    def test_authenticated_but_wrong_version_or_target_snapshot_is_not_a_permission_grant(self):
        for mode in ("calendar", "sheets"):
            for change in ("version", "target", "credential"):
                with self.subTest(mode=mode, change=change):
                    job, args, snapshot = self._accepted(mode)
                    row = job.google_write_admission
                    keys = list(row.reservations.values_list("target_id", flat=True))
                    row.delete()
                    if change == "version":
                        snapshot["version"] = True
                    elif change == "credential":
                        snapshot["credential"]["account__uid"] = "another-private-google-identity"
                    elif mode == "calendar":
                        snapshot["calendar"]["event_id"] = "another-private-event"
                    else:
                        snapshot["sheets"]["spreadsheet_id"] = "another-private-sheet"
                    register_google_write(job, keys, snapshot)
                    with ExitStack() as stack:
                        sends, token = self._sends(stack)
                        self.assertEqual(self._worker(mode).run(*args), "invalid-admission")
                        token.assert_not_called()
                        for send in sends.values():
                            send.assert_not_called()
