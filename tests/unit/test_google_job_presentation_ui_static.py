from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from drf_spectacular.openapi import AutoSchema

from schedules.job_views import AsyncJobListView, AsyncJobSerializer


class GoogleJobPresentationUiStaticTest(SimpleTestCase):
    def test_api_schema_has_typed_read_only_status_hints_without_warnings(self):
        schema = AutoSchema()
        schema.view = AsyncJobListView()
        with patch("drf_spectacular.openapi.warn") as warning:
            generated = schema._map_serializer(AsyncJobSerializer(context={"request": None}), "response")
        for name, expected in (("display_state", "string"), ("status_message", "string"), ("can_retry", "boolean")):
            with self.subTest(field=name):
                self.assertEqual(generated["properties"][name]["type"], expected)
                self.assertIs(generated["properties"][name]["readOnly"], True)
        warning.assert_not_called()

    def test_history_requires_explicit_retry_hint_and_displays_safe_status_message(self):
        source = (Path(settings.BASE_DIR) / "templates/integrations/settings.html").read_text(encoding="utf-8")
        self.assertIn("job.can_retry === true", source)
        self.assertIn("job.display_state", source)
        self.assertIn("job.status_message", source)
        self.assertNotIn("const canRetry = job.status === 'failed'", source)

    def test_all_google_status_and_type_labels_are_japanese(self):
        source = (Path(settings.BASE_DIR) / "templates/integrations/settings.html").read_text(encoding="utf-8")
        for label in (
            "処理待ち",
            "対象待ち",
            "処理中",
            "完了",
            "失敗",
            "確認が必要",
            "期限切れ",
            "状態不明",
            "Google Calendar同期",
            "Google Sheets出力",
        ):
            with self.subTest(label=label):
                self.assertIn(label, source)

    def test_successful_intake_does_not_treat_deferred_publish_as_unknown_execution(self):
        source = (Path(settings.BASE_DIR) / "templates/integrations/settings.html").read_text(encoding="utf-8")
        self.assertNotIn("const uncertain = data.queued === false", source)
        self.assertIn("進捗と結果はジョブ履歴で確認してください。", source)
        self.assertIn("操作結果を確認できませんでした。処理が進んでいる可能性があります。", source)

    def test_production_database_ci_includes_owned_hints_and_retry_journal_races(self):
        source = (Path(settings.BASE_DIR) / ".github/workflows/django-ci.yml").read_text(encoding="utf-8")
        self.assertIn("schedules/test_google_job_presentation.py", source)
