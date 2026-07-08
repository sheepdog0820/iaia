from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from schedules import session_permissions
from schedules.models import SessionParticipant, SessionParticipantRole, TRPGSession


User = get_user_model()


class UnifiedSessionRoleServiceTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="role-owner", email="owner@example.com", password="pass")
        self.manager = User.objects.create_user(username="role-manager", email="manager@example.com", password="pass")
        self.gm = User.objects.create_user(username="role-gm", email="gm@example.com", password="pass")
        self.player = User.objects.create_user(username="role-player", email="player@example.com", password="pass")
        self.group = Group.objects.create(name="Unified Role Group", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.manager, role="member")
        GroupMembership.objects.create(group=self.group, user=self.gm, role="member")
        GroupMembership.objects.create(group=self.group, user=self.player, role="member")
        self.session = TRPGSession.objects.create(
            title="Unified Role Session",
            created_by=self.owner,
            group=self.group,
            visibility="group",
            date=timezone.now() + timedelta(days=1),
        )

    def test_created_session_gets_owner_participant_role_and_no_session_permission_model(self):
        session = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            title="Created Session",
            group=self.group,
            visibility="group",
            date=timezone.now() + timedelta(days=2),
        )

        participant = SessionParticipant.objects.get(session=session, user=self.owner)
        self.assertEqual(session_permissions.get_primary_participant_role(participant), "owner")
        with self.assertRaises(LookupError):
            apps.get_model("schedules", "SessionPermission")

    def test_owner_manager_and_gm_permissions_are_unified_roles(self):
        owner_participant = session_permissions.create_participant(
            session=self.session,
            user=self.owner,
            role=SessionParticipantRole.Role.OWNER,
        )
        manager_participant = session_permissions.create_participant(
            session=self.session,
            user=self.manager,
            role=SessionParticipantRole.Role.MANAGER,
        )
        gm_participant = session_permissions.create_participant(
            session=self.session,
            user=self.gm,
            role=SessionParticipantRole.Role.GM,
        )

        self.assertEqual(session_permissions.get_primary_participant_role(owner_participant), "owner")
        self.assertEqual(session_permissions.get_primary_participant_role(manager_participant), "manager")
        self.assertEqual(session_permissions.get_primary_participant_role(gm_participant), "gm")
        for user in [self.owner, self.manager, self.gm]:
            self.assertTrue(session_permissions.can_edit_session_basic(user, self.session))
            self.assertTrue(session_permissions.can_manage_participants(user, self.session))
            self.assertTrue(session_permissions.can_manage_permissions(user, self.session))

        self.assertFalse(session_permissions.can_view_secret_content(self.owner, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.manager, self.session))
        self.assertTrue(session_permissions.can_view_secret_content(self.gm, self.session))

    def test_participant_role_is_single_and_observer_is_rejected(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role=SessionParticipantRole.Role.PLAYER,
        )

        session_permissions.set_participant_roles(participant, [SessionParticipantRole.Role.GM])
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm"})

        session_permissions.set_participant_roles(participant, [SessionParticipantRole.Role.PLAYER])
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"player"})
        self.assertEqual(participant.participant_roles.count(), 1)

        with self.assertRaises(ValueError):
            session_permissions.set_participant_roles(participant, ["observer"])


class UnifiedSessionRoleApiTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="api-role-owner", email="owner@example.com", password="pass")
        self.manager = User.objects.create_user(username="api-role-manager", email="manager@example.com", password="pass")
        self.gm = User.objects.create_user(username="api-role-gm", email="gm@example.com", password="pass")
        self.player = User.objects.create_user(username="api-role-player", email="player@example.com", password="pass")
        self.group_member = User.objects.create_user(
            username="api-role-member",
            email="member@example.com",
            password="pass",
        )
        self.group = Group.objects.create(name="Unified Role API Group", created_by=self.owner)
        for user in [self.owner, self.manager, self.gm, self.player, self.group_member]:
            GroupMembership.objects.create(group=self.group, user=user, role="member")
        self.session = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            title="Unified Role API Session",
            group=self.group,
            visibility="group",
            date=timezone.now() + timedelta(days=1),
        )
        self.gm_participant = session_permissions.create_participant(
            session=self.session,
            user=self.gm,
            role=SessionParticipantRole.Role.GM,
        )
        self.player_participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role=SessionParticipantRole.Role.PLAYER,
        )
        self.client.force_authenticate(user=self.owner)

    def test_permissions_scope_lists_participants_only_and_hides_internal_manager(self):
        session_permissions.create_participant(
            session=self.session,
            user=self.manager,
            role=SessionParticipantRole.Role.MANAGER,
        )

        response = self.client.get(reverse("session-permissions", kwargs={"pk": self.session.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        role_values = [role["value"] for role in response.data["participant_roles"]]
        self.assertEqual(role_values, ["gm", "player"])
        user_ids = {row["user_id"] for row in response.data["users"]}
        self.assertIn(self.owner.id, user_ids)
        self.assertIn(self.gm.id, user_ids)
        self.assertIn(self.player.id, user_ids)
        self.assertNotIn(self.manager.id, user_ids)
        self.assertNotIn(self.group_member.id, user_ids)

    def test_permissions_api_switches_only_gm_and_player_roles(self):
        response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": self.session.id}),
            {"participant_id": self.player_participant.id, "roles": ["gm"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.player_participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(self.player_participant), {"gm"})

        response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": self.session.id}),
            {"participant_id": self.player_participant.id, "roles": ["owner"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_accepts_only_gm_or_player(self):
        observer_response = self.client.post(
            reverse("session-invite", kwargs={"pk": self.session.id}),
            {"user_id": self.group_member.id, "roles": ["observer"]},
            format="json",
        )
        self.assertEqual(observer_response.status_code, status.HTTP_400_BAD_REQUEST)

        manager_response = self.client.post(
            reverse("session-invite", kwargs={"pk": self.session.id}),
            {"user_id": self.group_member.id, "roles": ["manager"]},
            format="json",
        )
        self.assertEqual(manager_response.status_code, status.HTTP_400_BAD_REQUEST)

        gm_response = self.client.post(
            reverse("session-invite", kwargs={"pk": self.session.id}),
            {"user_id": self.group_member.id, "roles": ["gm"]},
            format="json",
        )
        self.assertEqual(gm_response.status_code, status.HTTP_200_OK)
        invitation = self.group_member.received_session_invitations.get(session=self.session)
        self.assertEqual(invitation.invited_role, "gm")
