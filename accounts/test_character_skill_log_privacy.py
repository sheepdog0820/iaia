"""Unexpected skill-save failures must not disclose private character data."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITransactionTestCase

from accounts.character_models import CharacterSkill6th, CharacterSkill7th
from accounts.test_character_factories import create_6th_character, create_7th_character


class CharacterSkillLogPrivacyTests(APITransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="skill-log-owner", password=None)
        self.client.force_authenticate(self.user)

    def assert_private_failure_is_safe(self, edition):
        factory = create_6th_character if edition == "6th" else create_7th_character
        model = CharacterSkill6th if edition == "6th" else CharacterSkill7th
        sheet, detail = factory(
            user=self.user,
            id=1001 if edition == "6th" else 2001,
            name="未公開探索者の名前",
            edu_value=50 if edition == "7th" else 12,
            int_value=50 if edition == "7th" else 14,
        )
        skill = model.objects.create(
            character_sheet=detail,
            skill_name="未公開の旧技能名",
            base_value=20,
            other_points=10,
        )
        try:
            raise ValueError("synthetic-private-database-detail")
        except ValueError as cause:
            try:
                raise RuntimeError("synthetic-private-save-failure") from cause
            except RuntimeError as failure:
                error = failure

        with patch("accounts.serializers.CharacterSkillSerializer.save", side_effect=error):
            with self.assertLogs("accounts.views.character_views", level="ERROR") as captured:
                with self.assertRaises(RuntimeError) as raised:
                    self.client.patch(
                        f"/accounts/character-sheets/{sheet.pk}/skills/{skill.pk}/",
                        {"skill_name": "未公開の変更後技能名", "other_points": 11},
                        format="json",
                    )

        self.assertIs(raised.exception, error)
        output = "\n".join(captured.output)
        self.assertIn(f"character_sheet_id={sheet.pk} ", output)
        self.assertIn(f"character_detail_id={detail.pk} ", output)
        self.assertIn(f"skill_id={skill.pk} ", output)
        for private_value in (
            detail.name,
            skill.skill_name,
            "未公開の変更後技能名",
            "synthetic-private-save-failure",
            "synthetic-private-database-detail",
        ):
            self.assertNotIn(private_value, output)
        self.assertIn("Character skill update failed", output)
        self.assertIn("RuntimeError", output)
        self.assertTrue(all(record.exc_info is None for record in captured.records))
        skill.refresh_from_db()
        self.assertEqual((skill.skill_name, skill.other_points, skill.current_value), ("未公開の旧技能名", 10, 30))

    def test_6th_skill_failure_omits_private_name_and_exception_chain(self):
        self.assert_private_failure_is_safe("6th")

    def test_7th_skill_failure_omits_private_name_and_exception_chain(self):
        self.assert_private_failure_is_safe("7th")
