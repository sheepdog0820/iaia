from io import StringIO

from django.core.management import CommandError, get_commands, load_command_class
from django.test import SimpleTestCase, override_settings


class DevelopmentCommandBoundaryTest(SimpleTestCase):
    def test_all_bulk_development_commands_reject_shared_settings_before_database_access(self):
        commands = (
            "create_sample_data",
            "create_test_data",
            "create_test_characters",
            "create_session_test_data",
            "create_flow_test_data",
            "create_advanced_scheduling_test_data",
            "reset_dev_session_data",
        )
        settings_cases = (
            ("aws-prod", "production", False),
            ("aws-prod", "production", True),
            ("aws-pre", "staging", False),
            ("aws-pre", "staging", True),
            ("local", "production", True),
            ("local", "staging", True),
            ("unknown", "development", True),
            ("local", "development", False),
        )
        for name in commands:
            command = load_command_class(get_commands()[name], name)
            command.stdout = StringIO()
            for app_env, environment, debug in settings_cases:
                with self.subTest(command=name, app_env=app_env, environment=environment, debug=debug):
                    with override_settings(APP_ENV=app_env, ENVIRONMENT=environment, DEBUG=debug):
                        # SimpleTestCase forbids DB access, including transaction entry.
                        with self.assertRaisesMessage(CommandError, "ローカル開発環境"):
                            command.handle(
                                clear=True,
                                reset=True,
                                force=True,
                                skip_flow=True,
                                username="boundary-only",
                                count=0,
                                users=0,
                                sessions=0,
                                scenarios=0,
                            )
