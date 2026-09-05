from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, OperationalError
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from accounts.test_character_factories import create_character_with_system_data
from accounts.views.character_views import CharacterSkillViewSet


class SkillBulkAtomicityTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="bulk-owner")
        self.client.force_authenticate(self.user)

    def character(self, edition):
        return create_character_with_system_data(
            user=self.user, edition=edition, name="一括技能テスト", edu_value=10, int_value=10
        )

    def submit(self, registry, skills):
        return self.client.patch(
            f"/api/accounts/character-sheets/{registry.pk}/skills/bulk_update/", {"skills": skills}, format="json"
        )

    def test_invalid_later_skill_rolls_back_earlier_update_in_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                skill = detail.skills.create(skill_name="既存技能", base_value=5)
                response = self.submit(
                    registry, [{"id": skill.pk, "base_value": 15}, {"skill_name": "不正技能", "base_value": -1}]
                )
                self.assertEqual(response.status_code, 400)
                skill.refresh_from_db()
                self.assertEqual(skill.base_value, 5)
                self.assertFalse(detail.skills.filter(skill_name="不正技能").exists())

    def test_unknown_skill_is_not_reported_as_success(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                response = self.submit(
                    registry, [{"skill_name": "先行作成", "base_value": 5}, {"id": 99999999, "base_value": 10}]
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(detail.skills.filter(skill_name="先行作成").exists())

    def test_valid_update_and_creation_are_returned_and_persisted(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                skill = detail.skills.create(skill_name="既存技能", base_value=5)
                response = self.submit(
                    registry, [{"id": skill.pk, "base_value": 15}, {"skill_name": "新規技能", "base_value": 10}]
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data), 2)
                skill.refresh_from_db()
                self.assertEqual(skill.current_value, 15)
                self.assertEqual(detail.skills.get(skill_name="新規技能").current_value, 10)

    def test_full_budget_can_be_redistributed_between_skills(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                occupation = detail.calculate_occupation_points()
                interest = detail.calculate_hobby_points()
                self.assertGreater(occupation, 0)
                self.assertGreater(interest, 0)
                first = detail.skills.create(skill_name="職業割当", occupation_points=occupation)
                second = detail.skills.create(skill_name="趣味割当", interest_points=interest)
                response = self.submit(
                    registry,
                    [
                        {"id": first.pk, "occupation_points": 0, "interest_points": interest},
                        {"id": second.pk, "occupation_points": occupation, "interest_points": 0},
                    ],
                )
                self.assertEqual(response.status_code, 200)
                first.refresh_from_db()
                second.refresh_from_db()
                self.assertEqual((first.occupation_points, first.interest_points), (0, interest))
                self.assertEqual((second.occupation_points, second.interest_points), (occupation, 0))

    def test_creation_can_use_points_released_by_a_later_update(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = self.character(edition)
                quota = detail.calculate_occupation_points()
                skill = detail.skills.create(skill_name="既存技能", occupation_points=quota, interest_points=3)
                response = self.submit(
                    registry,
                    [
                        {"skill_name": "新規技能", "occupation_points": 5},
                        {"id": skill.pk, "occupation_points": quota - 5},
                    ],
                )
                self.assertEqual(response.status_code, 200)
                skill.refresh_from_db()
                self.assertEqual((skill.occupation_points, skill.interest_points), (quota - 5, 3))
                self.assertEqual(detail.skills.get(skill_name="新規技能").occupation_points, 5)

    def test_final_total_over_budget_rolls_back_including_untouched_skills(self):
        for edition in ("6th", "7th"):
            for field, quota_method in (
                ("occupation_points", "calculate_occupation_points"),
                ("interest_points", "calculate_hobby_points"),
            ):
                with self.subTest(edition=edition, field=field):
                    registry, detail = self.character(edition)
                    quota = getattr(detail, quota_method)()
                    untouched = detail.skills.create(skill_name="未編集技能", **{field: quota - 5})
                    skill = detail.skills.create(skill_name="編集技能", **{field: 5})
                    response = self.submit(
                        registry,
                        [
                            {"id": skill.pk, field: 4},
                            {"skill_name": "上限超過技能", field: 2},
                        ],
                    )
                    self.assertEqual(response.status_code, 400)
                    skill.refresh_from_db()
                    untouched.refresh_from_db()
                    self.assertEqual(getattr(skill, field), 5)
                    self.assertEqual(getattr(untouched, field), quota - 5)
                    self.assertFalse(detail.skills.filter(skill_name="上限超過技能").exists())

    def test_repeated_skill_id_keeps_prior_patch_and_omitted_points(self):
        registry, detail = self.character("6th")
        skill = detail.skills.create(skill_name="既存技能", occupation_points=5, interest_points=3)
        response = self.submit(registry, [{"id": skill.pk, "base_value": 10}, {"id": str(skill.pk), "bonus_points": 2}])
        self.assertEqual(response.status_code, 200)
        skill.refresh_from_db()
        self.assertEqual((skill.occupation_points, skill.interest_points, skill.current_value), (5, 3, 20))

    def test_malformed_payloads_are_rejected_without_changes(self):
        registry, detail = self.character("6th")
        for payload in (None, {}, "bad", [], [None], [{"skill_name": " "}], [{"id": True}], [{"id": -1}]):
            with self.subTest(payload=payload):
                response = self.submit(registry, payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(detail.skills.exists())

    def test_missing_parent_is_rejected(self):
        request = APIRequestFactory().patch(
            "/skills/bulk_update/", {"skills": [{"skill_name": "新規技能"}]}, format="json"
        )
        force_authenticate(request, self.user)
        response = CharacterSkillViewSet.as_view({"patch": "bulk_update"})(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "キャラクターを指定してください。")

    def test_foreign_character_and_skill_cannot_be_changed(self):
        registry, detail = self.character("6th")
        other = get_user_model().objects.create_user(username="other-owner")
        other_registry, other_detail = create_character_with_system_data(user=other, name="別の探索者")
        other_skill = other_detail.skills.create(skill_name="別の技能", base_value=5)
        self.assertEqual(self.submit(other_registry, [{"id": other_skill.pk, "base_value": 15}]).status_code, 404)
        self.assertEqual(self.submit(registry, [{"id": other_skill.pk, "base_value": 15}]).status_code, 400)
        other_skill.refresh_from_db()
        self.assertEqual(other_skill.base_value, 5)
        self.assertFalse(detail.skills.exists())

    def test_storage_failure_rolls_back_and_does_not_expose_exception(self):
        for edition in ("6th", "7th"):
            for exception, expected in (
                (IntegrityError("secret fixture"), 503),
                (OperationalError("secret fixture"), 503),
                (RuntimeError("secret fixture"), 500),
            ):
                with self.subTest(edition=edition, exception=type(exception).__name__):
                    registry, detail = self.character(edition)
                    skill = detail.skills.create(skill_name="既存技能", base_value=5)
                    with patch.object(detail.skills.model, "create_custom_skill", side_effect=exception):
                        with self.assertLogs("accounts.views.character_views", level="WARNING") as logs:
                            response = self.submit(
                                registry, [{"id": skill.pk, "base_value": 15}, {"skill_name": "新規技能"}]
                            )
                    self.assertEqual(response.status_code, expected)
                    self.assertNotIn("secret fixture", str(response.data))
                    self.assertNotIn("secret fixture", str(logs.output))
                    skill.refresh_from_db()
                    self.assertEqual(skill.base_value, 5)
