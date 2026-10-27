"""Keep all editable skill adjustments in other_points in both editions."""

from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from rest_framework.test import APITestCase

from .test_character_factories import create_character_with_system_data


class SkillOtherPointsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="skill-adjustments-owner")
        self.client.force_authenticate(self.user)

    def character(self, edition):
        return create_character_with_system_data(
            user=self.user,
            edition=edition,
            name="その他ポイント検証",
            **{
                f"{ability}_value": 10 if edition == "6th" else 50
                for ability in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")
            },
        )

    def legacy_skill(self, detail, **values):
        skill = detail.skills.model(
            character_sheet=detail,
            skill_name="説得",
            base_value=15,
            occupation_points=25,
            bonus_points=30,
            other_points=5,
            current_value=75,
        )
        for key, value in values.items():
            setattr(skill, key, value)
        detail.skills.model.objects.bulk_create([skill])
        return skill

    def test_legacy_bonus_input_is_merged_once_on_save(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                skill = detail.skills.create(skill_name="説得", base_value=15, bonus_points=30, other_points=5)
                for _ in range(2):
                    skill.save()
                    skill.refresh_from_db()
                    self.assertEqual((skill.bonus_points, skill.other_points, skill.current_value), (0, 35, 50))

    def test_partial_save_persists_the_transfer_and_current_value(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                skill = self.legacy_skill(detail)
                skill.notes = "内訳を統一"
                skill.save(update_fields=["notes"])
                skill.refresh_from_db()
                self.assertEqual((skill.bonus_points, skill.other_points, skill.current_value), (0, 35, 75))
                self.assertEqual(skill.notes, "内訳を統一")

    def test_empty_update_fields_remains_a_noop(self):
        _, detail = self.character("6th")
        skill = self.legacy_skill(detail)
        skill.save(update_fields=[], skip_point_validation=True)
        skill.refresh_from_db()
        self.assertEqual((skill.bonus_points, skill.other_points, skill.current_value), (30, 5, 75))

    def test_partial_other_points_edit_updates_the_stored_total(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                skill = detail.skills.create(skill_name="説得", base_value=15, other_points=35)
                skill.other_points = 40
                skill.save(update_fields=["other_points"])
                skill.refresh_from_db()
                self.assertEqual((skill.bonus_points, skill.other_points, skill.current_value), (0, 40, 55))

    def test_negative_legacy_bonus_cannot_cancel_positive_other_points(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                with self.assertRaises(ValidationError):
                    detail.skills.create(skill_name="不正技能", bonus_points=-1, other_points=10)
                self.assertFalse(detail.skills.filter(skill_name="不正技能").exists())

    def test_data_migration_is_idempotent_and_preserves_every_skill_total(self):
        for edition in ("6th", "7th"):
            _, detail = self.character(edition)
            self.legacy_skill(detail)
            self.legacy_skill(detail, skill_name="電気修理", bonus_points=20, other_points=0, current_value=60)
            detail.skills.create(skill_name="未加算技能", base_value=5)
        migration = import_module("accounts.migrations.0068_merge_skill_bonus_into_other")
        editor = SimpleNamespace(connection=connection)
        before = {
            (model_name, row.pk): row.current_value
            for model_name in ("CharacterSkill6th", "CharacterSkill7th")
            for row in apps.get_model("accounts", model_name).objects.all()
        }
        for _ in range(2):
            migration.merge_bonus_into_other(apps, editor)
            for model_name in ("CharacterSkill6th", "CharacterSkill7th"):
                model = apps.get_model("accounts", model_name)
                self.assertFalse(model.objects.exclude(bonus_points=0).exists())
                for row in model.objects.all():
                    self.assertEqual(row.current_value, before[model_name, row.pk])
                    self.assertEqual(row.other_points, {"説得": 35, "電気修理": 20, "未加算技能": 0}[row.skill_name])

    def test_other_points_survive_editor_save_and_can_be_changed(self):
        migration = import_module("accounts.migrations.0068_merge_skill_bonus_into_other")
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                skill = self.legacy_skill(detail)
                migration.merge_bonus_into_other(apps, SimpleNamespace(connection=connection))
                response = self.client.get(f"/accounts/character-sheets/{registry.pk}/skills/")
                self.assertEqual(response.status_code, 200)
                payload = response.data[0]
                self.assertEqual(
                    (payload["bonus_points"], payload["other_points"], payload["current_value"]), (0, 35, 75)
                )
                url = f"/accounts/character-sheets/{registry.pk}/skills/{skill.pk}/"
                for expected_total in (75, 75):
                    saved = self.client.patch(url, {"other_points": payload["other_points"]}, format="json")
                    self.assertEqual(saved.status_code, 200)
                    self.assertEqual(saved.data["current_value"], expected_total)
                saved = self.client.patch(url, {"other_points": 40}, format="json")
                self.assertEqual(saved.status_code, 200)
                skill.refresh_from_db()
                self.assertEqual((skill.bonus_points, skill.other_points, skill.current_value), (0, 40, 80))
