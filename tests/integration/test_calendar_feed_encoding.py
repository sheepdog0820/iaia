import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from schedules.integration_views import _escape_ical
from schedules.models import CalendarSubscription, TRPGSession


class CalendarFeedEncodingTests(TestCase):
    def test_text_normalizes_line_endings_and_escapes_delimiters(self):
        self.assertEqual(_escape_ical("一\r\n二\r三\n四\\五,六;七:八"), "一\\n二\\n三\\n四\\\\五\\,六\\;七:八")
        self.assertEqual(_escape_ical(None), "")

    def test_japanese_feed_has_valid_folded_utf8_lines_and_preserves_values(self):
        user = get_user_model().objects.create_user(username="ics-reader", nickname="あ" * 40)
        title = "長い日本語のセッション🎲" * 7
        session = TRPGSession.objects.create(
            title=title,
            created_by=user,
            date=timezone.now() + timedelta(days=1),
            description="説明\r\n次行\rEND:VEVENT\rBEGIN:VEVENT",
            location="場所,会場;入口\\奥",
        )
        TRPGSession.objects.create(title="日程未定" * 20, created_by=user, date=None, description="未定\r\n相談")
        _, token = CalendarSubscription.issue_for(user)
        response = self.client.get(f"/calendar/subscribe/{token}.ics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        raw = response.content
        self.assertTrue(raw.endswith(b"\r\n"))
        for line in raw.split(b"\r\n")[:-1]:
            self.assertLessEqual(len(line), 75)
            self.assertNotIn(b"\r", line)
            self.assertNotIn(b"\n", line)
            line.decode("utf-8", errors="strict")
        unfolded = re.sub(rb"\r\n[ \t]", b"", raw).decode("utf-8")
        self.assertIn(f"SUMMARY:[Player] {title}\r\n", unfolded)
        self.assertIn("X-WR-CALNAME:Tableno - " + "あ" * 40 + "\r\n", unfolded)
        self.assertIn("DESCRIPTION:説明\\n次行\\nEND:VEVENT\\nBEGIN:VEVENT\r\n", unfolded)
        self.assertIn("LOCATION:場所\\,会場\\;入口\\\\奥\r\n", unfolded)
        self.assertIn("DESCRIPTION:未定\\n相談\r\n", unfolded)
        self.assertEqual(unfolded.split("\r\n").count("BEGIN:VEVENT"), 1)
        self.assertEqual(unfolded.split("\r\n").count("BEGIN:VTODO"), 1)
        self.assertIn(f"UID:session-{session.pk}@tableno\r\n", unfolded)
