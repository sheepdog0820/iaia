"""Regression coverage for bonus points in character detail skill breakdowns."""

import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from .character_models import CharacterSkill6th, CharacterSkill7th
from .serializers import CharacterSkillSerializer
from .test_character_factories import create_character_with_system_data


class CharacterSkillBonusDisplayAPITests(APITestCase):
    def test_detail_exposes_bonus_separately_without_changing_totals(self):
        user = get_user_model().objects.create_user(username="skill-bonus-display")
        self.client.force_authenticate(user)
        for edition, skill_model in (("6th", CharacterSkill6th), ("7th", CharacterSkill7th)):
            with self.subTest(edition=edition):
                registry, detail = create_character_with_system_data(
                    user=user,
                    edition=edition,
                    name="技能表示テスト",
                    **{
                        f"{ability}_value": 10 if edition == "6th" else 50
                        for ability in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")
                    },
                )
                for name, base, occupation, bonus in (
                    ("重機械操作", 1, 40, 30),
                    ("電気修理", 10, 35, 20),
                    ("説得", 15, 25, 30),
                    ("図書館", 25, 20, 0),
                ):
                    skill_model.objects.create(
                        character_sheet=detail,
                        skill_name=name,
                        base_value=base,
                        occupation_points=occupation,
                        bonus_points=bonus,
                    )

                response = self.client.get(f"/api/accounts/character-sheets/{registry.pk}/")
                self.assertEqual(response.status_code, 200)
                skills = {skill["skill_name"]: skill for skill in response.data["skills"]}
                for name, bonus, total in (
                    ("重機械操作", 30, 71),
                    ("電気修理", 20, 65),
                    ("説得", 30, 70),
                    ("図書館", 0, 45),
                ):
                    self.assertEqual(skills[name].get("bonus_points"), bonus)
                    self.assertEqual(skills[name]["other_points"], 0)
                    self.assertEqual(skills[name]["current_value"], total)


class CharacterSkillBonusRenderingTests(SimpleTestCase):
    def test_bonus_remains_read_only_in_the_skill_serializer(self):
        serializer = CharacterSkillSerializer(data={"skill_name": "目星", "bonus_points": 30})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("bonus_points", serializer.validated_data)

    @skipUnless(shutil.which("node"), "Node.js is required for skill rendering checks")
    def test_rendered_skill_breakdowns(self):
        script = Path(settings.BASE_DIR) / "tests/unit/character_detail_skills.test.js"
        result = subprocess.run(
            [shutil.which("node"), "--test", str(script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
