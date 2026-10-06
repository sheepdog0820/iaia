"""Foundation only: immutable admissions are not yet worker execution fences."""

import base64
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from schedules import google_write_ledger as ledger
from schedules.google_write_ledger import (
    InvalidGoogleWriteAdmission,
    calendar_event_target_key,
    calendar_session_target_key,
    open_google_write_snapshot,
    register_google_write,
    sheet_target_key,
)
from schedules.models import AsyncJob, GoogleWriteAdmission, GoogleWriteReservation, GoogleWriteTarget
from schedules.tasks import queue_google_calendar_sync

ISOLATED_KEY_ROTATION_MATERIAL = "isolated-key-rotation-fixture"


class GoogleWriteAdmissionTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="write-admission-fixture")
        self.key = sheet_target_key("synthetic-spreadsheet")
        self.snapshot = {"values": [["合成の非公開セル", 7]], "connection": "synthetic-connection"}

    def job(self, owner=None, kind="google_sheets_export"):
        return AsyncJob.objects.create(
            owner=owner or self.user,
            job_type=kind,
            payload={"spreadsheet_id": "synthetic-spreadsheet", "range": "Characters!A1"},
            expires_at=timezone.now() + timedelta(days=1),
        )

    def register(self, job=None, keys=None, snapshot=None):
        return register_google_write(
            job or self.job(),
            [self.key] if keys is None else keys,
            self.snapshot if snapshot is None else snapshot,
        )

    def allocation(self, row):
        return list(row.reservations.order_by("target_id").values_list("target_id", "sequence"))

    def test_resource_identity_is_stable_across_secrets_and_preserves_opaque_case(self):
        expected = (self.key, calendar_session_target_key(1, 2), calendar_event_target_key("account", "event"))
        with override_settings(SECRET_KEY=ISOLATED_KEY_ROTATION_MATERIAL):
            self.assertEqual(
                expected,
                (
                    sheet_target_key("synthetic-spreadsheet"),
                    calendar_session_target_key(1, 2),
                    calendar_event_target_key("account", "event"),
                ),
            )
        self.assertEqual(self.key, sheet_target_key("  synthetic-spreadsheet  "))
        self.assertNotEqual(self.key, sheet_target_key("Synthetic-spreadsheet"))
        self.assertNotEqual(calendar_session_target_key(1, 2), calendar_session_target_key(2, 1))
        self.assertNotEqual(calendar_event_target_key("account", "event"), calendar_event_target_key("other", "event"))
        self.assertRegex(self.key, r"^[0-9a-f]{64}$")

    def test_invalid_resource_components_fail_without_a_ledger_row(self):
        for value in (None, False, [], "", ".", "..", "bad\x00id", "\ud800"):
            with self.subTest(kind="sheet", value=repr(value)), self.assertRaises(InvalidGoogleWriteAdmission):
                sheet_target_key(value)
        for first, second in ((True, 1), (1, False), (0, 1), (1, -1), ("1", 1), (1, 2**63)):
            with (
                self.subTest(kind="calendar", first=first, second=second),
                self.assertRaises(InvalidGoogleWriteAdmission),
            ):
                calendar_session_target_key(first, second)
        for account, event in ((None, "id"), ("", "id"), ("account", ""), ("account", 3), ("\ud800", "id")):
            with self.subTest(kind="event"), self.assertRaises(InvalidGoogleWriteAdmission):
                calendar_event_target_key(account, event)
        self.assertFalse(GoogleWriteTarget.objects.exists())

    def test_encrypted_snapshot_and_canonical_idempotency(self):
        job = self.job()
        first = self.register(job)
        second = self.register(job, snapshot={"connection": "synthetic-connection", "values": self.snapshot["values"]})
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.ciphertext, second.ciphertext)
        self.assertEqual(open_google_write_snapshot(first), self.snapshot)
        self.assertEqual(self.allocation(first), [(self.key, 1)])
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)
        self.assertNotIn("非公開", first.ciphertext)
        self.assertTrue(first.ciphertext.startswith("v1."))
        self.assertEqual(str(first), f"Google受付 {first.pk}")
        self.assertEqual(str(GoogleWriteTarget.objects.get(pk=self.key)), "Google同期対象")

    def test_changed_registration_cannot_replace_snapshot_or_increment_sequence(self):
        job = self.job()
        row = self.register(job)
        before = GoogleWriteAdmission.objects.filter(pk=row.pk).values().get()
        for keys, snapshot in (([self.key], {"values": [["違う内容"]]}), ([sheet_target_key("other")], self.snapshot)):
            with self.subTest(keys=keys), self.assertRaises(InvalidGoogleWriteAdmission):
                self.register(job, keys=keys, snapshot=snapshot)
            self.assertEqual(GoogleWriteAdmission.objects.filter(pk=row.pk).values().get(), before)
            self.assertEqual(GoogleWriteTarget.objects.count(), 1)
            self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)

    def test_multiple_targets_use_canonical_order_and_independent_sequences(self):
        second_key = calendar_session_target_key(self.user.pk, 42)
        row = self.register(keys=[second_key, self.key])
        self.assertEqual(self.allocation(row), [(key, 1) for key in sorted([second_key, self.key])])
        next_row = self.register(keys=[self.key, second_key])
        self.assertEqual(self.allocation(next_row), [(key, 2) for key in sorted([second_key, self.key])])
        self.assertEqual(open_google_write_snapshot(next_row), self.snapshot)

    def test_shared_sheet_is_sequenced_across_owners_without_exposing_their_snapshot(self):
        first_job = self.job()
        first = self.register(first_job)
        other = get_user_model().objects.create_user(username="other-admission-fixture")
        second_job = self.job(owner=other)
        second_job.created_at = first_job.created_at - timedelta(hours=1)
        second_job.save(update_fields=["created_at"])
        second = self.register(second_job, snapshot={"values": [["別ユーザーの合成セル"]]})
        self.assertEqual(self.allocation(first), [(self.key, 1)])
        self.assertEqual(self.allocation(second), [(self.key, 2)])
        self.assertNotEqual(first.ciphertext, second.ciphertext)
        self.assertEqual(open_google_write_snapshot(first), self.snapshot)
        self.assertEqual(GoogleWriteTarget.objects.count(), 1)
        independent = self.register(keys=[sheet_target_key("independent")])
        self.assertEqual(self.allocation(independent)[0][1], 1)

    def test_invalid_admission_inputs_never_create_target_or_reservation(self):
        job = self.job()
        for keys in (
            None,
            self.key,
            [],
            [self.key, self.key],
            [None],
            ["z" * 64],
            [self.key.upper()],
            [self.key, sheet_target_key("b"), sheet_target_key("c")],
        ):
            with self.subTest(keys=keys), self.assertRaises(InvalidGoogleWriteAdmission):
                register_google_write(job, keys, self.snapshot)
        for snapshot in (
            None,
            [],
            {"nan": float("nan")},
            {"value": object()},
            {"value": "\ud800"},
            {"values": (1, 2)},
            {1: "non-string-json-key"},
        ):
            with self.subTest(snapshot=repr(snapshot)), self.assertRaises(InvalidGoogleWriteAdmission):
                register_google_write(job, [self.key], snapshot)
        self.assertFalse(GoogleWriteTarget.objects.exists())
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())

    def test_stale_wrong_owner_type_or_missing_source_is_rejected(self):
        job = self.job()
        for field, value in (
            ("owner_id", self.user.pk + 999),
            ("job_type", "other"),
            ("created_at", job.created_at - timedelta(seconds=1)),
            ("payload", {"changed": True}),
            ("pk", uuid4()),
        ):
            stale = copy.copy(job)
            setattr(stale, field, value)
            with self.subTest(field=field), self.assertRaises(InvalidGoogleWriteAdmission):
                self.register(stale)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            self.register(self.job(kind="unrelated-task"))
        self.assertFalse(GoogleWriteAdmission.objects.exists())

    def test_started_expired_failed_or_superseded_source_is_not_new_admission(self):
        for update in (
            {"status": AsyncJob.Status.RUNNING},
            {"started_at": timezone.now()},
            {"expires_at": timezone.now() - timedelta(seconds=1)},
            {"status": AsyncJob.Status.FAILED},
            {"payload": {"google_retry_successor": None}},
        ):
            job = self.job()
            AsyncJob.objects.filter(pk=job.pk).update(**update)
            job.refresh_from_db()
            with self.subTest(update=update), self.assertRaises(InvalidGoogleWriteAdmission):
                self.register(job)
        self.assertFalse(GoogleWriteTarget.objects.exists())

    def test_ciphertext_nonce_key_and_all_admission_metadata_are_authenticated(self):
        first, second = self.register(), self.register()
        raw = base64.b64decode(first.ciphertext[3:])
        self.assertNotEqual(raw[:12], base64.b64decode(second.ciphertext[3:])[:12])
        changes = {
            "owner_id_snapshot": self.user.pk + 1,
            "job_type_snapshot": "other",
            "job_created_at": first.job_created_at - timedelta(seconds=1),
            "created_at": first.created_at - timedelta(seconds=1),
            "payload_digest": "0" * 64,
            "allocation_digest": "0" * 64,
            "snapshot_binding": "0" * 64,
            "pk": uuid4(),
            "job_id": second.job_id,
        }
        for field, value in changes.items():
            forged = copy.copy(first)
            setattr(forged, field, value)
            with self.subTest(field=field), self.assertRaises(InvalidGoogleWriteAdmission):
                open_google_write_snapshot(forged)
        for envelope in (
            "",
            None,
            "v2." + first.ciphertext[3:],
            "v1.invalid!",
            "v1.",
            "v1." + base64.b64encode(raw[:-1] + bytes([raw[-1] ^ 1])).decode("ascii"),
        ):
            forged = copy.copy(first)
            forged.ciphertext = envelope
            with self.subTest(envelope=repr(envelope)), self.assertRaises(InvalidGoogleWriteAdmission):
                open_google_write_snapshot(forged)
        with (
            override_settings(SECRET_KEY=ISOLATED_KEY_ROTATION_MATERIAL),
            self.assertRaises(InvalidGoogleWriteAdmission),
        ):
            open_google_write_snapshot(first)

    def test_changed_reservation_is_not_trusted_and_cannot_be_repaired_by_reregister(self):
        job = self.job()
        row = self.register(job)
        reservation = row.reservations.get()
        GoogleWriteTarget.objects.filter(pk=self.key).update(last_sequence=2)
        GoogleWriteReservation.objects.filter(pk=reservation.pk).update(sequence=2)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            open_google_write_snapshot(row)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            self.register(job)
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 2)

    def test_job_and_owner_cleanup_leave_target_sequence_but_erase_private_admission(self):
        row = self.register()
        row.job.delete()
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)
        next_row = self.register()
        self.assertEqual(self.allocation(next_row), [(self.key, 2)])
        self.user.delete()
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 2)

    def test_database_constraints_and_target_protection(self):
        row = self.register()
        target = GoogleWriteTarget.objects.get(pk=self.key)
        with self.assertRaises(ProtectedError):
            target.delete()
        for action in (
            lambda: GoogleWriteTarget.objects.filter(pk=self.key).update(last_sequence=-1),
            lambda: GoogleWriteReservation.objects.filter(admission=row).update(sequence=0),
            lambda: GoogleWriteReservation.objects.create(admission=row, target=target, sequence=2),
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()
        another = self.register(keys=[sheet_target_key("different-target")])
        with self.assertRaises(IntegrityError), transaction.atomic():
            GoogleWriteReservation.objects.create(admission=another, target=target, sequence=1)

    def test_exhausted_sequence_rolls_back_without_partial_admission(self):
        GoogleWriteTarget.objects.create(resource_key=self.key, last_sequence=2**63 - 1)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            self.register()
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())

    def test_real_delivery_intent_and_admission_rollback_together(self):
        with (
            patch("schedules.tasks._broker_available", return_value=True) as broker,
            patch("schedules.tasks.sync_google_calendar.delay") as delay,
        ):
            with transaction.atomic():
                job = self.job(kind="google_calendar_sync")
                job.payload = {"sync_id": 987}
                job.save(update_fields=["payload"])
                row = self.register(job, keys=[calendar_session_target_key(self.user.pk, 123)])
                self.assertIsNone(queue_google_calendar_sync(987, str(job.pk)))
                self.assertTrue(job.google_dispatch.ciphertext)
                self.assertEqual(open_google_write_snapshot(row), self.snapshot)
                transaction.set_rollback(True)
            broker.assert_not_called()
            delay.assert_not_called()
        self.assertFalse(AsyncJob.objects.exists())
        self.assertFalse(GoogleWriteTarget.objects.exists())
        self.assertFalse(GoogleWriteAdmission.objects.exists())

    def test_inner_rollback_does_not_consume_committed_fifo_sequence(self):
        first = self.register()
        with transaction.atomic():
            discarded = self.register()
            self.assertEqual(self.allocation(discarded), [(self.key, 2)])
            transaction.set_rollback(True)
        next_row = self.register()
        self.assertEqual(self.allocation(first), [(self.key, 1)])
        self.assertEqual(self.allocation(next_row), [(self.key, 2)])
        self.assertFalse(GoogleWriteAdmission.objects.filter(pk=discarded.pk).exists())

    def test_mid_persistence_failure_restores_existing_counter_and_all_private_rows(self):
        first = self.register()
        job = self.job()
        with patch.object(GoogleWriteReservation.objects, "bulk_create", side_effect=RuntimeError("合成DB保存障害")):
            with self.assertRaisesRegex(RuntimeError, "合成DB保存障害"):
                self.register(job)
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)
        self.assertEqual(GoogleWriteAdmission.objects.count(), 1)
        self.assertEqual(GoogleWriteReservation.objects.count(), 1)
        self.assertEqual(open_google_write_snapshot(first), self.snapshot)
        second = self.register(job)
        self.assertEqual(self.allocation(second), [(self.key, 2)])

    def test_invalid_key_configuration_is_sanitized_before_allocation(self):
        for secret in (123, [], "", "\ud800"):
            with self.subTest(secret_type=type(secret).__name__), override_settings(SECRET_KEY=secret):
                with self.assertRaises(InvalidGoogleWriteAdmission) as failure:
                    self.register()
                self.assertEqual(
                    str(failure.exception), "Googleの処理受付情報を確認できません。連携設定から新しく実行してください。"
                )
        self.assertFalse(GoogleWriteTarget.objects.exists())

    def test_invalid_open_source_and_authenticated_plaintext_are_rejected(self):
        for row in (None, {}, GoogleWriteAdmission()):
            with self.subTest(row_type=type(row).__name__), self.assertRaises(InvalidGoogleWriteAdmission):
                open_google_write_snapshot(row)
        with self.assertRaises(InvalidGoogleWriteAdmission):
            register_google_write(None, [self.key], {})
        row = self.register()
        for plaintext in (b"[]", b"{", b'{"values": []}'):
            forged = copy.copy(row)
            nonce = b"synthetic123"
            forged.ciphertext = "v1." + base64.b64encode(
                nonce + ledger._cipher().encrypt(nonce, plaintext, ledger._aad(forged))
            ).decode("ascii")
            with self.subTest(plaintext=plaintext), self.assertRaises(InvalidGoogleWriteAdmission):
                open_google_write_snapshot(forged)
        forged = copy.copy(row)
        forged.job_created_at = None
        with self.assertRaises(InvalidGoogleWriteAdmission):
            open_google_write_snapshot(forged)

    def test_persisted_metadata_or_source_changes_prevent_reregistration(self):
        job = self.job()
        row = self.register(job)
        with transaction.atomic():
            GoogleWriteAdmission.objects.filter(pk=row.pk).update(owner_id_snapshot=self.user.pk + 1)
            with self.assertRaises(InvalidGoogleWriteAdmission):
                self.register(job)
            transaction.set_rollback(True)
        job.payload = ["invalid-google-payload"]
        job.save(update_fields=["payload"])
        with self.assertRaises(InvalidGoogleWriteAdmission):
            self.register(job)

    def test_old_code_raw_job_deletion_erases_private_rows_and_preserves_counter(self):
        row = self.register()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM schedules_asyncjob WHERE id = %s",
                [row.job._meta.pk.get_db_prep_value(row.job_id, connection)],
            )
        self.assertFalse(GoogleWriteAdmission.objects.exists())
        self.assertFalse(GoogleWriteReservation.objects.exists())
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)


