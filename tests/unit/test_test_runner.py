from unittest import TestCase
from unittest.mock import patch

from django.test.runner import DiscoverRunner

from tableno.test_runner import ProjectDiscoverRunner


class ProjectDiscoverRunnerTests(TestCase):
    def test_no_label_run_uses_project_default_labels(self):
        runner = ProjectDiscoverRunner(verbosity=0, interactive=False)

        with patch.object(DiscoverRunner, "build_suite", return_value="suite") as build_suite:
            suite = runner.build_suite([])

        self.assertEqual(suite, "suite")
        self.assertEqual(
            build_suite.call_args.args[0],
            ("accounts", "schedules", "scenarios", "tests.unit"),
        )

    def test_explicit_labels_are_respected(self):
        runner = ProjectDiscoverRunner(verbosity=0, interactive=False)

        with patch.object(DiscoverRunner, "build_suite", return_value="suite") as build_suite:
            suite = runner.build_suite(["tests.ui"])

        self.assertEqual(suite, "suite")
        self.assertEqual(build_suite.call_args.args[0], ["tests.ui"])
