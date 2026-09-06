import io
import json
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError, connection, transaction
from django.test import TransactionTestCase


class ReleaseDatabasePreflightTests(TransactionTestCase):
    def run_probe(self):
        output = io.StringIO()
        call_command("release_database_preflight", stdout=output)
        return json.loads(output.getvalue())

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL read-only transaction verification")

    def test_reports_schema_and_history_without_personal_data(self):
        report = self.run_probe()
        self.assertTrue(report["read_only"])
        self.assertIn("0058_minimize_character_sheet_registry", report["migrations"]["accounts"])
        self.assertIn("0055_allow_multiple_participant_roles", report["migrations"]["schedules"])
        self.assertNotIn("name", report["registry_columns"])
        self.assertIn(["participant_id", "role"], report["role_unique_columns"])
        self.assertEqual(report["participants_with_multiple_roles"], 0)
        self.assertEqual(report["duplicate_role_pairs"], 0)

    def test_reports_reverse_migration_risk_without_names_or_ids(self):
        from schedules.models import SessionParticipant, SessionParticipantRole, TRPGSession

        session = TRPGSession.objects.create(title="非公開の検査対象")
        participant = SessionParticipant.objects.create(session=session, guest_name="非公開の参加者")
        SessionParticipantRole.objects.create(participant=participant, role="player")
        SessionParticipantRole.objects.create(participant=participant, role="gm")
        report = self.run_probe()
        self.assertEqual(report["participants_with_multiple_roles"], 1)
        self.assertEqual(report["duplicate_role_pairs"], 0)
        self.assertNotIn("非公開", json.dumps(report, ensure_ascii=False))
        self.assertEqual(SessionParticipantRole.objects.filter(participant=participant).count(), 2)

    def test_database_rejects_accidental_write_and_error_is_redacted(self):
        original = connection.introspection.get_table_description

        def attempt_write(cursor, table_name):
            cursor.execute("CREATE TABLE preflight_must_not_create (id integer)")
            return original(cursor, table_name)

        output = io.StringIO()
        with patch.object(connection.introspection, "get_table_description", side_effect=attempt_write):
            with self.assertRaisesMessage(CommandError, "読み取り専用のDB検査に失敗しました"):
                call_command("release_database_preflight", stdout=output)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("preflight_must_not_create", connection.introspection.table_names())

    def test_refuses_existing_transaction(self):
        with transaction.atomic():
            with self.assertRaisesMessage(CommandError, "既存トランザクション内では実行できません"):
                self.run_probe()

    def test_missing_table_fails_without_partial_output(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE accounts_charactersheet RENAME TO preflight_hidden_registry")
        try:
            with self.assertRaisesMessage(CommandError, "読み取り専用のDB検査に失敗しました"):
                self.run_probe()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE preflight_hidden_registry RENAME TO accounts_charactersheet")

    def test_rejects_other_backends(self):
        with patch.object(connection, "vendor", "sqlite"):
            with self.assertRaisesMessage(CommandError, "PostgreSQL専用"):
                self.run_probe()

    def test_connection_error_does_not_expose_connection_details(self):
        with patch.object(connection, "get_autocommit", side_effect=OperationalError("private-host-and-user")):
            with self.assertRaisesMessage(CommandError, "読み取り専用のDB検査に失敗しました") as caught:
                self.run_probe()
        self.assertNotIn("private-host", str(caught.exception))

    def test_reports_legacy_schema_without_modifying_it(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE accounts_charactersheet ADD COLUMN notes text")
            cursor.execute("ALTER TABLE schedules_sessionparticipantrole DROP CONSTRAINT uniq_participant_role")
            cursor.execute(
                "ALTER TABLE schedules_sessionparticipantrole "
                "ADD CONSTRAINT uniq_participant_single_role UNIQUE (participant_id)"
            )
        try:
            report = self.run_probe()
            self.assertIn("notes", report["registry_columns"])
            self.assertIn(["participant_id"], report["role_unique_columns"])
            self.assertNotIn(["participant_id", "role"], report["role_unique_columns"])
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE accounts_charactersheet DROP COLUMN notes")
                cursor.execute(
                    "ALTER TABLE schedules_sessionparticipantrole DROP CONSTRAINT uniq_participant_single_role"
                )
                cursor.execute(
                    "ALTER TABLE schedules_sessionparticipantrole "
                    "ADD CONSTRAINT uniq_participant_role UNIQUE (participant_id, role)"
                )
