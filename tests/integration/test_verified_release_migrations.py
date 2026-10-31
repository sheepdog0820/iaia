"""Apply only the reviewed release plan on synthetic TLS PostgreSQL data."""

import io
import json
import time
from unittest.mock import patch

import psycopg
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import override_settings

from tests.integration.test_skill_other_points_migration import SkillOtherPointsMigrationTests


class VerifiedReleaseMigrationTests(SkillOtherPointsMigrationTests):
    old_target = [("accounts", "0064_preserve_character_descendants")]
    new_target = [("accounts", "0069_group_ownership_transfer")]
    names = [
        "0065_stripe_billing_requests",
        "0066_stripe_invoice_states",
        "0067_billing_email_delivery",
        "0068_merge_skill_bonus_into_other",
        "0069_group_ownership_transfer",
    ]

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL transactional release/ownership verification")
        super().setUp()
        users = self.apps.get_model("accounts", "CustomUser")
        self.owner = users.objects.get(username="migration-fixture")
        self.other = users.objects.create(username="private-other-fixture")
        groups = self.apps.get_model("accounts", "Group")
        members = self.apps.get_model("accounts", "GroupMembership")
        self.groups = []
        for index, role in enumerate(("admin", None, "member")):
            group = groups.objects.create(name=f"private-group-fixture-{index}", created_by_id=self.owner.pk)
            self.groups.append(group)
            if role:
                members.objects.create(group_id=group.pk, user_id=self.owner.pk, role=role)
        members.objects.create(group_id=self.groups[2].pk, user_id=self.other.pk, role="admin")
        self.apps.get_model("accounts", "PremiumSubscription").objects.create(
            user_id=self.owner.pk, subscription_status="active", stripe_customer_id="cus_private_fixture"
        )
        self.apps.get_model("accounts", "PremiumAuditLog").objects.create(
            user_id=self.owner.pk, action="granted", source="stripe", metadata={"private": "synthetic-only"}
        )
        self.original_groups = list(groups.objects.order_by("pk").values())
        self.original_members = list(members.objects.order_by("pk").values())
        self.original_history = list(MigrationRecorder.Migration.objects.order_by("pk").values())
        self.unchanged = {
            name: list(self.apps.get_model("accounts", name).objects.order_by("pk").values())
            for name in ("CustomUser", "PremiumSubscription", "PremiumAuditLog")
        }

    def tearDown(self):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = off")
        super().tearDown()

    def invoke(self, *, start_read_only=True, **overrides):
        options = {
            "apply": True,
            "mode": "billing-skills-ownership",
            "expected_host": connection.settings_dict["HOST"],
            "expected_database": connection.settings_dict["NAME"],
            "expected_group_count": 3,
            "expected_owner_membership_create_count": 1,
            "expected_owner_membership_promote_count": 1,
            "backup_reference": "isolated-fixture-backup-reference",
            "confirm_writers_stopped": True,
        }
        options.update(overrides)
        output = io.StringIO()
        with connection.cursor() as cursor:
            cursor.execute(
                "SET default_transaction_read_only = on"
                if start_read_only
                else "SET default_transaction_read_only = off"
            )
        try:
            call_command("apply_verified_release_migrations", stdout=output, **options)
            with connection.cursor() as cursor:
                cursor.execute("SHOW default_transaction_read_only")
                self.assertEqual(cursor.fetchone()[0], "on")
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = off")
        return json.loads(output.getvalue())

    def assert_no_changes(self):
        self.assertEqual(
            list(self.apps.get_model("accounts", "Group").objects.order_by("pk").values()), self.original_groups
        )
        self.assertEqual(
            list(self.apps.get_model("accounts", "GroupMembership").objects.order_by("pk").values()),
            self.original_members,
        )
        self.assertEqual(list(MigrationRecorder.Migration.objects.order_by("pk").values()), self.original_history)
        for edition in ("6th", "7th"):
            self.assertEqual(
                list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values()),
                self.before[edition],
            )
        self.assertNotIn("accounts_groupownershiptransfer", connection.introspection.table_names())
        for table in ("accounts_stripebillingrequest", "accounts_stripeinvoicestate", "accounts_billingemaildelivery"):
            self.assertNotIn(table, connection.introspection.table_names())
        for name, before in self.unchanged.items():
            self.assertEqual(list(self.apps.get_model("accounts", name).objects.order_by("pk").values()), before)
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, "accounts_group")
            self.assertNotIn("owner_id", {column.name for column in columns})

    def test_full_plan_changes_only_expected_skills_and_owner_memberships(self):
        result = self.invoke()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["applied_migrations"], [f"accounts.{name}" for name in self.names])
        self.assertEqual(
            result["ownership_verified"], {"groups": 3, "memberships_created": 1, "memberships_promoted": 1}
        )
        from accounts.models import Group, GroupMembership

        expected = [dict(row, owner_id=row["created_by_id"]) for row in self.original_groups]
        self.assertEqual(list(Group.objects.order_by("pk").values()), expected)
        for row in self.original_members:
            expected_role = "admin" if row["user_id"] == self.owner.pk else row["role"]
            self.assertEqual(GroupMembership.objects.filter(pk=row["id"]).values().get(), dict(row, role=expected_role))
        self.assertEqual(GroupMembership.objects.count(), len(self.original_members) + 1)
        for edition in ("6th", "7th"):
            actual = list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values())
            self.assertEqual(
                actual,
                [
                    dict(row, bonus_points=0, other_points=row["bonus_points"] + row["other_points"])
                    for row in self.before[edition]
                ],
            )

    def test_count_drift_is_refused_before_any_data_or_schema_change(self):
        with self.assertRaises(CommandError):
            self.invoke(expected_group_count=4)
        self.assert_no_changes()

    def test_missing_operator_acknowledgement_is_refused(self):
        with self.assertRaises(CommandError):
            self.invoke(confirm_writers_stopped=False)
        self.assert_no_changes()

    def test_failure_after_real_five_migrations_rolls_back_without_private_exception(self):
        real_migrate = MigrationExecutor.migrate

        def fail_after_migrate(executor, targets, *args, **kwargs):
            real_migrate(executor, targets, *args, **kwargs)
            raise RuntimeError("private-fixture-exception")

        with patch.object(MigrationExecutor, "migrate", fail_after_migrate):
            with self.assertRaises(CommandError) as error:
                self.invoke()
        self.assertNotIn("private", str(error.exception))
        self.assert_no_changes()

    def test_operator_arguments_do_not_allow_implicit_or_ambiguous_apply(self):
        cases = [
            {"apply": False},
            {"apply": 1},
            {"mode": None},
            {"mode": "ownership-only"},
            {"expected_host": "other.invalid"},
            {"expected_database": "other_database"},
            {"backup_reference": " "},
            {"backup_reference": "x" * 257},
            {"expected_group_count": True},
            {"expected_group_count": -1},
            {"expected_owner_membership_create_count": None},
            {"expected_owner_membership_promote_count": 2**63},
        ]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(CommandError):
                self.invoke(**options)
        self.assert_no_changes()

    def test_bootstrap_must_already_be_read_only(self):
        with self.assertRaisesMessage(CommandError, "READ ONLY"):
            self.invoke(start_read_only=False)
        self.assert_no_changes()

    def test_detailed_sql_logging_is_refused(self):
        with override_settings(DEBUG=True), self.assertRaisesMessage(CommandError, "SQL詳細ログ"):
            self.invoke()
        with (
            patch.object(connection, "force_debug_cursor", True),
            self.assertRaisesMessage(CommandError, "SQL詳細ログ"),
        ):
            self.invoke()
        self.assert_no_changes()

    def test_real_unencrypted_connection_is_refused(self):
        original = dict(connection.settings_dict["OPTIONS"])
        connection.close()
        try:
            connection.settings_dict["OPTIONS"] = dict(original, sslmode="disable")
            with connection.cursor() as cursor:
                cursor.execute("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
                self.assertFalse(cursor.fetchone()[0])
            with self.assertRaisesMessage(CommandError, "TLS"):
                self.invoke()
        finally:
            connection.close()
            connection.settings_dict["OPTIONS"] = original
        self.assert_no_changes()

    def test_inactive_creator_is_not_activated_or_reassigned(self):
        self.apps.get_model("accounts", "CustomUser").objects.filter(pk=self.owner.pk).update(is_active=False)
        self.unchanged["CustomUser"] = list(
            self.apps.get_model("accounts", "CustomUser").objects.order_by("pk").values()
        )
        with self.assertRaisesMessage(CommandError, "作成者不明・無効"):
            self.invoke()
        self.assert_no_changes()

    def test_unknown_history_is_refused_and_preserved(self):
        before_ids = set(MigrationRecorder.Migration.objects.values_list("pk", flat=True))
        MigrationRecorder(connection).record_applied("private_fixture", "0001_unknown")
        created_ids = set(MigrationRecorder.Migration.objects.values_list("pk", flat=True)) - before_ids
        self.original_history = list(MigrationRecorder.Migration.objects.order_by("pk").values())
        try:
            with self.assertRaises(CommandError) as error:
                self.invoke()
            self.assertNotIn("private", str(error.exception))
            self.assert_no_changes()
        finally:
            MigrationRecorder.Migration.objects.filter(pk__in=created_ids).delete()

    def test_existing_duplicate_history_rows_are_preserved_after_success(self):
        row = self.original_history[0]
        MigrationRecorder(connection).record_applied(row["app"], row["name"])
        before = list(MigrationRecorder.Migration.objects.order_by("pk").values())
        self.invoke()
        ids = [row["id"] for row in before]
        self.assertEqual(list(MigrationRecorder.Migration.objects.filter(pk__in=ids).order_by("pk").values()), before)
        self.assertEqual(MigrationRecorder.Migration.objects.count(), len(before) + 5)
        # Django intentionally retains migration history across TransactionTestCase flushes.
        MigrationRecorder.Migration.objects.filter(pk=before[-1]["id"]).delete()

    def test_partial_plan_is_not_silently_completed(self):
        MigrationExecutor(connection).migrate([("accounts", self.names[0])])
        before = list(MigrationRecorder.Migration.objects.order_by("pk").values())
        with self.assertRaisesMessage(CommandError, "5件だけ"):
            self.invoke()
        self.assertEqual(list(MigrationRecorder.Migration.objects.order_by("pk").values()), before)
        self.assertNotIn("accounts_groupownershiptransfer", connection.introspection.table_names())

    def test_active_writer_lock_causes_bounded_refusal(self):
        with psycopg.connect(**connection.get_connection_params(), autocommit=True) as writer:
            writer.execute("BEGIN")
            try:
                writer.execute("LOCK TABLE accounts_group IN ROW EXCLUSIVE MODE")
                start = time.monotonic()
                with self.assertRaises(CommandError):
                    self.invoke()
                self.assertLess(time.monotonic() - start, 6)
            finally:
                writer.execute("ROLLBACK")
        self.assert_no_changes()

    def test_post_migration_billing_drift_rolls_back_all_five(self):
        real_migrate = MigrationExecutor.migrate

        def corrupt_billing(executor, targets, *args, **kwargs):
            real_migrate(executor, targets, *args, **kwargs)
            self.apps.get_model("accounts", "PremiumAuditLog").objects.update(metadata={"private": "changed"})

        with patch.object(MigrationExecutor, "migrate", corrupt_billing):
            with self.assertRaises(CommandError):
                self.invoke()
        self.assert_no_changes()

    def test_unexpected_post_migration_changes_are_all_rolled_back(self):
        real_migrate = MigrationExecutor.migrate
        changes = [
            "UPDATE accounts_characterskill6th SET notes = 'private-fixture-corruption'",
            "UPDATE accounts_characterskill7th SET current_value = current_value + 1",
            "UPDATE accounts_customuser SET is_premium = NOT is_premium",
            "UPDATE accounts_group SET description = 'private-fixture-corruption'",
            "UPDATE accounts_groupmembership SET joined_at = joined_at + interval '1 day'",
            "UPDATE accounts_premiumsubscription SET stripe_customer_id = 'private-fixture-corruption'",
            "UPDATE django_migrations SET applied = applied + interval '1 day' WHERE id = (SELECT min(id) FROM django_migrations)",
            "DELETE FROM django_migrations WHERE app = 'accounts' AND name = '0069_group_ownership_transfer'",
            "ALTER TABLE accounts_group ALTER COLUMN owner_id DROP NOT NULL",
            "INSERT INTO accounts_groupownershiptransfer (group_id, requested_by_id, target_id, created_at, updated_at, expires_at) "
            "SELECT g.id, g.owner_id, u.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 day' "
            "FROM accounts_group g JOIN accounts_customuser u ON u.id <> g.owner_id ORDER BY g.id LIMIT 1",
            "INSERT INTO accounts_groupmembership (group_id, user_id, role, joined_at) "
            "SELECT g.id, u.id, 'member', CURRENT_TIMESTAMP FROM accounts_group g JOIN accounts_customuser u ON u.id <> g.owner_id "
            "WHERE NOT EXISTS (SELECT 1 FROM accounts_groupmembership m WHERE m.group_id = g.id AND m.user_id = u.id) "
            "ORDER BY g.id LIMIT 1",
        ]
        for change in changes:

            def corrupt(executor, targets, *args, **kwargs):
                real_migrate(executor, targets, *args, **kwargs)
                with connection.cursor() as cursor:
                    cursor.execute(change)

            with self.subTest(change=change), patch.object(MigrationExecutor, "migrate", corrupt):
                with self.assertRaises(CommandError) as error:
                    self.invoke()
                self.assertNotIn("private", str(error.exception))
            self.assert_no_changes()

    def test_schema_drift_is_refused_without_repairing_it(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE accounts_group ADD COLUMN private_fixture_extra text")
        try:
            with self.assertRaisesMessage(CommandError, "列・型・NULL制約"):
                self.invoke()
            with connection.cursor() as cursor:
                columns = connection.introspection.get_table_description(cursor, "accounts_group")
                self.assertIn("private_fixture_extra", {column.name for column in columns})
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE accounts_group DROP COLUMN private_fixture_extra")
        self.assert_no_changes()

    def test_integer_overflow_is_refused_before_migrations(self):
        skills = self.apps.get_model("accounts", "CharacterSkill6th")
        original = self.before["6th"][0]
        skills.objects.filter(pk=original["id"]).update(other_points=2147483647)
        self.before["6th"] = list(skills.objects.order_by("pk").values())
        try:
            with self.assertRaisesMessage(CommandError, "整数範囲"):
                self.invoke()
            self.assert_no_changes()
        finally:
            # Restore only the synthetic corruption so test teardown can apply the real migration.
            skills.objects.filter(pk=original["id"]).update(other_points=original["other_points"])

    def test_outer_transaction_is_refused(self):
        with transaction.atomic():
            with self.assertRaisesMessage(CommandError, "既存トランザクション"):
                self.invoke()
        self.assert_no_changes()

    def test_no_membership_adjustment_when_existing_owners_are_admins(self):
        members = self.apps.get_model("accounts", "GroupMembership")
        for group in self.groups:
            members.objects.update_or_create(group_id=group.pk, user_id=self.owner.pk, defaults={"role": "admin"})
        before = list(members.objects.order_by("pk").values())
        result = self.invoke(expected_owner_membership_create_count=0, expected_owner_membership_promote_count=0)
        self.assertEqual(
            result["ownership_verified"], {"groups": 3, "memberships_created": 0, "memberships_promoted": 0}
        )
        self.assertEqual(list(members.objects.order_by("pk").values()), before)

    def test_ambiguous_schema_search_path_is_refused(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA private_fixture_schema")
            cursor.execute("SET search_path = private_fixture_schema, public")
        try:
            with self.assertRaisesMessage(CommandError, "スキーマ"):
                self.invoke()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path = public")
                cursor.execute("DROP SCHEMA private_fixture_schema")
        self.assert_no_changes()

    def test_temporary_schema_is_refused_before_any_migration(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE TEMPORARY TABLE private_fixture_temp (id integer)")
        try:
            with self.assertRaisesMessage(CommandError, "スキーマ"):
                self.invoke()
        finally:
            # Reconnect also removes the session's temporary schema, without touching other sessions.
            connection.close()
        self.assert_no_changes()
