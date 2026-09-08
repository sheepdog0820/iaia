import contextlib
import io
import json
import runpy
import unittest
from unittest.mock import MagicMock, patch

from accounts.management.commands.release_database_preflight import Command as PreflightCommand
from scripts.ops import run_restore_preflight as launcher


class RestorePreflightLauncherTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "DB_HOST": "tableno-restore-drill-20260908.example.ap-northeast-1.rds.amazonaws.com",
            "RESTORE_EXPECTED_HOST": "tableno-restore-drill-20260908.example.ap-northeast-1.rds.amazonaws.com",
            "RESTORE_SOURCE_HOST": "tableno-aws-pre.example.ap-northeast-1.rds.amazonaws.com",
            "DB_NAME": "tableno",
            "RESTORE_EXPECTED_DB_NAME": "tableno",
            "DB_USER": "test-user",
            "DB_PASSWORD": "private-password",
            "DB_PORT": "5432",
        }

    def test_minimal_configuration_enforces_tls_and_connect_timeout(self):
        self.env["STRIPE_SECRET_KEY"] = "must-not-be-forwarded"
        self.env["DB_SSL_MODE"] = "disable"
        config = launcher.validated_database(self.env)
        self.assertEqual(config["HOST"], self.env["RESTORE_EXPECTED_HOST"])
        self.assertEqual(config["OPTIONS"], {"sslmode": "require", "connect_timeout": 5})
        self.assertNotIn("STRIPE_SECRET_KEY", json.dumps(config))

    def test_invalid_target_is_rejected_before_probe(self):
        changes = [
            {"DB_HOST": self.env["RESTORE_SOURCE_HOST"]},
            {"RESTORE_SOURCE_HOST": self.env["DB_HOST"]},
            {"RESTORE_EXPECTED_HOST": "another-host"},
            {"DB_HOST": "localhost", "RESTORE_EXPECTED_HOST": "localhost"},
            {"DB_HOST": self.env["DB_HOST"] + ".evil", "RESTORE_EXPECTED_HOST": self.env["DB_HOST"] + ".evil"},
            {"DB_NAME": "wrong-database"},
            {"DB_PORT": "5433"},
        ]
        changes.extend({key: ""} for key in self.env)
        for change in changes:
            with self.subTest(change=list(change)):
                with patch.object(launcher, "run_probe") as probe:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(launcher.main(self.env | change), 1)
                probe.assert_not_called()

    def test_success_prints_only_completed_report(self):
        report = {"read_only": True, "server_major": 18}
        output = io.StringIO()
        with patch.object(launcher, "run_probe", return_value=report):
            with contextlib.redirect_stdout(output):
                self.assertEqual(launcher.main(self.env), 0)
        self.assertEqual(json.loads(output.getvalue()), report)

    def test_failure_does_not_print_exception_or_partial_result(self):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(launcher, "run_probe", side_effect=RuntimeError("private-password private-host SQL")):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                self.assertEqual(launcher.main(self.env), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("private", error.getvalue())
        self.assertNotIn("SQL", error.getvalue())

    def test_probe_uses_minimal_settings_and_closes_connection(self):
        database = launcher.validated_database(self.env)
        cases = [
            (180003, "tableno", True),
            (170005, "tableno", True),
            (180003, "other", True),
            (180003, "tableno", False),
        ]
        for version, name, read_only in cases:
            with self.subTest(version=version, name=name, read_only=read_only):
                with (
                    patch("django.conf.settings", new=MagicMock()) as settings,
                    patch("django.setup") as setup,
                    patch("django.db.connection", new=MagicMock()) as connection,
                    patch("django.core.management.call_command") as command,
                ):
                    connection.pg_version = version
                    connection.cursor.return_value.__enter__.return_value.fetchone.return_value = [name]
                    command.side_effect = lambda *args, **kwargs: kwargs["stdout"].write(
                        json.dumps({"read_only": read_only})
                    )
                    if version == 180003 and name == "tableno" and read_only:
                        self.assertEqual(launcher.run_probe(database), {"read_only": True, "server_major": 18})
                        self.assertIsInstance(command.call_args.args[0], PreflightCommand)
                    else:
                        with self.assertRaises(ValueError):
                            launcher.run_probe(database)
                    settings.configure.assert_called_once_with(
                        DATABASES={"default": database}, INSTALLED_APPS=[], USE_TZ=True
                    )
                    setup.assert_called_once()
                    connection.close.assert_called_once()

    def test_probe_closes_connection_on_database_error(self):
        with (
            patch("django.conf.settings", new=MagicMock()),
            patch("django.setup"),
            patch("django.db.connection", new=MagicMock()) as connection,
            patch("django.core.management.call_command", side_effect=RuntimeError("private SQL")),
        ):
            connection.pg_version = 180003
            connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ["tableno"]
            with self.assertRaises(RuntimeError):
                launcher.run_probe(launcher.validated_database(self.env))
            connection.close.assert_called_once()

    def test_main_defaults_to_process_environment(self):
        with (
            patch.dict("os.environ", self.env, clear=True),
            patch.object(launcher, "run_probe", return_value={}) as probe,
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.main(), 0)
            self.assertEqual(probe.call_args.args[0]["NAME"], "tableno")

    def test_command_entrypoint_returns_failure_without_traceback(self):
        with patch.dict("os.environ", {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(launcher.__file__, run_name="__main__")
        self.assertEqual(caught.exception.code, 1)
        self.assertNotIn("Traceback", error.getvalue())
