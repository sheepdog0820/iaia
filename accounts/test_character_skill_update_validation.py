from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSkill7th
from accounts.test_character_factories import create_7th_character


class CharacterSkillUpdateValidationTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="skill-update-user", password="password")
        self.client.force_authenticate(self.user)
        self.sheet, self.detail = create_7th_character(
            user=self.user,
            name="技能更新検証",
            edu_value=50,
            dex_value=90,
            int_value=50,
            occupation_point_method="edu4",
        )
        self.skill = CharacterSkill7th.objects.create(
            character_sheet=self.detail,
            skill_name="目星",
            base_value=25,
            occupation_points=200,
        )

    def test_skill_update_returns_field_validation_error_when_occupation_points_exceed_limit(self):
        response = self.client.patch(
            f"/accounts/character-sheets/{self.sheet.id}/skills/{self.skill.id}/",
            {"occupation_points": 201},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("occupation_points", response.data)
        self.assertIn("職業技能ポイントの合計が上限を超えています", response.data["occupation_points"][0])

    def test_switching_to_edu_and_dex_method_allows_the_new_skill_budget(self):
        response = self.client.patch(
            f"/accounts/character-sheets/{self.sheet.id}/",
            {"occupation_point_method": "edu2dex2"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            f"/accounts/character-sheets/{self.sheet.id}/skills/{self.skill.id}/",
            {"occupation_points": 280},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["occupation_points"], 280)

    def test_create_7th_edition_returns_actionable_validation_error_for_invalid_skill_points(self):
        response = self.client.post(
            "/accounts/character-sheets/create_7th_edition/",
            {
                "name": "ポイント超過",
                "age": 25,
                "str_value": 50,
                "con_value": 50,
                "pow_value": 50,
                "dex_value": 90,
                "app_value": 50,
                "siz_value": 50,
                "int_value": 50,
                "edu_value": 50,
                "occupation_point_method": "edu2dex2",
                "skills": [
                    {
                        "skill_name": "目星",
                        "base_value": 25,
                        "occupation_points": 281,
                        "interest_points": 0,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("occupation_points", response.data)
        self.assertIn("職業技能ポイント", response.data["occupation_points"][0])
