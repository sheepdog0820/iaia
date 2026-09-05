from contextlib import ExitStack
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError
from django.test import SimpleTestCase, override_settings

from accounts.management.commands.create_sample_data import Command


class SampleDataEnvironmentTest(SimpleTestCase):
    def test_shared_or_non_debug_settings_are_rejected_before_data_access(self):
        cases = [
            ("aws-prod", "production", False),
            ("aws-pre", "staging", True),
            ("local", "production", True),
            ("local", "development", False),
            ("unknown", "development", True),
        ]
        for app_env, environment, debug in cases:
            for clear in (False, True):
                with self.subTest(app_env=app_env, environment=environment, debug=debug, clear=clear):
                    command = Command(stdout=StringIO())
                    with override_settings(APP_ENV=app_env, ENVIRONMENT=environment, DEBUG=debug):
                        with patch.object(command, "clear_data") as clear_data:
                            with patch.object(command, "create_users") as create_users:
                                with self.assertRaisesMessage(CommandError, "ローカル開発環境"):
                                    command.handle(clear=clear)
                                clear_data.assert_not_called()
                                create_users.assert_not_called()

    def test_local_debug_workflow_remains_available(self):
        methods = [
            "clear_data",
            "create_users",
            "create_groups",
            "create_friendships",
            "create_scenarios",
            "create_sessions",
            "create_play_history",
        ]
        for app_env in ("local", "dev", "development"):
            with self.subTest(app_env=app_env):
                command = Command(stdout=StringIO())
                with override_settings(APP_ENV=app_env, ENVIRONMENT="development", DEBUG=True):
                    with ExitStack() as stack:
                        mocks = {
                            name: stack.enter_context(patch.object(command, name, return_value=[])) for name in methods
                        }
                        command.handle(clear=True)
                        for mock in mocks.values():
                            mock.assert_called_once()
