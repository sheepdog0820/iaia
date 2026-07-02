import re
import subprocess
from pathlib import Path

from django.test import SimpleTestCase


class TextQualityTestCase(SimpleTestCase):
    # Keep these markers escaped so this test file itself remains scan-clean.
    MOJIBAKE_MARKERS = [
        "\u7e67",
        "\u7e3a",
        "\u8b5b",
        "\u879f",
        "\u8700",
        "\u9a3e",
        "\u9ae2",
        "\u8737",
        "\u86f9",
        "\u90e2\uff67",
        "\u90b5\uff7a",
        "\u96b4\ufffd",
        "\u9aeb\uff71",
        "\u9b2e\uff6f",
        "\u9677\ufffd",
        "\u9a4d\ufffd",
        "\ufffd",
        "\uf8f0",
        chr(0x7E5D),
        chr(0x8711),
        chr(0x90B5),
        chr(0x90E2),
        chr(0x96B4),
        chr(0x9B2E),
        chr(0x9677),
        chr(0x9A4D),
    ]
    TEXT_FILE_SUFFIXES = {
        ".cfg",
        ".css",
        ".dockerignore",
        ".editorconfig",
        ".env",
        ".example",
        ".flake8",
        ".gitattributes",
        ".gitignore",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    EXCLUDED_TEXT_PREFIXES = ("static/vendor/",)
    USER_FACING_PREFIXES = ("docs/", "templates/")
    QUESTION_MARK_PLACEHOLDER_RE = re.compile(r"\?{3,}")

    CHECKED_FILES = [
        Path("templates/integrations/settings.html"),
        Path("accounts/test_character_6th_comprehensive.py"),
        Path("docs/release/PUBLIC_RELEASE_TASKS.md"),
    ]
    RUNTIME_CONSOLE_LOG_FILES = [
        Path("templates/scenarios/archive.html"),
        Path("templates/schedules/calendar.html"),
        Path("templates/schedules/sessions.html"),
        Path("templates/schedules/session_date_poll.html"),
        Path("templates/schedules/session_detail.html"),
        Path("static/js/error-detector.js"),
    ]

    def _tracked_text_files(self, root):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        for raw_path in result.stdout.splitlines():
            normalized = raw_path.replace("\\", "/")
            if normalized.startswith(self.EXCLUDED_TEXT_PREFIXES):
                continue

            relative_path = Path(raw_path)
            path = root / relative_path
            if not path.exists():
                continue

            if path.suffix.lower() in self.TEXT_FILE_SUFFIXES:
                yield relative_path

    def test_tracked_text_files_are_utf8_without_mojibake_markers(self):
        root = Path(__file__).resolve().parents[2]
        failures = []

        for relative_path in self._tracked_text_files(root):
            path = root / relative_path
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                failures.append(f"{relative_path}: cannot decode as UTF-8 ({exc})")
                continue

            for marker in self.MOJIBAKE_MARKERS:
                if marker in content:
                    failures.append(f"{relative_path}: contains mojibake marker {marker!r}")
                    break

        self.assertFalse(failures, "\n".join(failures[:50]))

    def test_user_facing_text_has_no_question_mark_placeholders(self):
        root = Path(__file__).resolve().parents[2]
        failures = []

        for relative_path in self._tracked_text_files(root):
            normalized = relative_path.as_posix()
            if not normalized.startswith(self.USER_FACING_PREFIXES):
                continue
            if relative_path.suffix.lower() not in {".html", ".md", ".txt"}:
                continue

            content = (root / relative_path).read_text(encoding="utf-8")
            for line_number, line in enumerate(content.splitlines(), start=1):
                if self.QUESTION_MARK_PLACEHOLDER_RE.search(line):
                    failures.append(f"{relative_path}:{line_number}: {line.strip()}")

        self.assertFalse(failures, "\n".join(failures[:50]))

    def test_runtime_assets_do_not_emit_console_log(self):
        root = Path(__file__).resolve().parents[2]
        failures = []

        for relative_path in self.RUNTIME_CONSOLE_LOG_FILES:
            content = (root / relative_path).read_text(encoding="utf-8")
            if "console.log(" in content:
                failures.append(f"{relative_path}: contains console.log")

        self.assertFalse(failures, "\n".join(failures))

    def test_user_facing_integration_copy_has_no_mojibake_markers(self):
        root = Path(__file__).resolve().parents[2]
        for relative_path in self.CHECKED_FILES:
            content = (root / relative_path).read_text(encoding="utf-8")
            for marker in self.MOJIBAKE_MARKERS:
                self.assertNotIn(marker, content, f"{relative_path} contains mojibake marker {marker!r}")

    def test_discord_failure_ui_copy_is_localized(self):
        root = Path(__file__).resolve().parents[2]
        content = (root / "templates/integrations/settings.html").read_text(encoding="utf-8")

        expected_labels = [
            "Discord通知失敗履歴",
            "Discord通知失敗履歴を読み込み中...",
            "Discord通知失敗はありません。",
            "再送",
            "Discord通知の再送を開始しました",
            "Discord通知を再送キューに登録できませんでした",
        ]
        for label in expected_labels:
            self.assertIn(label, content)

        unexpected_labels = [
            "Discord delivery failures",
            "Loading Discord delivery failures",
            "No Discord delivery failures",
            ">Retry<",
        ]
        for label in unexpected_labels:
            self.assertNotIn(label, content)
