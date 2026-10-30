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


class VerifiedBillingPrerequisiteMigrationTests(fixtures.SkillOtherPointsMigrationTests):
    old_target = [("accounts", "0064_preserve_character_descendants")]
    batch_targets = (
        ("accounts", "0065_stripe_billing_requests"),
        ("accounts", "0066_stripe_invoice_states"),
        ("accounts", "0067_billing_email_delivery"),
        ("accounts", "0068_merge_skill_bonus_into_other"),
    )
    new_tables = (
        "accounts_stripebillingrequest",
        "accounts_stripeinvoicestate",
        "accounts_billingemaildelivery",
    )

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL transactional release migration verification")
        super().setUp()
        user = self.apps.get_model("accounts", "CustomUser").objects.get(username="migration-fixture")
        self.subscription = self.apps.get_model("accounts", "PremiumSubscription").objects.create(
            user=user, subscription_status="active", stripe_customer_id="cus_private_fixture"
        )
        self.audit = self.apps.get_model("accounts", "PremiumAuditLog").objects.create(
            user=user, action="granted", source="stripe", metadata={"private": "synthetic-audit-fixture"}
        )
        self.billing_before = self.billing_rows()

    def invoke(self, **overrides):
        options = {
            "apply": True,
            "expected_host": connection.settings_dict["HOST"],
            "expected_database": connection.settings_dict["NAME"],
            "include_billing_prerequisites": True,
        }
        options.update(overrides)
        if not options["include_billing_prerequisites"]:
            options.pop("include_billing_prerequisites")
        output = io.StringIO()
        call_command("apply_verified_skill_adjustments", stdout=output, **options)
        return json.loads(output.getvalue())

    def current_rows(self):
        return {
            edition: list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values())
            for edition in ("6th", "7th")
        }

    def billing_rows(self):
        return {
            name: list(self.apps.get_model("accounts", model).objects.order_by("pk").values())
            for name, model in (("subscriptions", "PremiumSubscription"), ("audit_logs", "PremiumAuditLog"))
        }

    def assert_no_batch_changes(self, before=None):
        self.assertEqual(self.current_rows(), before or self.before)
        self.assertEqual(self.billing_rows(), self.billing_before)
        self.assertFalse(set(self.new_tables) & set(connection.introspection.table_names()))
        self.assertFalse(set(self.batch_targets) & set(MigrationRecorder(connection).applied_migrations()))

    def assert_batch_applied(self):
        self.assertTrue(set(self.new_tables) <= set(connection.introspection.table_names()))
        self.assertTrue(set(self.batch_targets) <= set(MigrationRecorder(connection).applied_migrations()))
        self.assertEqual(self.billing_rows(), self.billing_before)
        for edition, rows in self.current_rows().items():
            self.assertEqual(
                rows,
                [
                    dict(row, bonus_points=0, other_points=row["other_points"] + row["bonus_points"])
                    for row in self.before[edition]
                ],
            )

    def test_explicit_batch_from_0064_creates_empty_billing_tables_and_preserves_all_existing_values(self):
        self.assertEqual(
            self.invoke(),
            {
                "status": "applied",
                "rows_verified": {"6th": 3, "7th": 3},
                "applied_migrations": [f"{app}.{name}" for app, name in self.batch_targets],
                "billing_rows_verified": {"subscriptions": 1, "audit_logs": 1},
            },
        )
        self.assert_batch_applied()
        with connection.cursor() as cursor:
            for table in self.new_tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                self.assertEqual(cursor.fetchone()[0], 0)

    def test_default_mode_still_rejects_billing_prerequisites_without_changing_anything(self):
        with self.assertRaisesMessage(CommandError, "未適用の0068だけ"):
            self.invoke(include_billing_prerequisites=False)
        self.assert_no_batch_changes()

    def test_failure_after_first_new_table_rolls_back_ddl_history_and_every_existing_row(self):
        apply_migration = MigrationExecutor.apply_migration

        def fail_on_second_migration(executor, state, migration, *args, **kwargs):
            if (migration.app_label, migration.name) == self.batch_targets[1]:
                self.assertIn(self.new_tables[0], connection.introspection.table_names())
                raise RuntimeError("private-billing-schema-failure")
            return apply_migration(executor, state, migration, *args, **kwargs)

        with patch.object(MigrationExecutor, "apply_migration", autospec=True, side_effect=fail_on_second_migration):
            with self.assertRaisesMessage(CommandError, "検証付き移行に失敗") as caught:
                self.invoke()
        self.assertNotIn("private", str(caught.exception))
        self.assert_no_batch_changes()

    def test_new_tables_have_the_required_uniqueness_foreign_keys_and_delivery_index(self):
        self.invoke()
        expected = {
            self.new_tables[0]: (
                {("id",), ("idempotency_key",), ("subscription_id", "operation")},
                {"subscription_id"},
            ),
            self.new_tables[1]: ({("id",), ("invoice_id",)}, {"subscription_id"}),
            self.new_tables[2]: ({("id",), ("audit_id",)}, {"subscription_id", "audit_id"}),
        }
        with connection.cursor() as cursor:
            for table, (unique_columns, foreign_columns) in expected.items():
                constraints = connection.introspection.get_constraints(cursor, table)
                actual_unique = {tuple(c["columns"]) for c in constraints.values() if c["unique"] or c["primary_key"]}
                self.assertTrue(unique_columns <= actual_unique, table)
                self.assertEqual({c["columns"][0] for c in constraints.values() if c["foreign_key"]}, foreign_columns)
            delivery = connection.introspection.get_constraints(cursor, self.new_tables[2])
        self.assertTrue(delivery["billing_mail_due_idx"]["index"])
        self.assertEqual(delivery["billing_mail_due_idx"]["columns"], ["status", "next_attempt_at"])

    def test_batch_accepts_empty_skill_and_billing_tables(self):
        for model in ("PremiumAuditLog", "PremiumSubscription", "CharacterSkill6th", "CharacterSkill7th"):
            self.apps.get_model("accounts", model).objects.all().delete()
        self.before = self.current_rows()
        self.billing_before = self.billing_rows()
        result = self.invoke()
        self.assertEqual(result["rows_verified"], {"6th": 0, "7th": 0})
        self.assertEqual(result["billing_rows_verified"], {"subscriptions": 0, "audit_logs": 0})
        self.assert_batch_applied()

    def test_batch_preserves_negative_adjustments_and_exact_integer_boundaries_in_both_editions(self):
        for edition in ("6th", "7th"):
            model = self.apps.get_model("accounts", f"CharacterSkill{edition}")
            for row, (bonus, other) in zip(
                self.before[edition], ((-30, 5), (1, 2147483646), (-1, -2147483647)), strict=True
            ):
                model.objects.filter(pk=row["id"]).update(bonus_points=bonus, other_points=other)
        self.before = self.current_rows()
        self.invoke()
        self.assert_batch_applied()
        for rows in self.current_rows().values():
            self.assertEqual([row["other_points"] for row in rows], [-25, 2147483647, -2147483648])

    def test_unrelated_skill_column_mismatch_also_rolls_back_all_new_tables(self):
        migrate = MigrationExecutor.migrate

        def corrupt_skill(executor, *args, **kwargs):
            result = migrate(executor, *args, **kwargs)
            self.apps.get_model("accounts", "CharacterSkill7th").objects.update(notes="private-unexpected-change")
            return result

        with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=corrupt_skill):
            with self.assertRaisesMessage(CommandError, "移行前後の全行比較") as caught:
                self.invoke()
        self.assertNotIn("private", str(caught.exception))
        self.assert_no_batch_changes()

    def test_batch_requires_explicit_apply_and_matching_connection_before_queries(self):
        for options in (
            {"apply": False},
            {"expected_host": ""},
            {"expected_database": ""},
            {"expected_host": "private-wrong-host"},
            {"expected_database": "private-wrong-db"},
        ):
            with self.subTest(options=options), self.assertNumQueries(0):
                with self.assertRaises(CommandError) as caught:
                    self.invoke(**options)
            self.assertNotIn("private", str(caught.exception))
        self.assert_no_batch_changes()

    def test_batch_refuses_a_suffix_or_an_unrelated_pending_migration(self):
        recorder = MigrationRecorder(connection)
        other = next(target for target in self.final_targets if target[0] == "schedules")
        recorder.record_unapplied(*other)
        try:
            with self.assertRaisesMessage(CommandError, "0065〜0068"):
                self.invoke()
            self.assert_no_batch_changes()
        finally:
            recorder.record_applied(*other)
        MigrationExecutor(connection).migrate([self.batch_targets[2]])
        with self.assertRaisesMessage(CommandError, "0065〜0068"):
            self.invoke()
        self.assertEqual(self.current_rows(), self.before)
        self.assertNotIn(self.new_target[0], recorder.applied_migrations())

    def test_batch_refuses_an_applied_migration_unknown_to_the_release_graph(self):
        recorder = MigrationRecorder(connection)
        unknown = ("private_unreviewed_app", "0001_unknown_fixture")
        recorder.record_applied(*unknown)
        try:
            with self.assertRaisesMessage(CommandError, "未知の適用履歴") as caught:
                self.invoke()
            self.assertNotIn("private", str(caught.exception))
            self.assert_no_batch_changes()
        finally:
            recorder.record_unapplied(*unknown)

    def test_batch_locks_existing_billing_data_as_well_as_skills_and_history(self):
        migrate = MigrationExecutor.migrate
        writer = connection.copy(alias="billing-migration-other-writer")

        def verify_locks(executor, *args, **kwargs):
            with writer.cursor() as cursor:
                cursor.execute("SET lock_timeout = '100ms'")
                for statement in (
                    "UPDATE accounts_premiumsubscription SET subscription_status = subscription_status",
                    "UPDATE accounts_premiumauditlog SET reason = reason",
                    "UPDATE accounts_characterskill6th SET notes = notes",
                    "UPDATE accounts_characterskill7th SET notes = notes",
                    "UPDATE django_migrations SET name = name WHERE app = 'accounts'",
                ):
                    with self.assertRaises(OperationalError) as caught:
                        cursor.execute(statement)
                    self.assertEqual(caught.exception.__cause__.sqlstate, "55P03")
            return migrate(executor, *args, **kwargs)

        try:
            with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=verify_locks):
                self.invoke()
            with writer.cursor() as cursor:
                cursor.execute("UPDATE accounts_premiumauditlog SET reason = reason")
        finally:
            writer.close()
        self.assert_batch_applied()

    def test_changed_or_deleted_billing_parent_rows_roll_back_schema_data_and_history(self):
        migrate = MigrationExecutor.migrate
        for change in ("subscription", "audit", "delete"):
            with self.subTest(change=change):

                def corrupt_billing(executor, *args, **kwargs):
                    result = migrate(executor, *args, **kwargs)
                    if change == "subscription":
                        self.apps.get_model("accounts", "PremiumSubscription").objects.update(
                            stripe_customer_id="private-changed"
                        )
                    elif change == "audit":
                        self.apps.get_model("accounts", "PremiumAuditLog").objects.update(reason="private-changed")
                    else:
                        self.apps.get_model("accounts", "PremiumAuditLog").objects.all().delete()
                    return result

                with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=corrupt_billing):
                    with self.assertRaisesMessage(CommandError, "課金データの全行比較") as caught:
                        self.invoke()
                self.assertNotIn("private", str(caught.exception))
                self.assert_no_batch_changes()

    def test_compares_extra_physical_billing_columns_not_present_in_historical_models(self):
        migrate = MigrationExecutor.migrate
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE accounts_premiumauditlog ADD COLUMN private_extra_fixture text")
            cursor.execute("UPDATE accounts_premiumauditlog SET private_extra_fixture = 'before-fixture'")

        def corrupt_extra(executor, *args, **kwargs):
            result = migrate(executor, *args, **kwargs)
            with connection.cursor() as cursor:
                cursor.execute("UPDATE accounts_premiumauditlog SET private_extra_fixture = 'changed-fixture'")
            return result

        try:
            with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=corrupt_extra):
                with self.assertRaisesMessage(CommandError, "課金データの全行比較"):
                    self.invoke()
            self.assert_no_batch_changes()
            with connection.cursor() as cursor:
                cursor.execute("SELECT private_extra_fixture FROM accounts_premiumauditlog")
                self.assertEqual(cursor.fetchall(), [("before-fixture",)])
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE accounts_premiumauditlog DROP COLUMN private_extra_fixture")

    def test_unexpected_new_billing_rows_are_rejected_without_exposing_parameters(self):
        migrate = MigrationExecutor.migrate

        def add_unexpected_request(executor, *args, **kwargs):
            result = migrate(executor, *args, **kwargs)
            model = executor.loader.project_state(self.new_target).apps.get_model("accounts", "StripeBillingRequest")
            model.objects.create(
                subscription_id=self.subscription.pk, operation="customer", parameters={"private": "fixture"}
            )
            return result

        with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=add_unexpected_request):
            with self.assertRaisesMessage(CommandError, "作成した課金テーブル") as caught:
                self.invoke()
        self.assertNotIn("private", str(caught.exception))
        self.assert_no_batch_changes()

    def test_missing_prerequisite_record_rolls_back_all_four_migrations(self):
        migrate = MigrationExecutor.migrate

        def remove_record(executor, *args, **kwargs):
            result = migrate(executor, *args, **kwargs)
            MigrationRecorder(connection).record_unapplied(*self.batch_targets[1])
            return result

        with patch.object(MigrationExecutor, "migrate", autospec=True, side_effect=remove_record):
            with self.assertRaisesMessage(CommandError, "0065〜0068の適用記録"):
                self.invoke()
        self.assert_no_batch_changes()

    def test_overflow_rejects_the_batch_before_creating_any_billing_table(self):
        skill = self.apps.get_model("accounts", "CharacterSkill7th").objects.filter(pk=self.before["7th"][0]["id"])
        old = self.before["7th"][0]
        try:
            for bonus, other in ((1, 2147483647), (-1, -2147483648)):
                with self.subTest(bonus=bonus, other=other):
                    skill.update(bonus_points=bonus, other_points=other)
                    before = self.current_rows()
                    with self.assertRaisesMessage(CommandError, "整数範囲"):
                        self.invoke()
                    self.assert_no_batch_changes(before)
        finally:
            skill.update(bonus_points=old["bonus_points"], other_points=old["other_points"])

    def test_batch_commit_reply_loss_requires_readback_and_does_not_retry(self):
        commit = connection.commit

        def lose_reply():
            commit()
            raise OperationalError("private-commit-response")

        with patch.object(connection, "commit", side_effect=lose_reply):
            with self.assertRaisesMessage(CommandError, "適用状態を読み取りで再確認") as caught:
                self.invoke()
        self.assertNotIn("取り消しました", str(caught.exception))
        self.assertNotIn("private", str(caught.exception))
        self.assert_batch_applied()
        with self.assertRaisesMessage(CommandError, "0065〜0068"):
            self.invoke()
