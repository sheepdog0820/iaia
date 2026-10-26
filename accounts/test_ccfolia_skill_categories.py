import json

# Fixed local Node test runner, no shell.
import subprocess  # nosec B404
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, CustomUser
from accounts.views.character_views import CharacterSheetViewSet

HEADINGS = [
    f"■ {name} ──────────" for name in ("戦闘技能", "探索技能", "行動技能", "交渉技能", "知識技能", "その他・独自")
]


def browser_exports():
    script = Path(__file__).resolve().parents[1] / "static/js/ccfolia_character_copy.js"
    runner = """
global.window = { location: { origin: 'https://example.test' } };
require(process.argv[1]);
const result = {};
for (const edition of ['6th', '7th']) {
    result[edition] = window.CCFOLIACharacterCopy.buildCharacterClipboard({
        edition, str_value: 60, con_value: 60, pow_value: 60, dex_value: 60,
        app_value: 60, siz_value: 60, int_value: 60, edu_value: 60,
        skills: [{ skill_name: '独自の技能', current_value: 42 }],
    }, '/characters/1/');
}
process.stdout.write(JSON.stringify(result));
"""
    # Fixed arguments and trusted Node runtime, no shell.
    completed = subprocess.run(  # nosec B603, B607
        ["node", "-e", runner, script.as_posix()], check=True, capture_output=True, encoding="utf-8"
    )
    return json.loads(completed.stdout)


class CcfoliaBrowserCategoryTests(SimpleTestCase):
    def test_browser_separators_preserve_skill_commands_and_categories_in_both_editions(self):
        for edition, exported in browser_exports().items():
            with self.subTest(edition=edition):
                lines = exported["data"]["commands"].splitlines()
                self.assertEqual([line for line in lines if line in HEADINGS], HEADINGS)
                self.assertEqual(lines[0], "■ 基本判定 ──────────")
                self.assertIn("■ 能力値 ──────────", lines)
                self.assertNotIn("■ 武器・ダメージ ──────────", lines)
                prefix = "CCB" if edition == "6th" else "CC"
                for heading, skill in zip(
                    HEADINGS, ("回避", "応急手当", "機械修理", "言いくるめ", "心理学", "独自の技能")
                ):
                    start = lines.index(heading)
                    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("■ ")), len(lines))
                    self.assertTrue(any(line.endswith(f"【{skill}】") for line in lines[start + 1 : end]))
                self.assertIn(f"{prefix}<=42 【独自の技能】", lines)
                totals = CharacterSheetViewSet._extract_skill_totals({}, exported["data"])
                self.assertEqual(len(totals), 61 if edition == "6th" else 49)
                self.assertEqual(totals["独自の技能"], 42)

    def test_browser_omits_empty_custom_section(self):
        script = Path(__file__).resolve().parents[1] / "static/js/ccfolia_character_copy.js"
        runner = """
global.window = { location: { origin: 'https://example.test' } };
require(process.argv[1]);
process.stdout.write(window.CCFOLIACharacterCopy.buildCharacterClipboard({ edition: '6th' }, '').data.commands);
"""
        # Fixed arguments and trusted Node runtime, no shell.
        completed = subprocess.run(  # nosec B603, B607
            ["node", "-e", runner, script.as_posix()], check=True, capture_output=True, encoding="utf-8"
        )
        self.assertNotIn(HEADINGS[-1], completed.stdout)


class CcfoliaServerCategoryTests(TestCase):
    def test_server_categories_match_browser_and_preserve_importable_values(self):
        user = CustomUser.objects.create_user(username="ccfolia-categories")
        for edition, exported in browser_exports().items():
            with self.subTest(edition=edition):
                registry = CharacterSheet.objects.create(user=user, edition=edition)
                detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
                detail = detail_model.objects.create(
                    character_sheet=registry,
                    name="区切り検証",
                    **{f"{ability}_value": 10 for ability in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")},
                )
                totals = CharacterSheetViewSet._extract_skill_totals({}, exported["data"])
                for name in totals:
                    detail.skills.create(skill_name=name, base_value=42)
                data = registry.export_ccfolia_format()
                lines = data["data"]["commands"].splitlines()
                self.assertEqual([line for line in lines if line in HEADINGS], HEADINGS)
                self.assertEqual(lines[0], "■ 基本判定 ──────────")
                self.assertIn("■ 能力値 ──────────", lines)
                self.assertIn("■ 武器・ダメージ ──────────", lines)
                browser_lines = exported["data"]["commands"].splitlines()
                for name in totals:
                    label = f"【{name}】"
                    server_index = next(i for i, line in enumerate(lines) if line.endswith(label))
                    browser_index = next(i for i, line in enumerate(browser_lines) if line.endswith(label))
                    self.assertEqual(
                        next(line for line in reversed(lines[:server_index]) if line.startswith("■ ")),
                        next(line for line in reversed(browser_lines[:browser_index]) if line.startswith("■ ")),
                    )
                expected = {name: 42 for name in totals}
                self.assertEqual(CharacterSheetViewSet._extract_skill_totals({}, data["data"]), expected)
                self.assertEqual({skill["name"]: skill["value"] for skill in data["skills"]}, expected)

    def test_server_omits_empty_sections(self):
        user = CustomUser.objects.create_user(username="ccfolia-empty-category")
        registry = CharacterSheet.objects.create(user=user, edition="6th")
        detail = CharacterSheet6th.objects.create(
            character_sheet=registry,
            name="区切り検証",
            **{f"{ability}_value": 10 for ability in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")},
        )
        self.assertFalse(any(heading in registry.export_ccfolia_format()["data"]["commands"] for heading in HEADINGS))
        detail.skills.create(skill_name="目星", base_value=70)
        lines = registry.export_ccfolia_format()["data"]["commands"].splitlines()
        self.assertEqual([line for line in lines if line in HEADINGS], [HEADINGS[1]])
        self.assertEqual(lines[lines.index(HEADINGS[1]) + 1], "CCB<=70 【目星】")
