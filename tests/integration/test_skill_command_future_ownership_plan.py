"""The original four-migration tool must refuse real extra 0069 work."""

import io

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

from tests.integration import test_skill_other_points_migration as fixtures


class FutureOwnershipPlanRejectionTests(fixtures.SkillOtherPointsMigrationTests):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL historical command rejects the real new migration graph")
        super().setUp()

    def test_real_0069_pending_prevents_0068_only_command_without_any_changes(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertIn(("accounts", "0069_group_ownership_transfer"), [(m.app_label, m.name) for m, _ in plan])
        with self.assertRaisesMessage(CommandError, "未適用の0068だけ"):
            call_command(
                "apply_verified_skill_adjustments",
                apply=True,
                expected_host=connection.settings_dict["HOST"],
                expected_database=connection.settings_dict["NAME"],
                stdout=io.StringIO(),
            )
        for edition, rows in self.before.items():
            self.assertEqual(
                list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values()), rows
            )
        applied = MigrationRecorder(connection).applied_migrations()
        self.assertNotIn(("accounts", "0068_merge_skill_bonus_into_other"), applied)
        self.assertNotIn(("accounts", "0069_group_ownership_transfer"), applied)


class FutureOwnershipBulkPlanRejectionTests(fixtures.SkillOtherPointsMigrationTests):
    old_target = [("accounts", "0064_preserve_character_descendants")]

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL historical command rejects the real new migration graph")
        super().setUp()

    def test_real_0069_pending_prevents_four_migration_command_without_any_changes(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertIn(("accounts", "0069_group_ownership_transfer"), [(m.app_label, m.name) for m, _ in plan])
        with self.assertRaisesMessage(CommandError, "未適用の0065〜0068だけ"):
            call_command(
                "apply_verified_skill_adjustments",
                apply=True,
                include_billing_prerequisites=True,
                expected_host=connection.settings_dict["HOST"],
                expected_database=connection.settings_dict["NAME"],
                stdout=io.StringIO(),
            )
        for edition, rows in self.before.items():
            self.assertEqual(
                list(self.apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values()), rows
            )
        applied = MigrationRecorder(connection).applied_migrations()
        self.assertFalse(
            any(
                app == "accounts" and name.startswith(("0065_", "0066_", "0067_", "0068_", "0069_"))
                for app, name in applied
            )
        )
