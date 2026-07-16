from pathlib import Path

from django.test import TestCase

from accounts.models import CharacterSheet, CharacterSheet6th, CustomUser


class CharacterCcfolliaExportTests(TestCase):
    def test_create_screens_and_payloads_include_name_kana(self):
        root = Path(__file__).resolve().parents[1]
        for edition in ("6th", "7th"):
            template = (root / "templates" / "accounts" / f"character_{edition}_create.html").read_text(encoding="utf-8")
            script = (root / "static" / "accounts" / "js" / f"character{edition}.js").read_text(encoding="utf-8")
            self.assertIn('name="name_kana"', template)
            self.assertIn("name_kana: data.name_kana || ''", script)

    def test_clipboard_export_uses_name_kana_as_its_only_memo_value(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "static" / "js" / "ccfolia_character_copy.js").read_text(encoding="utf-8")

        self.assertIn("memo: character.name_kana ? `読み仮名: ${character.name_kana}` : ''", script)
        self.assertNotIn("character.occupation ? `職業:", script)

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

        self.assertEqual(exported["data"]["memo"], "読み仮名: たかしま しずお")
