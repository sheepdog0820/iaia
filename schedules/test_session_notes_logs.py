from schedules import session_permissions
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Group
from schedules.models import SessionParticipant, TRPGSession


class SessionNotesLogsRemovedAPITestCase(APITestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username="gm_user",
            email="gm@example.com",
            password="pass1234",
            nickname="GM",
        )
        self.group = Group.objects.create(
            name="Test Group",
            description="Group for removed notes/log tests",
            created_by=self.gm,
            visibility="private",
        )
        self.group.members.add(self.gm)
        self.session = TRPGSession.objects.create(
            title="Removed Notes Logs Session",
            description="",
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            duration_minutes=180,
            location="Online",
            gm=self.gm,
            group=self.group,
            status="planned",
            visibility="group",
        )

    def test_session_notes_logs_endpoints_are_not_exposed(self):
        self.client.force_authenticate(user=self.gm)

        endpoints = [
            f"/api/schedules/sessions/{self.session.id}/notes/",
            f"/api/schedules/sessions/{self.session.id}/logs/",
            "/api/schedules/notes/",
            "/api/schedules/logs/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SessionNotesLogsRemovedUITestCase(TestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username="gm_user",
            email="gm@example.com",
            password="pass1234",
            nickname="GM",
        )
        self.player = CustomUser.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="pass1234",
            nickname="PL1",
        )
        self.group = Group.objects.create(
            name="Test Group",
            created_by=self.gm,
            visibility="private",
        )
        self.group.members.add(self.gm, self.player)
        self.session = TRPGSession.objects.create(
            title="UI Removed Notes Logs Session",
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            gm=self.gm,
            group=self.group,
            status="planned",
            visibility="group",
        )
        session_permissions.create_participant(session=self.session, user=self.player, role="player")

    def test_session_detail_does_not_show_notes_logs_ui(self):
        self.client.login(username="player1", password="pass1234")
        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/detail/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "セッションノート / ログ")
        self.assertNotContains(response, "sessionNotesLogsCard")
        self.assertNotContains(response, "sessionNoteModal")
        self.assertNotContains(response, "sessionLogModal")
