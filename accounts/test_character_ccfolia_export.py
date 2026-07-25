import json
import subprocess
from pathlib import Path

from django.test import TestCase

from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, CharacterSkill7th, CustomUser


class CharacterCcfolliaExportTests(TestCase):
    def test_create_screens_and_payloads_include_name_kana(self):
        root = Path(__file__).resolve().parents[1]
        for edition in ("6th", "7th"):
            template = (root / "templates" / "accounts" / f"character_{edition}_create.html").read_text(
                encoding="utf-8"
            )
            script = (root / "static" / "accounts" / "js" / f"character{edition}.js").read_text(encoding="utf-8")
            self.assertIn('name="name_kana"', template)
            self.assertIn("name_kana: data.name_kana || ''", script)

    def test_character_detail_clipboard_export_uses_name_kana_without_a_label(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "static" / "js" / "ccfolia_character_copy.js").read_text(encoding="utf-8")

        self.assertIn("memo: character.name_kana || ''", script)
        self.assertNotIn("character.occupation ? `職業:", script)

    def test_character_detail_displays_name_kana_only_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "accounts" / "character_detail.html").read_text(encoding="utf-8")

        self.assertIn("...(character.name_kana ? [{ label: '読み仮名', value: character.name_kana }] : []),", template)

    def test_session_clipboard_export_uses_name_kana_without_other_memo_fields(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "schedules" / "session_detail.html").read_text(encoding="utf-8")

        self.assertIn("const text = helper.stringifyCharacter(character, detailUrl);", template)
        self.assertNotIn("const memo = character.name_kana || '';", template)
        self.assertNotIn("const memoLines = [", template)

    def test_session_clipboard_export_delegates_to_the_shared_character_exporter(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "schedules" / "session_detail.html").read_text(encoding="utf-8")

        self.assertIn("{% static 'js/ccfolia_character_copy.js' %}", template)
        self.assertIn("const text = helper.stringifyCharacter(character, detailUrl);", template)
        self.assertIn("await helper.copyTextToClipboard(text);", template)
        self.assertNotIn("function collectCcfoliaSkills", template)
        self.assertNotIn("CCFOLIA_COC6_DEFAULT_SKILLS", template)
        self.assertNotIn("CCFOLIA_COC7_DEFAULT_SKILLS", template)

    def test_browser_exports_use_edition_specific_ability_placeholders_and_7th_luck_status(self):
        root = Path(__file__).resolve().parents[1]
        detail_script = (root / "static" / "js" / "ccfolia_character_copy.js").read_text(encoding="utf-8")

        self.assertIn("const isSeventhEdition = character.edition === '7th';", detail_script)
        self.assertIn("const abilityCommandPrefix = isSeventhEdition ? 'CC' : 'CCB';", detail_script)
        self.assertIn("`${abilityCommandPrefix}<={${label}}　【${label}】`", detail_script)
        self.assertIn("label: '幸運'", detail_script)
        self.assertIn("const luckMax = toNumber(seventh.max_luck", detail_script)
        self.assertIn("value: luckCurrent, max: luckMax", detail_script)

    def test_browser_export_generates_edition_correct_commands(self):
        root = Path(__file__).resolve().parents[1]
        script_path = root / "static" / "js" / "ccfolia_character_copy.js"
        runner = """
global.window = {
    location: { origin: 'https://example.test' },
    isSecureContext: true,
};
global.navigator = {};
global.document = {};
require(process.argv[1]);
const base = {
    name: 'Test Investigator',
    str_value: 10,
    con_value: 11,
    pow_value: 12,
    dex_value: 13,
    app_value: 14,
    siz_value: 15,
    int_value: 16,
    edu_value: 17,
    hit_points_current: 10,
    hit_points_max: 10,
    magic_points_current: 12,
    magic_points_max: 12,
    sanity_current: 60,
    sanity_max: 99,
};
const sixth = window.CCFOLIACharacterCopy.buildCharacterClipboard(
    { ...base, edition: '6th', skills: [{ skill_name: 'Custom Skill', current_value: 65 }] },
    '/characters/6/'
);
const seventh = window.CCFOLIACharacterCopy.buildCharacterClipboard(
    {
        ...base,
        edition: '7th',
        skills: [{ skill_name: 'Custom Skill', current_value: 65 }],
        character_7th: { current_luck: 55, max_luck: 60 },
    },
    '/characters/7/'
);
process.stdout.write(JSON.stringify({
    sixth: sixth.data.commands.split('\\n'),
    seventh: seventh.data.commands.split('\\n'),
}));
"""

        completed = subprocess.run(
            ["node", "-e", runner, script_path.as_posix()],
            check=True,
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        commands = json.loads(completed.stdout)

        self.assertIn("CCB<={STR}*5　【STR × 5】", commands["sixth"])
        self.assertIn("CCB<=65 【Custom Skill】", commands["sixth"])
        self.assertIn("CCB<={SAN}　【SANチェック】", commands["sixth"])
        self.assertNotIn("CCB<=60 【SANチェック】", commands["sixth"])
        self.assertIn("CC<={STR}　【STR】", commands["seventh"])
        self.assertIn("CC<=65 【Custom Skill】", commands["seventh"])
        self.assertNotIn("CCB<=65 【Custom Skill】", commands["seventh"])
        self.assertIn("CC<={幸運}　【幸運】", commands["seventh"])
        self.assertIn("CC<={SAN}　【SANチェック】", commands["seventh"])

    def test_export_includes_name_kana_in_character_memo(self):
        user = CustomUser.objects.create_user(username="ccfolia-reader", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="6th")
        CharacterSheet6th.objects.create(
            character_sheet=character,
            name="高島 静雄",
            name_kana="たかしま しずお",
            notes="これはCCFOLIAのメモへ出力しない",
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )

        exported = character.export_ccfolia_format()

        self.assertEqual(exported["data"]["memo"], "たかしま しずお")
        self.assertIn("CCB<={STR}*5　【STR × 5】", exported["data"]["commands"].splitlines())

    def test_export_omits_memo_when_name_kana_is_blank(self):
        user = CustomUser.objects.create_user(username="ccfolia-no-reader", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="6th")
        CharacterSheet6th.objects.create(
            character_sheet=character,
            name="テスト 太郎",
            name_kana="",
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )

        self.assertEqual(character.export_ccfolia_format()["data"]["memo"], "")

    def test_7th_edition_export_uses_cc_ability_placeholders_and_luck_status(self):
        user = CustomUser.objects.create_user(username="ccfolia-7th", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="7th")
        detail = CharacterSheet7th.objects.create(
            character_sheet=character,
            name="テスト 七郎",
            str_value=80,
            con_value=70,
            pow_value=75,
            dex_value=65,
            app_value=55,
            siz_value=65,
            int_value=55,
            edu_value=50,
            luck_starting=60,
            luck_current=55,
            luck_max=60,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )
        CharacterSkill7th.objects.create(
            character_sheet=detail,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
        )

        commands = character.export_ccfolia_format()["data"]["commands"].splitlines()

        self.assertIn("CC<={STR}　【STR】", commands)
        self.assertNotIn("CCB<={STR}　【STR】", commands)
        self.assertIn("CC<=65 【目星】", commands)
        self.assertNotIn("CCB<=65 【目星】", commands)
        luck_status = next(
            status for status in character.export_ccfolia_format()["data"]["status"] if status["label"] == "幸運"
        )
        self.assertEqual(luck_status, {"label": "幸運", "value": 55, "max": 60})