@skipUnless(connection.vendor == "postgresql", "PostgreSQL専用の受付順競合検証")
class GoogleWriteAdmissionConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="admission-pg-fixture")
        self.key = sheet_target_key("pg-shared-sheet")

    def job(self):
        return AsyncJob.objects.create(
            owner=self.user, job_type="google_sheets_export", payload={}, expires_at=timezone.now() + timedelta(days=1)
        )

    def _register(self, job, keys, backend_ids, barrier=None):
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                backend_ids.append(cursor.fetchone()[0])
            if barrier is not None:
                barrier.wait(timeout=10)
            return register_google_write(job, keys, {"fixture": "private synthetic value"}).pk
        finally:
            close_old_connections()

    def _observe_lock(self, backend_ids, table, timeout=5, minimum=2):
        deadline = monotonic() + timeout
        observed = []
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT pid, length(query), position('FOR UPDATE' in query) "
                    "FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid = ANY(%s) AND wait_event_type='Lock' "
                    "AND query LIKE %s",
                    [backend_ids, f"%{table}%"],
                )
                observed = cursor.fetchall()
                if sum(position > 0 for _, _, position in observed) >= minimum:
                    print(f"GOOGLE_ADMISSION_LOCK table={table} observed={observed}")
                    return
            sleep(0.01)
        self.fail(f"実受付の行ロック待機を観測できませんでした。SQL観測長/位置: {observed}")

    def test_two_jobs_wait_on_one_shared_target_and_receive_committed_sequence(self):
        GoogleWriteTarget.objects.create(resource_key=self.key)
        first, second = self.job(), self.job()
        backend_ids = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            with transaction.atomic():
                GoogleWriteTarget.objects.select_for_update().get(pk=self.key)
                one = pool.submit(self._register, first, [self.key], backend_ids)
                two = pool.submit(self._register, second, [self.key], backend_ids)
                self._observe_lock(backend_ids, "schedules_googlewritetarget")
            ids = [one.result(timeout=10), two.result(timeout=10)]
        self.assertEqual(len(set(backend_ids)), 2)
        self.assertEqual(len(set(ids)), 2)
        self.assertCountEqual(list(GoogleWriteReservation.objects.values_list("sequence", flat=True)), [1, 2])
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 2)

    def test_first_creation_and_opposite_multi_target_order_do_not_duplicate_or_deadlock(self):
        second_key = calendar_session_target_key(self.user.pk, 321)
        first, second = self.job(), self.job()
        backend_ids = []
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(self._register, first, [self.key, second_key], backend_ids, barrier)
            two = pool.submit(self._register, second, [second_key, self.key], backend_ids, barrier)
            ids = [one.result(timeout=10), two.result(timeout=10)]
        self.assertEqual(len(set(backend_ids)), 2)
        self.assertEqual(GoogleWriteTarget.objects.count(), 2)
        self.assertEqual(len(set(ids)), 2)
        for key in (self.key, second_key):
            self.assertCountEqual(
                list(GoogleWriteReservation.objects.filter(target_id=key).values_list("sequence", flat=True)), [1, 2]
            )

    def test_same_job_waits_on_source_and_reuses_one_immutable_admission(self):
        job = self.job()
        backend_ids = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            with transaction.atomic():
                AsyncJob.objects.select_for_update().get(pk=job.pk)
                one = pool.submit(self._register, job, [self.key], backend_ids)
                two = pool.submit(self._register, job, [self.key], backend_ids)
                self._observe_lock(backend_ids, "schedules_asyncjob")
            ids = [one.result(timeout=10), two.result(timeout=10)]
        self.assertEqual(len(set(backend_ids)), 2)
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(GoogleWriteTarget.objects.get(pk=self.key).last_sequence, 1)
        self.assertEqual(GoogleWriteAdmission.objects.count(), 1)

    def test_lock_observation_timeout_is_bounded(self):
        with self.assertRaisesRegex(AssertionError, "行ロック待機"):
            self._observe_lock([], "schedules_asyncjob", timeout=0.02)

    def test_mutating_caller_snapshot_during_lock_wait_cannot_change_sealed_acceptance(self):
        job = self.job()
        snapshot = {"values": [["受付前の内容"]]}
        backend_ids = []

        def run():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_ids.append(cursor.fetchone()[0])
                return register_google_write(job, [self.key], snapshot).pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                AsyncJob.objects.select_for_update().get(pk=job.pk)
                future = pool.submit(run)
                self._observe_lock(backend_ids, "schedules_asyncjob", minimum=1)
                snapshot["values"][0][0] = "待機中に変更した内容"
            row = GoogleWriteAdmission.objects.get(pk=future.result(timeout=10))
        self.assertEqual(open_google_write_snapshot(row), {"values": [["受付前の内容"]]})
