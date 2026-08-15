import json
import subprocess
from pathlib import Path

from django.test import TestCase

from accounts.character_models import CharacterExportManager
from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, CharacterSkill7th, CustomUser


class CharacterCcfolliaExportTests(TestCase):
    def test_server_exports_all_equipment_fields_and_weapon_commands(self):
        user = CustomUser.objects.create_user(username="ccfolia-equipment", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="6th")
        detail = CharacterSheet6th.objects.create(
            character_sheet=character,
            name="装備探索者",
            str_value=12,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=13,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=60,
            sanity_max=99,
            sanity_current=60,
        )
        detail.skills.create(skill_name="ライフル", base_value=25, occupation_points=45)
        detail.equipment.create(
            item_type="weapon",
            name="試作ライフル",
            skill_name="ライフル",
            damage="2D6+1",
            base_range="100m",
            attacks_per_round=1,
            ammo=5,
            malfunction_number=98,
            description="試作品",
            quantity=1,
            weight=3.5,
        )
        detail.equipment.create(
            item_type="armor",
            name="防弾ベスト",
            armor_points=3,
            description="胴体用",
            quantity=1,
            weight=2.0,
        )
        detail.equipment.create(
            item_type="item",
            name="予備弾倉",
            description="ライフル用",
            quantity=2,
            weight=0.5,
        )

        exported = character.export_ccfolia_format()
        equipment_by_name = {item["name"]: item for item in exported["equipment"]}

        self.assertEqual(
            equipment_by_name["試作ライフル"],
            {
                "item_type": "weapon",
                "name": "試作ライフル",
                "skill_name": "ライフル",
                "damage": "2D6+1",
                "base_range": "100m",
                "attacks_per_round": 1,
                "ammo": 5,
                "malfunction_number": 98,
                "armor_points": None,
                "description": "試作品",
                "quantity": 1,
                "weight": 3.5,
            },
        )
        self.assertEqual(equipment_by_name["防弾ベスト"]["armor_points"], 3)
        self.assertEqual(equipment_by_name["予備弾倉"]["quantity"], 2)
        commands = exported["data"]["commands"].splitlines()
        self.assertIn("CCB<=70 【試作ライフル】", commands)
        self.assertIn("2D6+1 【試作ライフルダメージ】", commands)

        version_data = CharacterExportManager.export_version_data(character)
        self.assertEqual(version_data["equipment"], exported["equipment"])

    def test_browser_export_includes_equipment_and_seventh_weapon_commands(self):
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
const exported = window.CCFOLIACharacterCopy.buildCharacterClipboard({
    name: '装備探索者',
    edition: '7th',
    str_value: 60,
    con_value: 60,
    pow_value: 60,
    dex_value: 60,
    app_value: 50,
    siz_value: 60,
    int_value: 70,
    edu_value: 70,
    hit_points_current: 12,
    hit_points_max: 12,
    magic_points_current: 12,
    magic_points_max: 12,
    sanity_current: 60,
    sanity_max: 99,
    skills: [{ skill_name: '射撃（拳銃）', current_value: 65 }],
    equipment: [
        {
            item_type: 'weapon',
            name: 'カスタム拳銃',
            skill_name: '射撃（拳銃）',
            damage: '1D10',
            base_range: '15m',
            attacks_per_round: 1,
            ammo: 6,
            malfunction_number: 100,
            armor_points: null,
            description: '調整済み',
            quantity: 1,
            weight: 1.2,
        },
    ],
}, '/characters/7/');
process.stdout.write(JSON.stringify(exported));
"""

        completed = subprocess.run(
            ["node", "-e", runner, script_path.as_posix()],
            check=True,
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        exported = json.loads(completed.stdout)

        self.assertEqual(exported["equipment"][0]["name"], "カスタム拳銃")
        self.assertEqual(exported["equipment"][0]["ammo"], 6)
        commands = exported["data"]["commands"].splitlines()
        self.assertIn("CC<=65 【カスタム拳銃】", commands)
        self.assertIn("1D10 【カスタム拳銃ダメージ】", commands)

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

    def test_browser_export_uses_kobushi_name_damage_bonus_and_current_san_max(self):
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
const exported = window.CCFOLIACharacterCopy.buildCharacterClipboard({
    name: 'Sixth Investigator',
    edition: '6th',
    str_value: 12,
    con_value: 11,
    pow_value: 12,
    dex_value: 13,
    app_value: 14,
    siz_value: 13,
    int_value: 16,
    edu_value: 17,
    hit_points_current: 10,
    hit_points_max: 10,
    magic_points_current: 12,
    magic_points_max: 12,
    sanity_current: 60,
    sanity_max: 99,
    character_6th: { damage_bonus: '+1D4' },
    skills: [{ skill_name: 'こぶし（パンチ）', current_value: 70 }],
}, '/characters/6/');
process.stdout.write(JSON.stringify(exported.data));
"""

        completed = subprocess.run(
            ["node", "-e", runner, script_path.as_posix()],
            check=True,
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        data = json.loads(completed.stdout)
        commands = data["commands"].splitlines()
        san = next(status for status in data["status"] if status["label"] == "SAN")

        self.assertIn("CCB<=70 【こぶし】", commands)
        self.assertFalse(any("こぶし（パンチ）" in command for command in commands))
        self.assertIn("1D3+{DB} 【こぶしダメージ】", commands)
        self.assertIn("1D6+{DB} 【キックダメージ】", commands)
        self.assertIn("1D4+{DB} 【頭突きダメージ】", commands)
        self.assertIn({"label": "DB", "value": "1D4"}, data["params"])
        self.assertEqual(san, {"label": "SAN", "value": 60, "max": 60})

    def test_browser_seventh_export_unifies_melee_names_and_adds_damage_bonus(self):
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
const aliases = [
    '近接戦闘',
    '近接戦闘（格闘）',
    '格闘技',
    'こぶし',
    'こぶし（パンチ）',
    'こぶし(パンチ)',
    'キック',
    '頭突き',
    '組み付き',
    'マーシャルアーツ',
];
const exported = window.CCFOLIACharacterCopy.buildCharacterClipboard({
    name: 'Seventh Investigator',
    edition: '7th',
    str_value: 80,
    con_value: 60,
    pow_value: 60,
    dex_value: 60,
    app_value: 50,
    siz_value: 65,
    int_value: 70,
    edu_value: 70,
    hit_points_current: 12,
    hit_points_max: 12,
    magic_points_current: 12,
    magic_points_max: 12,
    sanity_current: 60,
    sanity_max: 99,
    character_7th: { current_luck: 55, max_luck: 60, damage_bonus: '+1D4' },
    skills: aliases.map((skill_name, index) => ({ skill_name, current_value: 60 + index })),
}, '/characters/7/');
process.stdout.write(JSON.stringify(exported.data));
"""

        completed = subprocess.run(
            ["node", "-e", runner, script_path.as_posix()],
            check=True,
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        data = json.loads(completed.stdout)
        commands = data["commands"].splitlines()
        melee_commands = [command for command in commands if "近接戦闘" in command]

        self.assertEqual(melee_commands, ["CC<=69 【近接戦闘】", "1D3+{DB} 【近接戦闘ダメージ】"])
        self.assertIn({"label": "DB", "value": "+1D4"}, data["params"])
        for alias in ["近接戦闘（格闘）", "格闘技", "こぶし", "キック", "頭突き", "組み付き", "マーシャルアーツ"]:
            self.assertFalse(any(f"【{alias}】" in command for command in commands))

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

    def test_server_export_uses_kobushi_name_damage_bonus_and_current_san_max(self):
        user = CustomUser.objects.create_user(username="ccfolia-sixth-combat", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="6th")
        detail = CharacterSheet6th.objects.create(
            character_sheet=character,
            name="戦闘 探索者",
            str_value=12,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=13,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=60,
            sanity_max=99,
            sanity_current=60,
        )
        detail.skills.create(skill_name="こぶし（パンチ）", base_value=70)

        exported = character.export_ccfolia_format()
        data = exported["data"]
        commands = data["commands"].splitlines()
        san = next(status for status in data["status"] if status["label"] == "SAN")

        self.assertIn("CCB<=70 【こぶし】", commands)
        self.assertFalse(any("こぶし（パンチ）" in command for command in commands))
        self.assertIn("1D3+{DB} 【こぶしダメージ】", commands)
        self.assertIn("1D6+{DB} 【キックダメージ】", commands)
        self.assertIn("1D4+{DB} 【頭突きダメージ】", commands)
        self.assertIn({"label": "DB", "value": "1D4"}, data["params"])
        self.assertEqual(san, {"label": "SAN", "value": 60, "max": 60})
        self.assertIn({"name": "こぶし", "value": 70}, exported["skills"])

    def test_server_seventh_export_unifies_melee_names_and_adds_damage_bonus(self):
        aliases = [
            "近接戦闘",
            "近接戦闘（格闘）",
            "格闘技",
            "こぶし",
            "こぶし（パンチ）",
            "こぶし(パンチ)",
            "キック",
            "頭突き",
            "組み付き",
            "マーシャルアーツ",
        ]
        for alias in aliases:
            with self.subTest(alias=alias):
                self.assertEqual(
                    CharacterExportManager._normalize_ccfolia_skill_name("7th", alias),
                    "近接戦闘",
                )

        user = CustomUser.objects.create_user(username="ccfolia-seventh-combat", password="testpass123")
        character = CharacterSheet.objects.create(user=user, edition="7th")
        detail = CharacterSheet7th.objects.create(
            character_sheet=character,
            name="七版 戦闘",
            str_value=80,
            con_value=60,
            pow_value=60,
            dex_value=60,
            app_value=50,
            siz_value=65,
            int_value=70,
            edu_value=70,
            luck_starting=60,
            luck_current=55,
            luck_max=60,
            hit_points_max=12,
            hit_points_current=12,
            magic_points_max=12,
            magic_points_current=12,
            sanity_starting=60,
            sanity_max=99,
            sanity_current=60,
        )
        detail.skills.create(skill_name="こぶし(パンチ)", base_value=70)

        exported = character.export_ccfolia_format()
        commands = exported["data"]["commands"].splitlines()

        self.assertIn("CC<=70 【近接戦闘】", commands)
        self.assertIn("1D3+{DB} 【近接戦闘ダメージ】", commands)
        self.assertIn({"label": "DB", "value": "+1D4"}, exported["data"]["params"])
        self.assertIn({"name": "近接戦闘", "value": 70}, exported["skills"])

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
