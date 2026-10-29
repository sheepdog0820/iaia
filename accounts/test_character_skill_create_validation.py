"""The live nested skill POST must return model input errors as HTTP 400."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import resolve
from rest_framework.test import APITransactionTestCase

from accounts.test_character_factories import create_character_with_system_data


class CharacterSkillCreateValidationTests(APITransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="skill-create-owner", password=None)
        self.client.force_authenticate(self.user)
        self.client.raise_request_exception = False

    def character(self, edition, **values):
        return create_character_with_system_data(
            user=self.user,
            edition=edition,
            name="技能作成の検証用探索者",
            edu_value=50 if edition == "7th" else 12,
            int_value=50 if edition == "7th" else 14,
            **values,
        )

    def assert_rejected(self, edition, values, field, message):
        sheet, detail = self.character(edition)
        url = f"/api/accounts/character-sheets/{sheet.pk}/skills/"
        self.assertEqual(resolve(url).func.actions["post"], "create")
        response = self.client.post(url, {"skill_name": "検証技能", "base_value": 20, **values}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(field, response.data)
        self.assertIn(message, str(response.data[field]))
        self.assertFalse(detail.skills.exists())

    def test_negative_points_are_field_validation_errors_in_both_editions(self):
        for edition in ("6th", "7th"):
            for field in ("base_value", "occupation_points", "interest_points", "other_points"):
                with self.subTest(edition=edition, field=field):
                    self.assert_rejected(edition, {field: -1}, field, "0以上")

    def test_occupation_budget_excess_returns_actionable_error_in_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                self.assert_rejected(
                    edition,
                    {"occupation_points": detail.calculate_occupation_points() + 1},
                    "occupation_points",
                    "職業技能ポイント",
                )

    def test_interest_budget_excess_returns_actionable_error_in_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                _, detail = self.character(edition)
                self.assert_rejected(
                    edition,
                    {"interest_points": detail.calculate_hobby_points() + 1},
                    "interest_points",
                    "趣味技能ポイント",
                )

    def test_total_above_999_is_rejected_without_saving_in_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                self.assert_rejected(edition, {"base_value": 999, "other_points": 1}, "current_value", "999")

    def test_existing_allocations_are_included_in_the_creation_budget(self):
        for edition in ("6th", "7th"):
            for field, calculate in (
                ("occupation_points", "calculate_occupation_points"),
                ("interest_points", "calculate_hobby_points"),
            ):
                with self.subTest(edition=edition, field=field):
                    sheet, detail = self.character(edition)
                    existing = detail.skills.create(skill_name="既存技能", base_value=5, **{field: 20})
                    response = self.client.post(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                        {"skill_name": "追加を拒否する技能", "base_value": 5, field: getattr(detail, calculate)() - 19},
                        format="json",
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("合計", str(response.data[field]))
                    existing.refresh_from_db()
                    self.assertEqual(getattr(existing, field), 20)
                    self.assertEqual(detail.skills.count(), 1)

    def test_validation_after_a_write_rolls_back_and_preserves_message_list(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition)
                model = detail.skills.model
                original_save = model.save

                def fail_after_save(instance, *args, **kwargs):
                    original_save(instance, *args, **kwargs)
                    raise ValidationError(["技能の入力を確認してください。"])

                with patch.object(model, "save", fail_after_save):
                    response = self.client.post(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                        {"skill_name": "保存を取り消す技能", "base_value": 20},
                        format="json",
                    )
                self.assertFalse(detail.skills.exists())
                self.assertEqual(response.status_code, 400)
                self.assertEqual(list(response.data), ["技能の入力を確認してください。"])

    def test_valid_creation_preserves_edition_and_total(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition)
                response = self.client.post(
                    f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                    {
                        "skill_name": "正常な技能",
                        "base_value": 20,
                        "occupation_points": 10,
                        "interest_points": 5,
                        "other_points": 3,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 201)
                saved = detail.skills.get(pk=response.data["id"])
                self.assertEqual(saved.character_sheet_id, detail.pk)
                self.assertEqual((saved.other_points, saved.current_value), (3, 38))

    def test_foreign_public_character_is_still_not_writable(self):
        other = get_user_model().objects.create_user(username="skill-create-stranger", password=None)
        self.client.force_authenticate(other)
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition, access_scope="public")
                response = self.client.post(
                    f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                    {"skill_name": "作成を拒否する技能", "base_value": 20},
                    format="json",
                )
                self.assertEqual(response.status_code, 404)
                self.assertFalse(detail.skills.exists())

    def test_unexpected_storage_failure_still_returns_server_error(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition)
                with patch.object(detail.skills.model, "save", side_effect=RuntimeError("synthetic-private-storage")):
                    response = self.client.post(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                        {"skill_name": "保存失敗の技能", "base_value": 20},
                        format="json",
                    )
                self.assertEqual(response.status_code, 500)
                self.assertNotIn("synthetic-private-storage", response.content.decode())
                self.assertFalse(detail.skills.exists())

    def test_unexpected_failure_after_a_write_does_not_leave_partial_creation(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition)
                model = detail.skills.model
                original_save = model.save

                def fail_after_save(instance, *args, **kwargs):
                    original_save(instance, *args, **kwargs)
                    raise RuntimeError("synthetic-private-after-save")

                with patch.object(model, "save", fail_after_save):
                    response = self.client.post(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/",
                        {"skill_name": "途中失敗の技能", "base_value": 20},
                        format="json",
                    )
                self.assertEqual(response.status_code, 500)
                self.assertNotIn("synthetic-private-after-save", response.content.decode())
                self.assertFalse(detail.skills.exists())
