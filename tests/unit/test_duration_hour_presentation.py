from pathlib import Path

from django.test import SimpleTestCase

from schedules.duration import format_duration_hours, hours_to_minutes


class DurationHourFormattingTests(SimpleTestCase):
    def test_formats_minutes_as_decimal_hours(self):
        self.assertEqual("0.5時間", format_duration_hours(30))
        self.assertEqual("1.5時間", format_duration_hours(90))
        self.assertEqual("4時間", format_duration_hours(240))
        self.assertEqual("未設定", format_duration_hours(0))
        self.assertEqual("未設定", format_duration_hours(None))

    def test_converts_decimal_hours_to_minutes(self):
        self.assertEqual(30, hours_to_minutes("0.5"))
        self.assertEqual(90, hours_to_minutes("1.5"))
        self.assertEqual(240, hours_to_minutes(4))
        self.assertIsNone(hours_to_minutes(""))


class DurationHourUiStaticTests(SimpleTestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def read(self, relative_path):
        return (self.ROOT / relative_path).read_text(encoding="utf-8")

    def test_scenario_views_use_hour_inputs_and_displays(self):
        archive = self.read("templates/scenarios/archive.html")
        public_detail = self.read("templates/scenarios/scenario_public_detail.html")

        self.assertIn("所要時間（時間）", archive)
        self.assertIn("hoursToMinutes", archive)
        self.assertIn("minutesToHours", archive)
        self.assertNotIn("所要時間（分）", archive)
        self.assertIn("duration_hours", public_detail)

    def test_session_views_do_not_present_minute_units(self):
        paths = [
            "templates/schedules/_session_edit_form_fields.html",
            "templates/schedules/calendar.html",
            "templates/schedules/sessions_list.html",
            "templates/schedules/session_detail.html",
            "templates/schedules/session_date_poll.html",
        ]

        for relative_path in paths:
            with self.subTest(relative_path=relative_path):
                content = self.read(relative_path)
                self.assertNotIn("予定時間（分）", content)
                self.assertNotIn("実時間（分）", content)
                self.assertNotRegex(content, r"duration_minutes\s*}}分")
