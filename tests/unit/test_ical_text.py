import unittest

from schedules.ical_text import escape_ical, fold_ical_line


class ICalTextTests(unittest.TestCase):
    def test_empty_values_and_plain_text(self):
        self.assertEqual(escape_ical(None), "")
        self.assertEqual(escape_ical("日本語:説明"), "日本語:説明")
        self.assertEqual(fold_ical_line(""), "")

    def test_fold_boundary_counts_continuation_space_and_utf8(self):
        self.assertEqual(fold_ical_line("a" * 75), "a" * 75)
        self.assertEqual(fold_ical_line("a" * 76), "a" * 75 + "\r\n a")
        self.assertEqual(fold_ical_line("あ" * 25 + "🎲" * 19), "あ" * 25 + "\r\n " + "🎲" * 18 + "\r\n 🎲")

    def test_escape_handles_all_line_endings_and_literal_delimiters(self):
        self.assertEqual(escape_ical("一\r\n二\r三\n四\\五,六;七:八"), "一\\n二\\n三\\n四\\\\五\\,六\\;七:八")
