"""Public references retain the edition data used by the screen and clipboard."""

import json

# The Node subprocess below uses fixed arguments and no shell.
import subprocess  # nosec B404
from datetime import timedelta
from pathlib import Path

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSheet7th
from accounts.models import CustomUser, Group, GroupMembership, ShareLink
from accounts.share_serializers import SharedCharacterSheetSerializer
from schedules import session_permissions
from schedules.models import TRPGSession


class SharedCharacterReferenceTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username="reference-owner", email="reference@example.test")

    def create_character(self, edition="7th", current_luck=35, max_luck=60):
        character = CharacterSheet.objects.create(user=self.owner, edition=edition, access_scope="link")
        model = CharacterSheet7th if edition == "7th" else CharacterSheet6th
        values = {
            "name": "参照確認用の探索者",
            "name_kana": "さんしょうかくにんようのたんさくしゃ",
            "player_name": "確認用PL",
            "age": 25,
            "str_value": 60 if edition == "7th" else 12,
            "con_value": 60 if edition == "7th" else 12,
            "pow_value": 60 if edition == "7th" else 12,
            "dex_value": 60 if edition == "7th" else 12,
            "app_value": 60 if edition == "7th" else 12,
            "siz_value": 60 if edition == "7th" else 12,
            "int_value": 60 if edition == "7th" else 12,
            "edu_value": 60 if edition == "7th" else 12,
            "notes": "非公開の作業メモ",
        }
        if edition == "7th":
            values.update(luck_starting=50, luck_current=current_luck, luck_max=max_luck)
        model.objects.create(character_sheet=character, **values)
        return character

    def shared_url(self, character):
        return reverse("shared-character-detail", kwargs={"token": str(character.share_token)})

    def test_fixed_reference_returns_kana_for_both_editions(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                character = self.create_character(edition)
                response = self.client.get(self.shared_url(character))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["name_kana"], character.system_data.name_kana)

    def test_seventh_luck_matches_normal_api_including_zero_values(self):
        public_fields = {"damage_bonus", "build", "move_rate", "dodge", "starting_luck", "current_luck", "max_luck"}
        for current, maximum in ((35, 60), (0, 60), (0, 0)):
            with self.subTest(current=current, maximum=maximum):
                character = self.create_character(current_luck=current, max_luck=maximum)
                self.client.force_authenticate(self.owner)
                normal = self.client.get(f"/api/accounts/character-sheets/{character.pk}/")
                self.assertEqual(normal.status_code, 200)
                self.client.force_authenticate(user=None)
                shared = self.client.get(self.shared_url(character))
                self.assertEqual(shared.status_code, 200)
                data = shared.json()["character_7th"]
                self.assertEqual(set(data), public_fields)
                self.assertEqual(data, {key: normal.json()["character_7th"][key] for key in public_fields})
                self.assertEqual(data["current_luck"], current)
                self.assertEqual(data["max_luck"], maximum)
                character.system_data.refresh_from_db()
                self.assertEqual(character.system_data.luck_current, current)
                self.assertEqual(character.system_data.luck_max, maximum)

    def test_issued_share_link_returns_the_same_seventh_reference_data(self):
        character = self.create_character(current_luck=0)
        _, token = ShareLink.issue(
            resource_type=ShareLink.ResourceType.CHARACTER, object_id=character.pk, created_by=self.owner
        )
        response = self.client.get(reverse("shared-character-detail", kwargs={"token": token}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["character_7th"]["current_luck"], 0)
        self.assertEqual(response.json()["name_kana"], character.system_data.name_kana)

    def test_sixth_reference_does_not_gain_seventh_luck_or_change_its_roll(self):
        character = self.create_character("6th")
        response = self.client.get(self.shared_url(character))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["character_7th"])
        self.assertIn("CCB<=60 【幸運】", character.export_ccfolia_format()["data"]["commands"])

    def test_real_shared_api_payload_preserves_luck_in_browser_clipboard_builder(self):
        runner = """
global.window = { location: { origin: 'http://localhost' } };
global.navigator = {};
global.document = {};
require(process.argv[1]);
const character = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
process.stdout.write(window.CCFOLIACharacterCopy.stringifyCharacter(character, '/reference/'));
"""
        script = Path(__file__).resolve().parents[1] / "static/js/ccfolia_character_copy.js"
        for edition, current, maximum in (("7th", 35, 60), ("7th", 0, 60), ("6th", 0, 0)):
            with self.subTest(edition=edition, current=current):
                character = self.create_character(edition, current_luck=current, max_luck=maximum)
                response = self.client.get(self.shared_url(character))
                self.assertEqual(response.status_code, 200)
                # Fixed test script and trusted test PATH; no user command input.
                completed = subprocess.run(  # nosec B603, B607
                    ["node", "-e", runner, script.as_posix()],
                    input=response.content.decode(),
                    capture_output=True,
                    encoding="utf-8",
                    check=True,
                    timeout=15,
                )
                exported = json.loads(completed.stdout)
                self.assertEqual(exported["kind"], "character")
                luck = [item for item in exported["data"]["status"] if item["label"] == "幸運"]
                if edition == "7th":
                    self.assertEqual(luck, [{"label": "幸運", "value": current, "max": maximum}])
                else:
                    self.assertEqual(luck, [])
                    self.assertIn("CCB<=60 【幸運】", exported["data"]["commands"])

    def test_private_scope_rejects_a_previously_valid_reference(self):
        character = self.create_character()
        self.assertEqual(self.client.get(self.shared_url(character)).status_code, 200)
        character.access_scope = "private"
        character.save(update_fields=["access_scope"])
        self.assertEqual(self.client.get(self.shared_url(character)).status_code, 404)

    def test_added_reference_fields_do_not_expose_private_account_or_notes(self):
        character = self.create_character()
        response = self.client.get(self.shared_url(character))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("reference@example.test", response.content.decode())
        self.assertNotIn("非公開の作業メモ", response.content.decode())
        self.assertNotIn("user", response.json())
        self.assertNotIn("secret_ho_info", response.json())

    def test_session_participant_reference_reaches_the_seventh_shared_api(self):
        character = self.create_character(current_luck=0)
        group = Group.objects.create(name="参照試験用グループ", created_by=self.owner)
        GroupMembership.objects.create(group=group, user=self.owner, role="admin")
        session = TRPGSession.objects.create(
            title="参照試験用セッション",
            group=group,
            gm=self.owner,
            created_by=self.owner,
            date=timezone.now() + timedelta(days=1),
            visibility="group",
        )
        session_permissions.create_participant(
            session=session,
            user=self.owner,
            role="player",
            character_sheet=character,
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/schedules/sessions/{session.pk}/detail/")
        reference = reverse("fixed-shared-character-view", kwargs={"share_token": character.share_token})
        self.assertContains(response, f'href="{reference}"')
        self.client.force_authenticate(user=None)
        page = self.client.get(reference)
        self.assertContains(page, f'data-shared-api-url="{self.shared_url(character)}"')
        self.assertEqual(self.client.get(self.shared_url(character)).json()["character_7th"]["current_luck"], 0)

    def test_missing_seventh_detail_has_no_derived_reference_data(self):
        character = CharacterSheet.objects.create(user=self.owner, edition="7th")
        self.assertIsNone(SharedCharacterSheetSerializer().get_character_7th(character))
