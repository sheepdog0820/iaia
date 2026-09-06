import importlib
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from accounts.management.commands.create_test_characters import Command


class CleanupFailureReportingTests(SimpleTestCase):
    def test_legacy_cleanup_reports_failure_without_private_details_and_continues(self):
        migration = importlib.import_module("schedules.migrations.0041_remove_sessiontemplate_group_and_more")
        storage = Mock()
        storage.exists.return_value = True
        storage.delete.side_effect = [OSError("private-storage-credential"), None]
        images = [
            SimpleNamespace(image=SimpleNamespace(name=name, storage=storage)) for name in ("private-a", "private-b")
        ]
        apps = Mock()
        apps.get_model.return_value.objects.exclude.return_value.iterator.return_value = images
        with self.assertLogs(migration.__name__, level="WARNING") as captured:
            migration.delete_session_template_image_files(apps, None)
        self.assertEqual(storage.delete.call_count, 2)
        self.assertNotIn("private", " ".join(captured.output))
        self.assertIn("cleanup", " ".join(captured.output))

    def test_sample_image_font_failure_is_reported_and_image_remains_valid(self):
        with patch("PIL.ImageDraw.ImageDraw.text", side_effect=UnicodeError("private-name")):
            with self.assertLogs("accounts.management.commands.create_test_characters", level="WARNING") as captured:
                images = Command().create_additional_images("private-name", count=1)
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0][1].read().startswith(b"\x89PNG"))
        self.assertNotIn("private-name", " ".join(captured.output))

    def test_sample_image_unexpected_error_is_not_swallowed(self):
        with patch("PIL.ImageDraw.ImageDraw.text", side_effect=RuntimeError("drawing failure")):
            with self.assertRaises(RuntimeError):
                Command().create_additional_images("sample", count=1)
