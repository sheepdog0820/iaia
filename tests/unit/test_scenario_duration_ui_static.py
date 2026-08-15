from pathlib import Path

from django.test import SimpleTestCase


class ScenarioDurationUiStaticTests(SimpleTestCase):
    def setUp(self):
        self.template = (Path(__file__).resolve().parents[2] / "templates/scenarios/archive.html").read_text(
            encoding="utf-8"
        )

    def test_scenario_form_uses_only_estimated_time(self):
        self.assertIn('label for="scenarioEstimatedTime" class="form-label">所要時間（時間）</label>', self.template)
        self.assertNotIn('id="scenarioDuration"', self.template)
        self.assertNotIn("estimated_duration: document.getElementById('scenarioDuration').value", self.template)

    def test_scenario_duration_filter_is_removed(self):
        self.assertNotIn('id="durationFilter"', self.template)
        self.assertNotIn("currentFilters.duration", self.template)

    def test_scenario_cards_and_detail_display_estimated_time(self):
        self.assertIn("formatEstimatedTime(scenario?.estimated_time)", self.template)
        self.assertNotIn("getDurationLabel(scenario?.estimated_duration)", self.template)
