"""Local schema and old-code cleanup compatibility, not a shared DB migration."""

from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone

from schedules.google_write_ledger import open_google_write_snapshot, register_google_write, sheet_target_key
from schedules.models import AsyncJob, GoogleWriteAdmission, GoogleWriteReservation, GoogleWriteTarget


class GoogleWriteAdmissionMigrationTest(TransactionTestCase):
    old = [("schedules", "0058_google_dispatch_delete_cascade")]
    new = [("schedules", "0060_google_write_delete_cascade")]

    def setUp(self):
        self.original_targets = MigrationExecutor(connection).loader.graph.leaf_nodes("schedules")

    def test_forward_reverse_preserve_existing_job_and_do_not_invent_legacy_admission(self):
        user = get_user_model().objects.create_user(username="admission-schema-fixture")
        job = AsyncJob.objects.create(
            owner=user,
            job_type="google_sheets_export",
            payload={"legacy": True},
            expires_at=timezone.now() + timedelta(days=1),
        )
        before = AsyncJob.objects.filter(pk=job.pk).values().get()
        try:
            MigrationExecutor(connection).migrate(self.old)
            self.assertNotIn("schedules_googlewriteadmission", connection.introspection.table_names())
            self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
            MigrationExecutor(connection).migrate(self.new)
            self.assertFalse(GoogleWriteAdmission.objects.exists())
            self.assertFalse(GoogleWriteTarget.objects.exists())
            # Runtime helpers use the current model; test the old migration
            # boundary above before restoring its required local schema.
            MigrationExecutor(connection).migrate(self.original_targets)
            row = register_google_write(job, [sheet_target_key("schema-fixture")], {"private": "合成データ"})
            self.assertEqual(open_google_write_snapshot(row), {"private": "合成データ"})
            self.assertTrue(GoogleWriteReservation.objects.filter(admission=row).exists())
            MigrationExecutor(connection).migrate(self.old)
            self.assertNotIn("schedules_googlewritereservation", connection.introspection.table_names())
            self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
            MigrationExecutor(connection).migrate(self.new)
            self.assertFalse(GoogleWriteAdmission.objects.exists())
            self.assertFalse(GoogleWriteTarget.objects.exists())
            self.assertEqual(AsyncJob.objects.filter(pk=job.pk).values().get(), before)
        finally:
            MigrationExecutor(connection).migrate(self.original_targets)

    def test_reverse_only_cascade_keeps_receipts_and_reinstall_preserves_counter(self):
        user = get_user_model().objects.create_user(username="admission-cascade-fixture")
        job = AsyncJob.objects.create(
            owner=user, job_type="google_sheets_export", payload={}, expires_at=timezone.now() + timedelta(days=1)
        )
        key = sheet_target_key("cascade-fixture")
        row = register_google_write(job, [key], {"private": "合成データ"})
        try:
            MigrationExecutor(connection).migrate([("schedules", "0059_google_write_admission")])
            self.assertEqual(open_google_write_snapshot(row), {"private": "合成データ"})
            historical = (
                MigrationExecutor(connection)
                .loader.project_state([("schedules", "0059_google_write_admission")])
                .apps.get_model("schedules", "GoogleWriteTarget")
            )
            self.assertEqual(historical.objects.get(pk=key).last_sequence, 1)
            MigrationExecutor(connection).migrate(self.new)
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM schedules_asyncjob WHERE id = %s", [job._meta.pk.get_db_prep_value(job.pk, connection)]
                )
            self.assertFalse(GoogleWriteAdmission.objects.exists())
            self.assertFalse(GoogleWriteReservation.objects.exists())
            self.assertEqual(historical.objects.get(pk=key).last_sequence, 1)
        finally:
            MigrationExecutor(connection).migrate(self.original_targets)


class GoogleWriteCascadeMigrationGuardTest(SimpleTestCase):
    def setUp(self):
        self.migration = import_module("schedules.migrations.0060_google_write_delete_cascade")

    def test_sqlite_cascade_and_reverse_use_two_specific_triggers(self):
        fake = SimpleNamespace(connection=SimpleNamespace(vendor="sqlite"), execute=Mock())
        self.migration.install_delete_cascade(None, fake)
        self.assertEqual(fake.execute.call_count, 2)
        self.assertIn("AFTER DELETE ON schedules_asyncjob", fake.execute.call_args_list[0].args[0])
        self.assertIn("AFTER DELETE ON schedules_googlewriteadmission", fake.execute.call_args_list[1].args[0])
        fake.execute.reset_mock()
        self.migration.remove_delete_cascade(None, fake)
        self.assertEqual(
            [call.args[0] for call in fake.execute.call_args_list],
            ["DROP TRIGGER google_write_admission_id_delete", "DROP TRIGGER google_write_job_id_delete"],
        )

    def test_unsupported_database_and_missing_or_ambiguous_fk_are_rejected(self):
        fake = SimpleNamespace(connection=SimpleNamespace(vendor="unavailable"))
        for function in (self.migration.install_delete_cascade, self.migration.remove_delete_cascade):
            with self.assertRaisesRegex(RuntimeError, "Google受付はSQLiteまたはPostgreSQL"):
                function(None, fake)
        fake.connection = MagicMock(vendor="postgresql")
        reference = {"foreign_key": ("schedules_asyncjob", "id"), "columns": ["job_id"]}
        for constraints in ({}, {"one": reference, "two": reference}):
            fake.connection.introspection.get_constraints.return_value = constraints
            with self.assertRaisesRegex(RuntimeError, "Google受付の参照制約"):
                self.migration._postgres_fk(
                    fake, "schedules_googlewriteadmission", "job_id", "schedules_asyncjob", True
                )

    def test_postgres_reversal_restores_deferrable_fk_without_cascade(self):
        fake = SimpleNamespace(
            connection=MagicMock(vendor="postgresql"), quote_name=lambda value: f'"{value}"', execute=Mock()
        )

        def constraints(cursor, table):
            column, parent = (
                ("job_id", "schedules_asyncjob")
                if table == "schedules_googlewriteadmission"
                else ("admission_id", "schedules_googlewriteadmission")
            )
            return {"synthetic-fk": {"foreign_key": (parent, "id"), "columns": [column]}}

        fake.connection.introspection.get_constraints.side_effect = constraints
        self.migration.install_delete_cascade(None, fake)
        self.assertEqual(fake.execute.call_count, 4)
        for call in fake.execute.call_args_list[1::2]:
            self.assertIn("ON DELETE CASCADE", call.args[0])
            self.assertIn("DEFERRABLE INITIALLY DEFERRED", call.args[0])
        fake.execute.reset_mock()
        self.migration.remove_delete_cascade(None, fake)
        self.assertEqual(fake.execute.call_count, 4)
        for call in fake.execute.call_args_list[1::2]:
            self.assertNotIn("ON DELETE CASCADE", call.args[0])
            self.assertIn("DEFERRABLE INITIALLY DEFERRED", call.args[0])
