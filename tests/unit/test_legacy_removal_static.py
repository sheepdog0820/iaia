from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse

from accounts.character_models import CharacterSheet
from schedules.models import ParticipantIdentity


class LegacyRemovalStaticTests(SimpleTestCase):
    def read_text(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_character_public_state_uses_access_scope_only(self):
        field_names = {field.name for field in CharacterSheet._meta.get_fields()}

        self.assertNotIn("is_public", field_names)
        self.assertIn("access_scope", field_names)

    def test_legacy_character_public_and_edit_routes_are_removed(self):
        for route_name in [
            "character_public_view",
            "character_public_view_6th",
            "character_edit",
            "character_new",
        ]:
            with self.subTest(route_name=route_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(route_name, kwargs={"character_id": 1})

    def test_legacy_session_public_routes_are_removed(self):
        for route_name in ["session_public_view", "public_session_detail"]:
            with self.subTest(route_name=route_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(route_name, kwargs={"share_token": "00000000-0000-0000-0000-000000000000"})

    def test_participant_identity_has_no_legacy_import_fields(self):
        field_names = {field.name for field in ParticipantIdentity._meta.get_fields()}

        self.assertNotIn("legacy_source", field_names)
        self.assertNotIn("legacy_key", field_names)
        self.assertIn("normalized_name", field_names)

    def test_import_trpg_schedule_has_no_legacy_csv_options(self):
        command = self.read_text("schedules/management/commands/import_trpg_schedule.py")

        for marker in [
            "--sessions-csv",
            "--participants-csv",
            "--aliases-csv",
            "legacy_session_id",
            "legacy_source",
            "legacy_key",
        ]:
            self.assertNotIn(marker, command)

    def test_primary_docs_do_not_reference_removed_legacy_surfaces(self):
        self.assertFalse(
            (Path(settings.BASE_DIR) / "docs/specifications/SAFE_SHARE_LINKS_AND_LEGACY_IMPORT.md").exists()
        )
        self.assertTrue((Path(settings.BASE_DIR) / "docs/specifications/SAFE_SHARE_LINKS.md").exists())

        docs = [
            "README.md",
            "docs/specifications/PROJECT_SPECIFICATION.md",
            "docs/specifications/CURRENT_WEBAPP_FEATURES.md",
            "docs/specifications/SAFE_SHARE_LINKS.md",
            "docs/imports/trpg_schedule_2026_pre_import.md",
            "docs/character_sheet/CHARACTER_SHEET_6TH_EDITION_SPECIFICATION.md",
        ]
        removed_markers = [
            "SAFE_SHARE_LINKS_AND_LEGACY_IMPORT.md",
            "--sessions-csv",
            "--participants-csv",
            "--aliases-csv",
            "--allow-duplicates",
            "legacy_session_id",
            "legacy_source",
            "legacy_key",
            "GET /sessions/<uuid:share_token>/view/",
            "GET /s/<uuid:share_token>/",
            "`/sessions/<uuid:share_token>/view/` and `/s/<uuid:share_token>/`",
            "?is_public=",
        ]

        for relative_path in docs:
            with self.subTest(relative_path=relative_path):
                content = self.read_text(relative_path)
                for marker in removed_markers:
                    self.assertNotIn(marker, content)
