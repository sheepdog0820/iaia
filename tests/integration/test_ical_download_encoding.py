import re
from datetime import timedelta
from datetime import timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules import session_permissions
from schedules.models import TRPGSession


class ICalDownloadEncodingTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ics-download", nickname="カレンダー利用者")
        self.group = Group.objects.create(name="カレンダー検証", created_by=self.user)
        self.session = TRPGSession.objects.create(
            title="日本語のセッション🎲",
            description="説明",
            location="会場",
            created_by=self.user,
            gm=self.user,
            group=self.group,
            date=timezone.now() + timedelta(days=1),
            status="planned",
            duration_minutes=180,
        )
        session_permissions.create_participant(session=self.session, user=self.user, role="gm")
        self.client.force_authenticate(self.user)

    def download(self):
        response = self.client.get(reverse("ical_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        unfolded = re.sub(rb"\r\n[ \t]", b"", response.content).decode("utf-8")
        return response.content, unfolded.split("\r\n")

    def test_user_text_cannot_inject_calendar_components_or_properties(self):
        for field in ("title", "description", "location", "nickname", "group_name"):
            for newline in ("\r\n", "\r", "\n"):
                with self.subTest(field=field, newline=repr(newline)):
                    self.user.nickname = "カレンダー利用者"
                    self.user.save(update_fields=["nickname"])
                    self.group.name = "カレンダー検証"
                    self.group.save(update_fields=["name"])
                    self.session.title = "日本語のセッション🎲"
                    self.session.description = "説明"
                    self.session.location = "会場"
                    text = f"検証{newline}BEGIN:VEVENT{newline}SUMMARY:偽予定{newline}END:VEVENT"
                    if field == "nickname":
                        self.user.nickname = text
                        self.user.save(update_fields=["nickname"])
                    elif field == "group_name":
                        self.group.name = text
                        self.group.save(update_fields=["name"])
                    else:
                        setattr(self.session, field, text)
                    self.session.save(update_fields=["title", "description", "location"])
                    _, lines = self.download()
                    self.assertEqual(lines.count("BEGIN:VCALENDAR"), 1)
                    self.assertEqual(lines.count("END:VCALENDAR"), 1)
                    self.assertEqual(lines.count("BEGIN:VEVENT"), 1)
                    self.assertEqual(lines.count("END:VEVENT"), 1)
                    self.assertEqual(lines.count("BEGIN:VALARM"), 2)
                    self.assertEqual(lines.count("END:VALARM"), 2)
                    self.assertNotIn("SUMMARY:偽予定", lines)
                    self.assertFalse(any("\n" in line or "\r" in line for line in lines))
                    self.assertIn("検証\\nBEGIN:VEVENT\\nSUMMARY:偽予定\\nEND:VEVENT", "\r\n".join(lines))

    def test_delimiters_and_literal_backslash_are_preserved_as_text(self):
        text = "場所,入口;奥\\室:机"
        escaped = "場所\\,入口\\;奥\\\\室:机"
        self.user.nickname = text
        self.user.save(update_fields=["nickname"])
        self.group.name = text
        self.group.save(update_fields=["name"])
        self.session.title = text
        self.session.description = "一行目\r\n二行目\\n三行目"
        self.session.location = text
        self.session.save(update_fields=["title", "description", "location"])
        _, lines = self.download()
        self.assertIn(f"X-WR-CALNAME:タブレノ - {escaped}", lines)
        self.assertIn(f"SUMMARY:[GM] {escaped}", lines)
        self.assertIn(f"LOCATION:{escaped}", lines)
        description = next(line for line in lines if line.startswith("DESCRIPTION:"))
        self.assertIn(f"GM: {escaped}", description)
        self.assertIn(f"Group: {escaped}", description)
        self.assertIn(f"Location: {escaped}", description)
        self.assertIn("\\n一行目\\n二行目\\\\n三行目", description)
        self.assertIn(f"DESCRIPTION:明日のTRPGセッション: {escaped}", lines)
        self.assertIn(f"DESCRIPTION:1時間後のTRPGセッション: {escaped}", lines)

    def test_long_japanese_text_folds_by_utf8_octets_and_ends_with_crlf(self):
        text = "長い日本語のセッション🎲" * 10
        self.session.title = text
        self.session.description = text
        self.session.save(update_fields=["title", "description"])
        raw, lines = self.download()
        self.assertTrue(raw.endswith(b"\r\n"))
        self.assertIn(b"\r\n ", raw)
        for line in raw.split(b"\r\n")[:-1]:
            self.assertLessEqual(len(line), 75)
            line.decode("utf-8", errors="strict")
        self.assertIn(f"SUMMARY:[GM] {text}", lines)
        self.assertIn(f"DESCRIPTION:明日のTRPGセッション: {text}", lines)
        self.assertIn(f"DESCRIPTION:1時間後のTRPGセッション: {text}", lines)

    def test_empty_optional_fields_and_cancelled_session_have_no_alarm(self):
        self.session.description = ""
        self.session.location = ""
        self.session.status = "cancelled"
        self.session.save(update_fields=["description", "location", "status"])
        _, lines = self.download()
        self.assertIn("STATUS:CANCELLED", lines)
        self.assertNotIn("BEGIN:VALARM", lines)
        self.assertFalse(any(line.startswith("LOCATION:") for line in lines))

    def test_download_dates_identify_utc_instead_of_receivers_local_time(self):
        start = self.session.date.astimezone(datetime_timezone.utc)
        end = start + timedelta(minutes=self.session.duration_minutes)
        _, lines = self.download()
        self.assertIn(f'DTSTART:{start.strftime("%Y%m%dT%H%M%SZ")}', lines)
        self.assertIn(f'DTEND:{end.strftime("%Y%m%dT%H%M%SZ")}', lines)

    def test_empty_calendar_and_nickname_fallback(self):
        self.session.delete()
        self.user.nickname = ""
        self.user.save(update_fields=["nickname"])
        raw, lines = self.download()
        self.assertIn("X-WR-CALNAME:タブレノ - ics-download", lines)
        self.assertNotIn("BEGIN:VEVENT", lines)
        self.assertTrue(raw.endswith(b"END:VCALENDAR\r\n"))

    def test_download_excludes_another_users_private_session(self):
        other = get_user_model().objects.create_user(username="ics-other")
        TRPGSession.objects.create(
            title="別利用者の非公開予定",
            created_by=other,
            gm=other,
            visibility="private",
            date=timezone.now() + timedelta(days=1),
        )
        _, lines = self.download()
        self.assertEqual(lines.count("BEGIN:VEVENT"), 1)
        self.assertNotIn("別利用者の非公開予定", "\r\n".join(lines))

    def test_download_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("ical_export"))
        self.assertEqual(response.status_code, 401)
