from pathlib import Path

from django.test import SimpleTestCase


class DatabasePortabilityTests(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def test_character_registry_migration_uses_backend_aware_field_removal(self):
        migration = (self.ROOT / "accounts" / "migrations" / "0058_minimize_character_sheet_registry.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("migrations.RunPython", migration)
        self.assertIn("schema_editor.remove_field", migration)
        self.assertNotIn("DROP INDEX IF EXISTS", migration)
