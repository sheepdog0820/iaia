from pathlib import Path

from django.test import SimpleTestCase


class TextQualityTestCase(SimpleTestCase):
    MOJIBAKE_MARKERS = [
        "繧",
        "縺",
        "譛",
        "螟",
        "蜀",
        "騾",
        "髢",
        "蜷",
        "蛹",
    ]

    CHECKED_FILES = [
        Path("templates/integrations/settings.html"),
        Path("accounts/test_character_6th_comprehensive.py"),
    ]

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
