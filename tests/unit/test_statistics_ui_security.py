from pathlib import Path

from django.test import SimpleTestCase


class StatisticsUiSecurityTests(SimpleTestCase):
    def test_dynamic_statistics_names_are_html_escaped(self):
        template = (Path(__file__).resolve().parents[2] / "templates/statistics/tindalos_metrics.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("function escapeStatisticsText(value)", template)
        for expression in (
            "escapeStatisticsText(group.group_name)",
            "escapeStatisticsText(group.top_gm || '—')",
            "escapeStatisticsText(session.title)",
            "escapeStatisticsText(session.group_name)",
            "escapeStatisticsText(session.gm_name)",
            "escapeStatisticsText(item.nickname)",
        ):
            with self.subTest(expression=expression):
                self.assertIn(expression, template)
