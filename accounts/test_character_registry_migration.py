"""Regression coverage for the one-way registry-minimising migration."""

import os
import tempfile

from django.conf import settings
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CharacterRegistryMinimizationMigrationTests(TransactionTestCase):
    """Run the migration against a genuinely pre-split SQLite database.

    The production migration is deliberately forward-only, so this uses an
    independent database rather than attempting to reverse it on Django's test
    database.  That also verifies the actual SQLite ``DROP COLUMN`` operations.
    """

    migrate_from = ("accounts", "0054_remove_cross_edition_basic_skills")
    migrate_to = ("accounts", "0058_minimize_character_sheet_registry")
    databases = {"default"}

    def setUp(self):
        super().setUp()
        descriptor, self.database_name = tempfile.mkstemp(suffix=".sqlite3")
        os.close(descriptor)
        database_settings = settings.DATABASES["default"].copy()
        database_settings["NAME"] = self.database_name
        self.original_connection = connections["default"]
        self.connection = DatabaseWrapper(database_settings, alias="default")
        # Schema editors use transaction.get_connection(self.connection.alias).
        # Temporarily make this independent database the default connection so
        # those internal transactions are scoped to the same database.
        connections._connections.default = self.connection
        self.executor = MigrationExecutor(self.connection)
        self.executor.migrate([self.migrate_from])
        self.old_apps = self.executor.loader.project_state([self.migrate_from]).apps

    def tearDown(self):
        try:
            self.connection.close()
            if os.path.exists(self.database_name):
                os.unlink(self.database_name)
        finally:
            connections._connections.default = self.original_connection
            super().tearDown()

    def test_legacy_data_is_moved_before_the_registry_columns_are_dropped(self):
        User = self.old_apps.get_model("accounts", "CustomUser")
        Sheet = self.old_apps.get_model("accounts", "CharacterSheet")
        Skill = self.old_apps.get_model("accounts", "CharacterSkill")
        Equipment = self.old_apps.get_model("accounts", "CharacterEquipment")

        user = User.objects.create(username="legacy-character", email="legacy@example.com")
        legacy_stats = {
            "str_value": 12,
            "con_value": 13,
            "pow_value": 14,
            "dex_value": 15,
            "app_value": 16,
            "siz_value": 17,
            "int_value": 18,
            "edu_value": 19,
            "hit_points_max": 15,
            "hit_points_current": 15,
            "magic_points_max": 14,
            "magic_points_current": 14,
            "sanity_starting": 70,
            "sanity_max": 99,
            "sanity_current": 70,
        }
        root = Sheet.objects.create(
            user=user,
            edition="6th",
            name="旧6版ルート",
            player_name="探索者",
            age=27,
            occupation="私立探偵",
            **{
                **legacy_stats,
                "hit_points_current": 11,
                "magic_points_current": 9,
                "sanity_max": 88,
                "sanity_current": 61,
            },
            notes="旧メモ",
            is_active=False,
            session_count=3,
            ccfolia_sync_enabled=True,
            ccfolia_character_id="ccfolia-root",
            version=1,
            version_note="初期版",
        )
        version = Sheet.objects.create(
            user=user,
            edition="6th",
            name="旧6版履歴",
            parent_sheet=root,
            version=2,
            version_note="第2版",
            **legacy_stats,
        )
        seventh = Sheet.objects.create(
            user=user,
            edition="7th",
            name="旧7版",
            age=31,
            occupation="考古学者",
            **{**legacy_stats, "pow_value": 60},
            session_count=5,
            ccfolia_character_id="ccfolia-7th",
            version=1,
        )
        skill = Skill.objects.create(
            character_sheet=root,
            skill_name="目星",
            category="探索",
            base_value=25,
            current_value=65,
        )
        equipment = Equipment.objects.create(
            character_sheet=root,
            item_type="weapon",
            name="拳銃",
            quantity=1,
        )

        self.executor.loader.build_graph()
        self.executor.migrate([self.migrate_to])
        apps = self.executor.loader.project_state([self.migrate_to]).apps
        NewSheet = apps.get_model("accounts", "CharacterSheet")
        Sixth = apps.get_model("accounts", "CharacterSheet6th")
        Seventh = apps.get_model("accounts", "CharacterSheet7th")
        SixthSkill = apps.get_model("accounts", "CharacterSkill6th")
        SixthEquipment = apps.get_model("accounts", "CharacterEquipment6th")

        root_detail = Sixth.objects.get(character_sheet_id=root.id)
        self.assertEqual(root_detail.name, "旧6版ルート")
        self.assertEqual(root_detail.player_name, "探索者")
        self.assertEqual(root_detail.hit_points_current, 11)
        self.assertEqual(root_detail.session_count, 3)
        self.assertFalse(root_detail.is_active)
        self.assertTrue(root_detail.ccfolia_sync_enabled)
        self.assertEqual(root_detail.ccfolia_character_id, "ccfolia-root")
        self.assertEqual(root_detail.version_note, "初期版")

        self.assertEqual(Sixth.objects.get(character_sheet_id=version.id).parent_data_id, root_detail.id)
        self.assertEqual(Seventh.objects.get(character_sheet_id=seventh.id).name, "旧7版")
        self.assertEqual(Seventh.objects.get(character_sheet_id=seventh.id).session_count, 5)
        self.assertEqual(SixthSkill.objects.get(legacy_skill_id=skill.id).current_value, 65)
        self.assertEqual(SixthEquipment.objects.get(legacy_equipment_id=equipment.id).name, "拳銃")

        self.assertEqual(
            {field.name for field in NewSheet._meta.fields},
            {"id", "user", "edition", "access_scope", "share_token", "created_at", "updated_at"},
        )
        column_names = {
            column.name for column in self.connection.introspection.get_table_description(
                self.connection.cursor(), NewSheet._meta.db_table
            )
        }
        self.assertNotIn("name", column_names)
        self.assertNotIn("parent_sheet_id", column_names)
        self.assertNotIn("ccfolia_character_id", column_names)

        # The next one-way migration removes the copied-from legacy related
        # tables only after the edition-specific rows above have been proven.
        self.executor.loader.build_graph()
        self.executor.migrate([("accounts", "0059_remove_legacy_character_related_tables")])
        table_names = set(self.connection.introspection.table_names())
        self.assertFalse(
            {"accounts_characterskill", "accounts_characterequipment", "accounts_characterimage"} & table_names
        )
        self.assertTrue(
            {
                "accounts_characterskill6th", "accounts_characterskill7th",
                "accounts_characterequipment6th", "accounts_characterequipment7th",
                "accounts_characterimage6th", "accounts_characterimage7th",
            }.issubset(table_names)
        )
