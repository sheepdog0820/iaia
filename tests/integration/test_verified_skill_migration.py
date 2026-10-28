import io
import json
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

from tests.integration import test_skill_other_points_migration as fixtures


class VerifiedSkillMigrationTests(fixtures.SkillOtherPointsMigrationTests):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL transactional migration verification")
        super().setUp()

    def invoke(self, **overrides):
        options = {
            "apply": True,
            "expected_host": connection.settings_dict["HOST"],
            "expected_database": connection.settings_dict["NAME"],
        }
        options.update(overrides)
        output = io.StringIO()
        call_command("apply_verified_skill_adjustments", stdout=output, **options)
        return json.loads(output.getvalue())

    def current_rows(self):
        return {
            edition: list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values())
            for edition in ("6th", "7th")
        }

    def assert_unchanged(self, before=None):
        self.assertEqual(self.current_rows(), before or self.before)
        self.assertNotIn(self.new_target[0], MigrationRecorder(connection).applied_migrations())

    def test_applies_only_0068_and_verifies_every_column(self):
        self.assertEqual(self.invoke(), {"status": "applied", "rows_verified": {"6th": 3, "7th": 3}})
        for edition, rows in self.current_rows().items():
            expected = [
                dict(row, bonus_points=0, other_points=row["other_points"] + row["bonus_points"])
                for row in self.before[edition]
            ]
            self.assertEqual(rows, expected)
        self.assertIn(self.new_target[0], MigrationRecorder(connection).applied_migrations())
        with self.assertRaisesMessage(CommandError, "未適用の0068だけ"):
            self.invoke()

    def test_requires_explicit_apply_and_expected_target_before_queries(self):
        for overrides in ({"apply": False}, {"expected_host": ""}, {"expected_database": ""}):
            with self.subTest(overrides=overrides), self.assertNumQueries(0):
                with self.assertRaisesMessage(CommandError, "明示"):
                    self.invoke(**overrides)
        self.assert_unchanged()

    def test_refuses_different_host_or_database(self):
        for overrides in ({"expected_host": "other-private-host"}, {"expected_database": "other-private-db"}):
            with self.subTest(overrides=overrides):
                with self.assertRaisesMessage(CommandError, "接続先が一致しません") as caught:
                    self.invoke(**overrides)
                self.assertNotIn("other-private", str(caught.exception))
        self.assert_unchanged()

    def test_refuses_actual_database_that_differs_from_configured_target(self):
        # Keep the real connection open, then simulate stale/misdirected connection settings.
        with patch.dict(connection.settings_dict, {"NAME": "different-configured-fixture"}):
            with self.assertRaisesMessage(CommandError, "接続先が一致しません"):
                self.invoke()
        self.assert_unchanged()

    def test_handles_empty_tables_and_refuses_missing_applied_record(self):
        for edition in ("6th", "7th"):
            self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.all().delete()
        with patch.object(MigrationExecutor, "migrate", return_value=None):
            with self.assertRaisesMessage(CommandError, "適用記録を確認できない"):
                self.invoke()
        self.assertNotIn(self.new_target[0], MigrationRecorder(connection).applied_migrations())
        self.assertEqual(self.invoke(), {"status": "applied", "rows_verified": {"6th": 0, "7th": 0}})

    def test_locks_both_skill_tables_and_history_until_commit(self):
        migrate = MigrationExecutor.migrate
        writer = connection.copy(alias="verified-migration-other-writer")

        def check_writer_locks(executor, *args, **kwargs):
            with writer.cursor() as cursor:
                cursor.execute("SET lock_timeout = '100ms'")
                statements = (
                    "UPDATE accounts_characterskill6th SET notes = 'concurrent-fixture'",
                    "UPDATE accounts_characterskill7th SET notes = 'concurrent-fixture'",
                    "UPDATE django_migrations SET name = name WHERE app = 'accounts'",
                )
                for sql in statements:
                    with self.assertRaises(OperationalError) as caught:
                        cursor.execute(sql)
                    self.assertEqual(caught.exception.__cause__.sqlstate, "55P03")
            return migrate(executor, *args, **kwargs)

        try:
            with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=check_writer_locks):
                self.invoke()
            with writer.cursor() as cursor:
                cursor.execute("UPDATE accounts_characterskill6th SET notes = 'after-commit-fixture'")
            self.assertTrue(all(row["notes"] == "after-commit-fixture" for row in self.current_rows()["6th"]))
        finally:
            writer.close()

    def test_compares_physical_columns_outside_the_historical_model(self):
        migrate = MigrationExecutor.migrate
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE accounts_characterskill7th ADD COLUMN private_extra_fixture text")
            cursor.execute("UPDATE accounts_characterskill7th SET private_extra_fixture = 'original-fixture'")

        def corrupt_extra_column(executor, *args, **kwargs):
            result = migrate(executor, *args, **kwargs)
            with connection.cursor() as cursor:
                cursor.execute("UPDATE accounts_characterskill7th SET private_extra_fixture = 'changed-fixture'")
            return result

        try:
            with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=corrupt_extra_column):
                with self.assertRaisesMessage(CommandError, "移行前後の全行比較"):
                    self.invoke()
            self.assert_unchanged()
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT private_extra_fixture FROM accounts_characterskill7th")
                self.assertEqual(cursor.fetchall(), [("original-fixture",)])
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE accounts_characterskill7th DROP COLUMN private_extra_fixture")

    def test_refuses_existing_transaction_and_other_backend(self):
        with transaction.atomic():
            with self.assertRaisesMessage(CommandError, "既存トランザクション"):
                self.invoke()
        with patch.object(connection, "vendor", "sqlite"):
            with self.assertRaisesMessage(CommandError, "PostgreSQL専用"):
                self.invoke()
        self.assert_unchanged()

    def test_refuses_other_pending_migrations_without_applying_any(self):
        recorder = MigrationRecorder(connection)
        recorder.record_unapplied(*self.old_target[0])
        try:
            with self.assertRaisesMessage(CommandError, "未適用の0068だけ"):
                self.invoke()
            self.assert_unchanged()
        finally:
            recorder.record_applied(*self.old_target[0])

    def test_overflow_is_rejected_before_changes(self):
        skill_model = self.apps.get_model("accounts", "CharacterSkill7th")
        original = self.before["7th"][0]
        row = skill_model.objects.filter(pk=original["id"])
        try:
            for bonus, other in ((1, 2147483647), (-1, -2147483648)):
                with self.subTest(bonus=bonus, other=other):
                    row.update(other_points=other, bonus_points=bonus)
                    before = self.current_rows()
                    with self.assertRaisesMessage(CommandError, "整数範囲"):
                        self.invoke()
                    self.assert_unchanged(before)
        finally:
            row.update(other_points=original["other_points"], bonus_points=original["bonus_points"])

    def test_failure_after_real_migration_rolls_back_data_and_recorder_without_private_error(self):
        migrate = MigrationExecutor.migrate

        def fail_after_migration(executor, *args, **kwargs):
            migrate(executor, *args, **kwargs)
            raise RuntimeError("private-signed-url-and-user-data")

        output = io.StringIO()
        with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=fail_after_migration):
            with self.assertRaisesMessage(CommandError, "検証付き移行に失敗") as caught:
                call_command(
                    "apply_verified_skill_adjustments",
                    apply=True,
                    expected_host=connection.settings_dict["HOST"],
                    expected_database=connection.settings_dict["NAME"],
                    stdout=output,
                )
        self.assertNotIn("private", str(caught.exception))
        self.assertEqual(output.getvalue(), "")
        self.assert_unchanged()

    def test_commit_reply_loss_requires_readback_and_never_claims_rollback(self):
        commit = connection.commit

        def commit_then_lose_reply():
            commit()
            raise OperationalError("private-commit-connection-details")

        with patch.object(connection, "commit", side_effect=commit_then_lose_reply):
            with self.assertRaisesMessage(CommandError, "適用状態を読み取りで再確認") as caught:
                self.invoke()
        self.assertNotIn("private", str(caught.exception))
        self.assertNotIn("取り消しました", str(caught.exception))
        self.assertIn(self.new_target[0], MigrationRecorder(connection).applied_migrations())
        for edition, rows in self.current_rows().items():
            self.assertEqual(
                rows,
                [
                    dict(row, bonus_points=0, other_points=row["other_points"] + row["bonus_points"])
                    for row in self.before[edition]
                ],
            )
        with self.assertRaisesMessage(CommandError, "未適用の0068だけ"):
            self.invoke()

    def test_unrelated_column_or_missing_row_mismatch_rolls_back_both_editions_and_history(self):
        migrate = MigrationExecutor.migrate
        skill_model = self.apps.get_model("accounts", "CharacterSkill7th")
        for change in ("notes", "delete", "points"):
            with self.subTest(change=change):

                def corrupt_after_migration(executor, *args, **kwargs):
                    result = migrate(executor, *args, **kwargs)
                    row = skill_model.objects.filter(pk=self.before["7th"][0]["id"])
                    if change == "delete":
                        row.delete()
                    else:
                        row.update(**({"notes": "private-corruption"} if change == "notes" else {"other_points": 0}))
                    return result

                with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=corrupt_after_migration):
                    with self.assertRaisesMessage(CommandError, "移行前後の全行比較"):
                        self.invoke()
                self.assert_unchanged()
