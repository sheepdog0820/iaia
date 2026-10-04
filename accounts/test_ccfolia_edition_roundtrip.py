"""Tableno's own export must identify the edition when imported unchanged."""

import json

# Fixed repository script and Node argv, with no shell or downloaded code.
import subprocess  # nosec B404
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, CustomUser


class CcfoliaEditionRoundtripTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="ccfolia-edition-roundtrip")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def make_character(self, edition):
        registry = CharacterSheet.objects.create(user=self.user, edition=edition)
        model = CharacterSheet7th if edition == "7th" else CharacterSheet6th
        abilities = {
            f"{name}_value": 65 if edition == "7th" else 13
            for name in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")
        }
        detail = model.objects.create(
            character_sheet=registry,
            name=f"版情報の往復検証 {edition}",
            hit_points_current=9,
            hit_points_max=13,
            magic_points_current=8,
            magic_points_max=13,
            sanity_starting=65,
            sanity_current=60,
            sanity_max=99,
            **abilities,
            **({"luck_starting": 70, "luck_current": 55, "luck_max": 70} if edition == "7th" else {}),
        )
        detail.skills.create(skill_name="目星", base_value=25, other_points=40)
        return registry

    def assert_imported(self, payload, original):
        response = self.client.post(reverse("character-sheet-import-ccfolia-json"), {"ccfolia": payload}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        imported = CharacterSheet.objects.get(pk=response.data["id"])
        self.assertEqual(imported.edition, original.edition)
        self.assertEqual(imported.user_id, self.user.pk)
        detail = imported.system_data
        for ability in ("str", "con", "pow", "dex", "app", "siz", "int", "edu"):
            self.assertEqual(getattr(detail, f"{ability}_value"), getattr(original.system_data, f"{ability}_value"))
        self.assertEqual((detail.hit_points_current, detail.hit_points_max), (9, 13))
        self.assertEqual((detail.magic_points_current, detail.magic_points_max), (8, 13))
        self.assertEqual(detail.sanity_current, 60)
        skill = detail.skills.get(skill_name="目星")
        self.assertEqual(skill.base_value + skill.other_points, 65)
        if original.edition == "7th":
            self.assertEqual((detail.luck_current, detail.luck_max), (55, 70))
        self.assertFalse(self.user.is_premium)

    def test_server_export_import_preserves_both_editions_without_request_hint(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                original = self.make_character(edition)
                response = self.client.get(reverse("character-sheet-ccfolia-json", args=[original.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["edition"], edition)
                self.assert_imported(response.data, original)

    def test_browser_export_import_preserves_both_editions_without_request_hint(self):
        script = Path(__file__).resolve().parents[1] / "static/js/ccfolia_character_copy.js"
        runner = """
global.window = { location: { origin: 'https://example.test' } };
global.navigator = {};
global.document = {};
require(process.argv[1]);
const input = JSON.parse(process.argv[2]);
console.log(JSON.stringify(window.CCFOLIACharacterCopy.buildCharacterClipboard(input)));
"""
        for edition in ("6th", "7th", None):
            with self.subTest(edition=edition):
                original = self.make_character(edition or "6th")
                detail = original.system_data
                source = {
                    "edition": edition,
                    "name": detail.name,
                    **{
                        f"{name}_value": getattr(detail, f"{name}_value")
                        for name in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")
                    },
                    "hit_points_current": 9,
                    "hit_points_max": 13,
                    "magic_points_current": 8,
                    "magic_points_max": 13,
                    "sanity_current": 60,
                    "skills": [{"skill_name": "目星", "current_value": 65}],
                    "character_7th": {"current_luck": 55, "max_luck": 70},
                }
                if edition is None:
                    source.pop("edition")
                result = subprocess.run(  # nosec B603 B607
                    ["node", "-e", runner, str(script), json.dumps(source)],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=15,
                )
                payload = json.loads(result.stdout)
                self.assertEqual(payload["edition"], edition or "6th")
                self.assert_imported(payload, original)

    def test_legacy_json_without_metadata_keeps_sixth_edition_default(self):
        # Legacy JSON without metadata retains the importer's sixth-edition default.
        original = self.make_character("6th")
        payload = original.export_ccfolia_format()
        payload.pop("edition", None)
        self.assert_imported(payload, original)
