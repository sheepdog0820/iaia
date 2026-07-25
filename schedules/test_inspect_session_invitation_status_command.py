import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from accounts.models import Group
from schedules.models import SessionInvitation, TRPGSession


class InspectSessionInvitationStatusCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="invitation-owner")
        self.invitee = user_model.objects.create_user(username="invitation-target")
        self.group = Group.objects.create(name="Invitation Group", created_by=self.owner)
        self.session = TRPGSession.objects.create(
            title="Invitation Investigation",
            created_by=self.owner,
            gm=self.owner,
            group=self.group,
        )

    def test_outputs_session_and_invitation_status_as_json(self):
        invitation = SessionInvitation.objects.create(
            session=self.session,
            inviter=self.owner,
            invitee=self.invitee,
            status="pending",
            invited_role="player",
        )
        output = StringIO()

        call_command(
            "inspect_session_invitation_status",
            session_id=self.session.pk,
            stdout=output,
        )

        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["session"],
            {
                "id": self.session.pk,
                "title": "Invitation Investigation",
                "group_id": self.group.pk,
                "group_name": "Invitation Group",
            },
        )
        self.assertEqual(payload["invitation_count"], 1)
        self.assertEqual(
            payload["invitations"][0],
            {
                "id": invitation.pk,
                "invitee_username": "invitation-target",
                "status": "pending",
                "invited_role": "player",
            },
        )

    def test_missing_session_returns_command_error(self):
        with self.assertRaisesMessage(CommandError, "Session 999999 does not exist."):
            call_command("inspect_session_invitation_status", session_id=999999)

    def test_outputs_empty_invitations_for_session_without_group(self):
        session = TRPGSession.objects.create(
            title="Ungrouped Investigation",
            created_by=self.owner,
            gm=self.owner,
        )
        TRPGSession.objects.filter(pk=session.pk).update(group=None)
        output = StringIO()

        call_command(
            "inspect_session_invitation_status",
            session_id=session.pk,
            stdout=output,
        )

        payload = json.loads(output.getvalue())
        self.assertIsNone(payload["session"]["group_id"])
        self.assertIsNone(payload["session"]["group_name"])
        self.assertEqual(payload["invitation_count"], 0)
        self.assertEqual(payload["invitations"], [])

    def test_aws_override_invokes_management_command_for_session_313(self):
        override_path = Path(settings.BASE_DIR) / "aws_invitation_status.json"
        payload = json.loads(override_path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["containerOverrides"][0]["command"],
            [
                "python",
                "manage.py",
                "inspect_session_invitation_status",
                "--session-id",
                "313",
            ],
        )
