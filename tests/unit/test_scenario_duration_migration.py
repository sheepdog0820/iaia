from importlib import import_module
from unittest.mock import MagicMock, call

from django.db import migrations
from django.test import SimpleTestCase


class ScenarioDurationMigrationTests(SimpleTestCase):
    def setUp(self):
        self.migration = import_module("scenarios.migrations.0011_migrate_estimated_duration")

    def test_fills_only_missing_estimated_time_from_legacy_duration(self):
        scenario_model = MagicMock()
        apps = MagicMock()
        apps.get_model.return_value = scenario_model

        self.migration.migrate_estimated_duration(apps, None)

        self.assertEqual(
            [
                call(estimated_time__isnull=True, estimated_duration="short"),
                call(estimated_time__isnull=True, estimated_duration="medium"),
                call(estimated_time__isnull=True, estimated_duration="long"),
                call(estimated_time__isnull=True, estimated_duration="campaign"),
            ],
            scenario_model.objects.filter.call_args_list,
        )
        self.assertEqual(
            [call(estimated_time=180), call(estimated_time=270), call(estimated_time=420), call(estimated_time=480)],
            scenario_model.objects.filter.return_value.update.call_args_list,
        )

    def test_removes_legacy_column_after_data_migration(self):
        operations = self.migration.Migration.operations

        self.assertIsInstance(operations[0], migrations.RunPython)
        self.assertIsInstance(operations[1], migrations.RemoveField)
        self.assertEqual("estimated_duration", operations[1].name)
