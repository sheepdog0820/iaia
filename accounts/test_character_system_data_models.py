from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from accounts.models import (
    CharacterEquipment6th,
    CharacterEquipment7th,
    CharacterImage6th,
    CharacterImage7th,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
    CharacterSkill6th,
    CharacterSkill7th,
)
from accounts.services.character_version_service import CharacterVersionService


class CharacterSystemDataModelsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="system-data-user", password="pass")

    def create_registry_character(self, edition):
        return CharacterSheet.objects.create(user=self.user, edition=edition)

    def create_system_data(self, registry, **values):
        model = CharacterSheet6th if registry.edition == "6th" else CharacterSheet7th
        return model.objects.create(character_sheet=registry, **values)

    def system_data_defaults(self, name):
        return {
            "name": name,
            "str_value": 50,
            "con_value": 50,
            "pow_value": 50,
            "dex_value": 50,
            "app_value": 50,
            "siz_value": 50,
            "int_value": 50,
            "edu_value": 50,
            "hit_points_max": 10,
            "hit_points_current": 10,
            "magic_points_max": 10,
            "magic_points_current": 10,
            "sanity_starting": 50,
            "sanity_max": 99,
            "sanity_current": 50,
        }

    def test_each_edition_has_a_dedicated_system_data_record(self):
        seventh_registry = self.create_registry_character("7th")
        sixth_registry = self.create_registry_character("6th")

        seventh = self.create_system_data(seventh_registry, **self.system_data_defaults("7th investigator"))
        sixth = self.create_system_data(sixth_registry, **self.system_data_defaults("6th investigator"))

        self.assertEqual(seventh.character_sheet_id, seventh_registry.id)
        self.assertEqual(sixth.character_sheet_id, sixth_registry.id)
        self.assertEqual(seventh.name, "7th investigator")
        self.assertEqual(sixth.name, "6th investigator")
        self.assertEqual(seventh_registry.system_data.pk, seventh.pk)
        self.assertEqual(sixth_registry.system_data.pk, sixth.pk)

    def test_system_data_is_created_without_parent_character_attributes(self):
        registry = self.create_registry_character("7th")
        seventh = self.create_system_data(registry, **self.system_data_defaults("edition investigator"))

        self.assertEqual(seventh.character_sheet_id, registry.id)
        self.assertEqual(seventh.name, "edition investigator")
        self.assertEqual(seventh.str_value, 50)

    def test_registry_contains_only_registry_fields(self):
        registry_field_names = {field.name for field in CharacterSheet._meta.fields}
        self.assertEqual(
            registry_field_names,
            {
                "id", "user", "edition", "access_scope", "share_token",
                "created_at", "updated_at",
            },
        )
        self.assertEqual({field.name for field in CharacterSheet._meta.many_to_many}, {"allowed_users"})

    def test_legacy_parent_related_tables_are_removed(self):
        table_names = set(connection.introspection.table_names())
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

    def test_related_data_is_stored_only_in_edition_tables(self):
        registry = self.create_registry_character("6th")
        detail = self.create_system_data(registry, **self.system_data_defaults("edition investigator"))
        skill = CharacterSkill6th.objects.create(character_sheet=detail, skill_name="Library Use", base_value=25)
        equipment = CharacterEquipment6th.objects.create(character_sheet=detail, item_type="item", name="Notebook")

        self.assertEqual(skill.character_sheet_id, detail.id)
        self.assertEqual(equipment.character_sheet_id, detail.id)
        skill.delete()
        equipment.delete()

        self.assertFalse(CharacterSkill6th.objects.filter(pk=skill.pk).exists())
        self.assertFalse(CharacterEquipment6th.objects.filter(pk=equipment.pk).exists())

    def test_version_lineage_and_values_are_stored_in_edition_data(self):
        registry = self.create_registry_character("6th")
        original = self.create_system_data(registry, **self.system_data_defaults("original"))

        version = CharacterVersionService.create_version(
            source_character=registry,
            actor=self.user,
            validated_data={"version_note": "session 1", "sanity_current": 42},
        )

        version_data = version.sixth_edition_data
        self.assertEqual(version_data.parent_data_id, original.id)
        self.assertEqual(version_data.version, 2)
        self.assertEqual(version_data.version_note, "session 1")
        self.assertEqual(version_data.sanity_current, 42)

    def test_seventh_edition_related_data_and_history_do_not_mix_with_sixth(self):
        sixth_registry = self.create_registry_character("6th")
        seventh_registry = self.create_registry_character("7th")
        sixth = self.create_system_data(sixth_registry, **self.system_data_defaults("same name"))
        seventh = self.create_system_data(seventh_registry, **self.system_data_defaults("same name"))

        CharacterSkill6th.objects.create(character_sheet=sixth, skill_name="図書館", base_value=25)
        CharacterSkill7th.objects.create(character_sheet=seventh, skill_name="図書館", base_value=20)
        CharacterEquipment6th.objects.create(character_sheet=sixth, item_type="item", name="6th notebook")
        CharacterEquipment7th.objects.create(character_sheet=seventh, item_type="item", name="7th notebook")
        CharacterImage6th.objects.create(character_sheet=sixth, image="6th.png", is_main=True)
        CharacterImage7th.objects.create(character_sheet=seventh, image="7th.png", is_main=True)

        seventh_version = CharacterVersionService.create_version(
            source_character=seventh_registry,
            actor=self.user,
            validated_data={"version_note": "7th session 1"},
        )

        self.assertEqual(CharacterSkill6th.objects.filter(character_sheet=sixth).count(), 1)
        self.assertEqual(CharacterSkill7th.objects.filter(character_sheet=seventh).count(), 1)
        self.assertEqual(CharacterEquipment6th.objects.filter(character_sheet=sixth).count(), 1)
        self.assertEqual(CharacterEquipment7th.objects.filter(character_sheet=seventh).count(), 1)
        self.assertEqual(CharacterImage6th.objects.filter(character_sheet=sixth, is_main=True).count(), 1)
        self.assertEqual(CharacterImage7th.objects.filter(character_sheet=seventh, is_main=True).count(), 1)
        self.assertEqual(seventh_version.edition, "7th")
        self.assertEqual(seventh_version.seventh_edition_data.parent_data_id, seventh.id)
        self.assertEqual(seventh_version.seventh_edition_data.version, 2)
        self.assertFalse(CharacterSheet6th.objects.filter(parent_data=seventh.id).exists())
