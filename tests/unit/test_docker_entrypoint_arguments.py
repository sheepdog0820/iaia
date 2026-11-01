import os
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "posix" and Path("/bin/sh").is_file(), "Requires POSIX /bin/sh")
class DockerEntrypointArgumentTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def server_arguments(self, timeout=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_python = bin_dir / "python"
            fake_python.write_text('#!/bin/sh\nprintf \'%s\\000\' "$@" > "$ARGV_OUTPUT"\n', encoding="utf-8")
            fake_python.chmod(0o700)
            working_dir = root / "work"
            working_dir.mkdir()
            (working_dir / "unexpected-file").touch()
            output = root / "arguments"
            environment = {
                "PATH": str(bin_dir),
                "APP_ENV": "aws-pre",
                "RUN_MIGRATIONS": "false",
                "RUN_COLLECTSTATIC": "false",
                "CREATE_DEV_LOGIN_USER": "false",
                "ARGV_OUTPUT": str(output),
            }
            if timeout is not None:
                environment["DAPHNE_APPLICATION_CLOSE_TIMEOUT"] = timeout
            result = subprocess.run(
                ["/bin/sh", str(self.ROOT / "docker" / "entrypoint.sh")],
                cwd=working_dir,
                env=environment,
                capture_output=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
            return output.read_bytes().decode("utf-8").rstrip("\0").split("\0")

    def expected_arguments(self, timeout):
        return [
            "-m",
            "tableno.server",
            "--bind",
            "0.0.0.0",
            "--port",
            "8000",
            "--application-close-timeout",
            timeout,
            "tableno.asgi:application",
        ]

    def test_unset_timeout_keeps_the_default(self):
        self.assertEqual(self.server_arguments(), self.expected_arguments("10"))

    def test_numeric_timeout_remains_one_argument(self):
        self.assertEqual(self.server_arguments("17"), self.expected_arguments("17"))

    def test_timeout_cannot_add_server_options(self):
        value = "17 --bind 127.0.0.1"
        self.assertEqual(self.server_arguments(value), self.expected_arguments(value))

    def test_timeout_is_not_expanded_to_working_directory_files(self):
        self.assertEqual(self.server_arguments("*"), self.expected_arguments("*"))
