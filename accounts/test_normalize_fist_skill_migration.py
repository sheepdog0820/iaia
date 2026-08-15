"""Regression coverage for canonical fist-skill names after the edition split."""

import os
import tempfile

from django.conf import settings
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class NormalizeFistSkillMigrationTests(TransactionTestCase):
    migrate_from = [
        ("accounts", "0061_background_removal_jobs"),
        ("scenarios", "0010_scenario_share_token"),
    ]
    migrate_to = [("accounts", "0062_normalize_fist_skill_names")]
    databases = {"default"}

    def setUp(self):
        super().setUp()
        descriptor, self.database_name = tempfile.mkstemp(suffix=".sqlite3")
        os.close(descriptor)
        database_settings = settings.DATABASES["default"].copy()
        database_settings["NAME"] = self.database_name
        self.original_connection = connections["default"]
        self.connection = DatabaseWrapper(database_settings, alias="default")
        connections._connections.default = self.connection
        self.executor = MigrationExecutor(self.connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

    def tearDown(self):
        try:
            self.connection.close()
            if os.path.exists(self.database_name):
                os.unlink(self.database_name)
        finally:
            connections._connections.default = self.original_connection
            super().tearDown()

    def test_old_fist_names_are_normalized_without_duplicate_point_inflation(self):
        User = self.old_apps.get_model("accounts", "CustomUser")
        Registry = self.old_apps.get_model("accounts", "CharacterSheet")
        SixthSheet = self.old_apps.get_model("accounts", "CharacterSheet6th")
        SeventhSheet = self.old_apps.get_model("accounts", "CharacterSheet7th")
        SixthSkill = self.old_apps.get_model("accounts", "CharacterSkill6th")
        SeventhSkill = self.old_apps.get_model("accounts", "CharacterSkill7th")
        SixthEquipment = self.old_apps.get_model("accounts", "CharacterEquipment6th")
        Scenario = self.old_apps.get_model("scenarios", "Scenario")
        ScenarioSkill = self.old_apps.get_model("scenarios", "ScenarioRecommendedSkill")
        ScenarioHandout = self.old_apps.get_model("scenarios", "ScenarioHandout")
        HandoutSkill = self.old_apps.get_model("scenarios", "ScenarioHandoutRecommendedSkill")

        user = User.objects.create(username="fist-normalization", email="fist-normalization@example.com")

        sixth_root = Registry.objects.create(user=user, edition="6th")
        sixth = SixthSheet.objects.create(
            character_sheet=sixth_root,
            name="旧表記のみ",
            recommended_skills=["目星", "こぶし（パンチ）", "こぶし"],
            occupation_skills=["こぶし(パンチ)"],
        )
        SixthSkill.objects.create(
            character_sheet=sixth,
            skill_name="こぶし（パンチ）",
            category="戦闘系",
            base_value=50,
            occupation_points=15,
            current_value=65,
            notes="旧表記",
        )
        SixthEquipment.objects.create(
            character_sheet=sixth,
            item_type="weapon",
            name="素手",
            skill_name="こぶし（パンチ）",
        )

        duplicate_root = Registry.objects.create(user=user, edition="6th")
        duplicate_sheet = SixthSheet.objects.create(character_sheet=duplicate_root, name="新旧重複")
        SixthSkill.objects.create(
            character_sheet=duplicate_sheet,
            skill_name="こぶし",
            category="戦闘系",
            base_value=50,
            occupation_points=20,
            current_value=70,
            notes="新表記",
        )
        SixthSkill.objects.create(
            character_sheet=duplicate_sheet,
            skill_name="こぶし(パンチ)",
            category="戦闘系",
            base_value=50,
            occupation_points=10,
            interest_points=25,
            current_value=85,
            notes="旧表記",
        )

        seventh_root = Registry.objects.create(user=user, edition="7th")
        seventh = SeventhSheet.objects.create(character_sheet=seventh_root, name="7版旧表記")
        SeventhSkill.objects.create(
            character_sheet=seventh,
            skill_name="こぶし（パンチ）",
            category="戦闘系",
            base_value=25,
            current_value=25,
        )
        SeventhSkill.objects.create(
            character_sheet=seventh,
            skill_name="近接戦闘（格闘）",
            category="戦闘系",
            base_value=25,
            occupation_points=10,
            current_value=35,
            notes="旧7版表記",
        )
        SeventhSkill.objects.create(
            character_sheet=seventh,
            skill_name="近接戦闘",
            category="戦闘系",
            base_value=25,
            interest_points=20,
            current_value=45,
            notes="新7版表記",
        )

        sixth_scenario = Scenario.objects.create(
            title="6版シナリオ",
            game_system="coc6",
            recommended_skills="目星, こぶし（パンチ）",
            semi_recommended_skills="こぶし(パンチ)",
            created_by=user,
        )
        ScenarioSkill.objects.create(scenario=sixth_scenario, name="こぶし（パンチ）")
        sixth_handout = ScenarioHandout.objects.create(
            scenario=sixth_scenario,
            title="HO1",
            recommended_skills="こぶし（パンチ）, 回避",
        )
        HandoutSkill.objects.create(handout=sixth_handout, name="こぶし(パンチ)")

        seventh_scenario = Scenario.objects.create(
            title="7版シナリオ",
            game_system="coc7",
            recommended_skills="近接戦闘（格闘）",
            created_by=user,
        )
        ScenarioSkill.objects.create(scenario=seventh_scenario, name="近接戦闘（格闘）")

        self.executor.loader.build_graph()
        self.executor.migrate(self.migrate_to)
        apps = self.executor.loader.project_state(self.migrate_to).apps
        SixthSkill = apps.get_model("accounts", "CharacterSkill6th")
        SeventhSkill = apps.get_model("accounts", "CharacterSkill7th")
        SixthSheet = apps.get_model("accounts", "CharacterSheet6th")
        SixthEquipment = apps.get_model("accounts", "CharacterEquipment6th")
        Scenario = apps.get_model("scenarios", "Scenario")
        ScenarioSkill = apps.get_model("scenarios", "ScenarioRecommendedSkill")
        ScenarioHandout = apps.get_model("scenarios", "ScenarioHandout")
        HandoutSkill = apps.get_model("scenarios", "ScenarioHandoutRecommendedSkill")

        normalized = SixthSkill.objects.get(character_sheet_id=sixth.id)
        self.assertEqual(normalized.skill_name, "こぶし")
        self.assertEqual(normalized.current_value, 65)
        self.assertEqual(SixthEquipment.objects.get(character_sheet_id=sixth.id).skill_name, "こぶし")
        normalized_sheet = SixthSheet.objects.get(pk=sixth.id)
        self.assertEqual(normalized_sheet.recommended_skills, ["目星", "こぶし"])
        self.assertEqual(normalized_sheet.occupation_skills, ["こぶし"])

        merged = SixthSkill.objects.get(character_sheet_id=duplicate_sheet.id)
        self.assertEqual(merged.skill_name, "こぶし")
        self.assertEqual(merged.occupation_points, 20)
        self.assertEqual(merged.interest_points, 25)
        self.assertEqual(merged.current_value, 95)
        self.assertEqual(SixthSkill.objects.filter(character_sheet_id=duplicate_sheet.id).count(), 1)
        self.assertIn("新表記", merged.notes)
        self.assertIn("旧表記", merged.notes)

        normalized_seventh = SeventhSkill.objects.get(character_sheet_id=seventh.id)
        self.assertEqual(normalized_seventh.skill_name, "近接戦闘")
        self.assertEqual(normalized_seventh.occupation_points, 10)
        self.assertEqual(normalized_seventh.interest_points, 20)
        self.assertEqual(normalized_seventh.current_value, 55)
        self.assertEqual(SeventhSkill.objects.filter(character_sheet_id=seventh.id).count(), 1)
        self.assertIn("旧7版表記", normalized_seventh.notes)
        self.assertIn("新7版表記", normalized_seventh.notes)

        migrated_sixth_scenario = Scenario.objects.get(pk=sixth_scenario.id)
        self.assertEqual(migrated_sixth_scenario.recommended_skills, "目星, こぶし")
        self.assertEqual(migrated_sixth_scenario.semi_recommended_skills, "こぶし")
        self.assertEqual(ScenarioSkill.objects.get(scenario_id=sixth_scenario.id).name, "こぶし")
        self.assertEqual(ScenarioHandout.objects.get(pk=sixth_handout.id).recommended_skills, "こぶし, 回避")
        self.assertEqual(HandoutSkill.objects.get(handout_id=sixth_handout.id).name, "こぶし")

        migrated_seventh_scenario = Scenario.objects.get(pk=seventh_scenario.id)
        self.assertEqual(migrated_seventh_scenario.recommended_skills, "近接戦闘")
        self.assertEqual(
            ScenarioSkill.objects.get(scenario_id=seventh_scenario.id).name,
            "近接戦闘",
        )
