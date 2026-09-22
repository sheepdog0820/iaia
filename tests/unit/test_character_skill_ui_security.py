from pathlib import Path

from django.test import SimpleTestCase


class CharacterSkillUiSecurityTests(SimpleTestCase):
    def test_custom_skill_names_are_escaped_before_html_rendering(self):
        project_root = Path(__file__).resolve().parents[2]

        for edition in ("6th", "7th"):
            script = (project_root / f"static/accounts/js/character{edition}.js").read_text(encoding="utf-8")

            with self.subTest(edition=edition):
                self.assertIn("function escapeCharacterSkillText(value)", script)
                self.assertIn("const safeSkillName = escapeCharacterSkillText(skillName);", script)
                self.assertIn('value="${safeSkillName}"', script)
                self.assertIn('title="${safeSkillName}"', script)
                self.assertIn('aria-label="${safeSkillName} 初期値"', script)
                self.assertIn('aria-label="${safeSkillName} 職業"', script)
                self.assertIn('aria-label="${safeSkillName} 趣味"', script)
                self.assertIn('aria-label="${safeSkillName} その他"', script)
