"""Exercise the historical migration graph with data in both edition tables."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SkillOtherPointsMigrationTests(TransactionTestCase):
    old_target = [("accounts", "0067_billing_email_delivery")]
    new_target = [("accounts", "0068_merge_skill_bonus_into_other")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.final_targets = executor.loader.graph.leaf_nodes()
        executor.migrate(self.old_target)
        self.apps = executor.loader.project_state(self.old_target).apps
        user = self.apps.get_model("accounts", "CustomUser").objects.create(username="migration-fixture")
        registry_model = self.apps.get_model("accounts", "CharacterSheet")
        self.before = {}
        for edition in ("6th", "7th"):
            registry = registry_model.objects.create(user=user, edition=edition)
            detail = self.apps.get_model("accounts", f"CharacterSheet{edition}").objects.create(
                character_sheet=registry,
                name="移行試験用の探索者",
            )
            skills = self.apps.get_model("accounts", f"CharacterSkill{edition}")
            for name, bonus, other in (("説得", 30, 5), ("電気修理", 20, 0), ("図書館", 0, 10)):
                skills.objects.create(
                    character_sheet=detail,
                    skill_name=name,
                    base_value=15,
                    occupation_points=25,
                    interest_points=0,
                    bonus_points=bonus,
                    other_points=other,
                    current_value=40 + bonus + other,
                    notes="内訳以外は保持する",
                )
            self.before[edition] = list(skills.objects.order_by("pk").values())

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.final_targets)
        super().tearDown()

    def rows(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        apps = executor.loader.project_state(targets).apps
        return {
            edition: list(apps.get_model("accounts", f"CharacterSkill{edition}").objects.order_by("pk").values())
            for edition in ("6th", "7th")
        }

    def test_forward_reverse_and_reapply_preserve_totals_and_unrelated_columns(self):
        migrated = self.rows(self.new_target)
        for edition, before in self.before.items():
            for old, actual in zip(before, migrated[edition], strict=True):
                with self.subTest(edition=edition, skill=old["skill_name"]):
                    expected = dict(old, bonus_points=0, other_points=old["bonus_points"] + old["other_points"])
                    self.assertEqual(actual, expected)
        self.assertEqual(self.rows(self.old_target), migrated)
        self.assertEqual(self.rows(self.new_target), migrated)
