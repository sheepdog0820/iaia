import json
import tempfile
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import Group
from scenarios.models import Scenario
from schedules.models import SessionParticipant, SessionParticipantRole, SessionYouTubeLink, TRPGSession


class ImportTRPGScheduleCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gm = User.objects.create_user(
            username="gm",
            password="pass",
            nickname="メイサイ",
            email="gm@example.com",
        )
        self.player = User.objects.create_user(
            username="player",
            password="pass",
            nickname="シララ",
            email="player@example.com",
        )

    def _write_payload(self, payload):
        tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        with tmp:
            json.dump(payload, tmp, ensure_ascii=False)
        return tmp.name

    def test_import_json_creates_sessions_participants_scenarios_and_links_idempotently(self):
        payload = {
            "source": "unit-test.xlsx",
            "sessions": [
                {
                    "source_rows": [10],
                    "date": "2026-01-03",
                    "title": "静なるテロリスタ",
                    "kp": "メイサイ",
                    "members": ["シララ", "未登録PL"],
                    "url_or_notes": ["https://youtube.com/live/abc123XYZ09", "メイサイ視点"],
                    "character_names": ["シララPC"],
                }
            ],
        }
        input_path = self._write_payload(payload)

        for _ in range(2):
            out = StringIO()
            call_command(
                "import_trpg_schedule",
                "--input-json",
                input_path,
                "--group-name",
                "移行テスト卓",
                "--default-gm-username",
                self.gm.username,
                "--today",
                "2026-06-20",
                stdout=out,
            )

        group = Group.objects.get(name="移行テスト卓")
        self.assertEqual(group.created_by, self.gm)
        self.assertEqual(TRPGSession.objects.count(), 1)

        session = TRPGSession.objects.get()
        self.assertEqual(session.title, "静なるテロリスタ")
        self.assertEqual(timezone.localtime(session.date).date(), date(2026, 1, 3))
        self.assertEqual(session.status, "completed")
        self.assertEqual(session.visibility, "group")
        self.assertEqual(session.group, group)
        self.assertEqual(session.gm, self.gm)
        self.assertEqual(session.scenario, Scenario.objects.get(title="静なるテロリスタ"))
        self.assertIn("source_rows=10", session.description)
        self.assertIn("メイサイ視点", session.description)

        participants = SessionParticipant.objects.order_by("guest_name", "user__username")
        self.assertEqual(participants.count(), 3)
        self.assertTrue(participants.filter(user=self.gm, participant_roles__role=SessionParticipantRole.Role.GM).exists())
        self.assertTrue(
            participants.filter(user=self.player, participant_roles__role=SessionParticipantRole.Role.PLAYER).exists()
        )
        self.assertTrue(
            participants.filter(
                guest_name="未登録PL",
                participant_roles__role=SessionParticipantRole.Role.PLAYER,
            ).exists()
        )

        self.assertEqual(SessionYouTubeLink.objects.count(), 1)
        link = SessionYouTubeLink.objects.get()
        self.assertEqual(link.video_id, "abc123XYZ09")
        self.assertEqual(link.title, "静なるテロリスタ")
        self.assertEqual(link.added_by, self.gm)

    def test_dry_run_does_not_write(self):
        input_path = self._write_payload(
            {
                "sessions": [
                    {
                        "source_rows": [1],
                        "date": "2026-01-03",
                        "title": "登録されない",
                        "kp": "メイサイ",
                        "members": [],
                        "url_or_notes": [],
                    }
                ],
            }
        )

        call_command(
            "import_trpg_schedule",
            "--input-json",
            input_path,
            "--group-name",
            "Dry Run",
            "--default-gm-username",
            self.gm.username,
            "--dry-run",
        )

        self.assertFalse(TRPGSession.objects.exists())
        self.assertFalse(Group.objects.exists())
