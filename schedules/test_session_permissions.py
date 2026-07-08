from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership
from schedules import session_permissions
from schedules.models import (
    ParticipantClaimRequest,
    ParticipantIdentity,
    SessionParticipant,
    SessionParticipantRole,
    SessionPermission,
    TRPGSession,
)


User = get_user_model()


class SessionPermissionServiceTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
        self.gm = User.objects.create_user(username="gm", email="gm@example.com", password="pass")
        self.manager = User.objects.create_user(username="manager", email="manager@example.com", password="pass")
        self.player = User.objects.create_user(username="player", email="player@example.com", password="pass")
        self.group_admin = User.objects.create_user(
            username="group-admin",
            email="group-admin@example.com",
            password="pass",
        )
        self.group_member = User.objects.create_user(
            username="group-member",
            email="group-member@example.com",
            password="pass",
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass",
        )
        self.group = Group.objects.create(name="Permission Group", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.group_admin, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.group_member, role="member")
        self.session = TRPGSession.objects.create(
            title="Permission Session",
            created_by=self.owner,
            group=self.group,
            visibility="group",
            date=timezone.now() + timedelta(days=1),
        )

    def test_owner_can_manage_basic_but_not_secrets_without_secret_keeper(self):
        session_permissions.grant_session_permission(
            self.session,
            self.owner,
            SessionPermission.Role.OWNER,
        )

        self.assertTrue(session_permissions.can_edit_session_basic(self.owner, self.session))
        self.assertTrue(session_permissions.can_manage_participants(self.owner, self.session))
        self.assertTrue(session_permissions.can_manage_share_links(self.owner, self.session))
        self.assertTrue(session_permissions.can_manage_permissions(self.owner, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.owner, self.session))

    def test_manager_can_manage_basic_but_not_permissions_or_secrets(self):
        session_permissions.grant_session_permission(
            self.session,
            self.manager,
            SessionPermission.Role.MANAGER,
            granted_by=self.owner,
        )

        self.assertTrue(session_permissions.can_edit_session_basic(self.manager, self.session))
        self.assertTrue(session_permissions.can_manage_participants(self.manager, self.session))
        self.assertTrue(session_permissions.can_manage_share_links(self.manager, self.session))
        self.assertFalse(session_permissions.can_manage_permissions(self.manager, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.manager, self.session))

    def test_gm_participant_role_grants_secret_keeper_but_secret_can_be_removed(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.gm,
            roles=[SessionParticipantRole.Role.PLAYER],
        )

        session_permissions.assign_participant_role(
            participant,
            SessionParticipantRole.Role.GM,
            granted_by=self.owner,
        )

        participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"player", "gm"})
        self.assertTrue(session_permissions.is_session_gm(self.gm, self.session))
        self.assertTrue(session_permissions.can_edit_session_basic(self.gm, self.session))
        self.assertTrue(session_permissions.can_view_secret_content(self.gm, self.session))

        session_permissions.revoke_session_permission(
            self.session,
            self.gm,
            SessionPermission.Role.SECRET_KEEPER,
        )

        self.assertTrue(session_permissions.is_session_gm(self.gm, self.session))
        self.assertTrue(session_permissions.can_edit_session_basic(self.gm, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.gm, self.session))

    def test_group_admin_can_manage_basic_without_secret_access(self):
        self.assertTrue(session_permissions.can_edit_session_basic(self.group_admin, self.session))
        self.assertTrue(session_permissions.can_manage_participants(self.group_admin, self.session))
        self.assertTrue(session_permissions.can_manage_share_links(self.group_admin, self.session))
        self.assertTrue(session_permissions.can_manage_permissions(self.group_admin, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.group_admin, self.session))

    def test_participant_can_have_multiple_roles(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            roles=[SessionParticipantRole.Role.PLAYER],
        )

        session_permissions.assign_participant_role(participant, SessionParticipantRole.Role.PLAYER)
        session_permissions.assign_participant_role(participant, SessionParticipantRole.Role.OBSERVER)
        session_permissions.assign_participant_role(participant, SessionParticipantRole.Role.PLAYER)

        self.assertEqual(
            session_permissions.get_participant_role_values(participant),
            {"player", "observer"},
        )

    def test_set_participant_roles_can_downgrade_gm_and_revoke_secret_keeper(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.gm,
            roles=[SessionParticipantRole.Role.GM],
        )
        session_permissions.set_participant_roles(
            participant,
            [SessionParticipantRole.Role.GM],
            granted_by=self.owner,
        )
        self.assertTrue(session_permissions.can_view_secret_content(self.gm, self.session))

        session_permissions.set_participant_roles(
            participant,
            [SessionParticipantRole.Role.PLAYER],
            granted_by=self.owner,
        )

        participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"player"})
        self.assertFalse(session_permissions.can_view_secret_content(self.gm, self.session))

    def test_guest_participant_can_receive_gm_role_without_user_account(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=None,
            guest_name="Guest Keeper",
            roles=[SessionParticipantRole.Role.PLAYER],
        )

        session_permissions.set_participant_roles(
            participant,
            [SessionParticipantRole.Role.GM],
            granted_by=self.owner,
        )

        participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm"})

    def test_create_personal_session_without_group_or_gm_grants_owner_only(self):
        personal = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            title="Personal Session",
            visibility="private",
            date=timezone.now() + timedelta(days=2),
        )

        self.assertIsNone(personal.group_id)
        self.assertIsNone(personal.gm_id)
        self.assertTrue(
            SessionPermission.objects.filter(
                session=personal,
                user=self.owner,
                role=SessionPermission.Role.OWNER,
            ).exists()
        )
        self.assertFalse(session_permissions.can_view_secret_content(self.owner, personal))

    def test_create_session_with_self_as_gm_grants_owner_and_secret_keeper(self):
        session = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            gm=self.owner,
            title="Self GM Session",
            visibility="private",
            date=timezone.now() + timedelta(days=3),
        )

        self.assertEqual(
            session_permissions.get_session_permission_roles(self.owner, session),
            {"owner", "secret_keeper"},
        )
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant__session=session,
                participant__user=self.owner,
                role=SessionParticipantRole.Role.GM,
            ).exists()
        )

    def test_participant_identity_can_be_group_or_user_scoped(self):
        identity = ParticipantIdentity.objects.create(
            display_name="Alice Player",
            group=self.group,
            user=self.player,
            created_by=self.owner,
        )

        self.assertEqual(identity.normalized_name, "alice player")
        self.assertEqual(identity.group, self.group)
        self.assertEqual(identity.user, self.player)
        self.assertEqual(identity.created_by, self.owner)


class SessionPermissionViewMigrationTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="view-owner", email="view-owner@example.com", password="pass")
        self.gm = User.objects.create_user(username="view-gm", email="view-gm@example.com", password="pass")
        self.manager = User.objects.create_user(
            username="view-manager",
            email="view-manager@example.com",
            password="pass",
        )
        self.observer = User.objects.create_user(
            username="view-observer",
            email="view-observer@example.com",
            password="pass",
        )
        self.group_admin = User.objects.create_user(
            username="view-group-admin",
            email="view-group-admin@example.com",
            password="pass",
        )
        self.group = Group.objects.create(name="View Permission Group", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.gm, role="member")
        GroupMembership.objects.create(group=self.group, user=self.manager, role="member")
        GroupMembership.objects.create(group=self.group, user=self.observer, role="member")
        GroupMembership.objects.create(group=self.group, user=self.group_admin, role="admin")

    def _create_session(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("session-list"),
            {
                "title": "View Migration Session",
                "date": (timezone.now() + timedelta(days=1)).isoformat(),
                "group": self.group.id,
                "visibility": "group",
                "duration_minutes": 180,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return TRPGSession.objects.get(pk=response.data["id"])

    def test_session_creator_is_owner_not_secret_keeper_by_default(self):
        session = self._create_session()

        self.assertIsNone(session.gm_id)
        self.assertTrue(
            SessionPermission.objects.filter(session=session, user=self.owner, role="owner").exists()
        )
        self.assertFalse(
            SessionPermission.objects.filter(session=session, user=self.owner, role="secret_keeper").exists()
        )

        update = self.client.patch(
            reverse("session-detail", kwargs={"pk": session.id}),
            {"location": "Updated Discord"},
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)

        handout_management = self.client.get(
            f"/api/schedules/sessions/{session.id}/handouts/manage/",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(handout_management.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_creator_can_create_self_as_gm(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("session-list"),
            {
                "title": "Self GM Session",
                "date": (timezone.now() + timedelta(days=1)).isoformat(),
                "group": self.group.id,
                "visibility": "group",
                "duration_minutes": 180,
                "as_gm": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(pk=response.data["id"])
        self.assertEqual(session.gm_id, self.owner.id)
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant__session=session,
                participant__user=self.owner,
                role=SessionParticipantRole.Role.GM,
            ).exists()
        )
        self.assertTrue(
            SessionPermission.objects.filter(
                session=session,
                user=self.owner,
                role=SessionPermission.Role.SECRET_KEEPER,
            ).exists()
        )

    def test_assigning_gm_grants_participant_role_and_secret_keeper(self):
        session = self._create_session()

        response = self.client.post(
            reverse("session-assign-roles", kwargs={"pk": session.id}),
            {"gm_user_id": self.gm.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.gm, self.gm)
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant__session=session,
                participant__user=self.gm,
                role="gm",
            ).exists()
        )
        self.assertTrue(
            SessionPermission.objects.filter(session=session, user=self.gm, role="secret_keeper").exists()
        )

        self.client.force_authenticate(user=self.gm)
        handout_management = self.client.get(
            f"/api/schedules/sessions/{session.id}/handouts/manage/",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(handout_management.status_code, status.HTTP_200_OK)

    def test_participant_create_rejects_legacy_role_key_and_accepts_roles(self):
        session = self._create_session()

        legacy_response = self.client.post(
            reverse("participant-list"),
            {
                "session": session.id,
                "user": self.gm.id,
                "role": "player",
            },
            format="json",
        )
        self.assertEqual(legacy_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", str(legacy_response.data))

        response = self.client.post(
            reverse("participant-list"),
            {
                "session": session.id,
                "user": self.gm.id,
                "roles": ["player"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant__session=session,
                participant__user=self.gm,
                role="player",
            ).exists()
        )

    def test_participant_update_rejects_legacy_role_key_and_accepts_roles(self):
        session = self._create_session()
        participant = session_permissions.create_participant(
            session=session,
            user=self.gm,
            role="player",
            granted_by=self.owner,
        )

        legacy_response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": participant.id}),
            {"role": "gm"},
            format="json",
        )
        self.assertEqual(legacy_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", str(legacy_response.data))

        response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": participant.id}),
            {"roles": ["gm", "player"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant=participant,
                role="gm",
            ).exists()
        )
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant=participant,
                role="player",
            ).exists()
        )

    def test_participant_update_accepts_repeated_form_roles(self):
        session = self._create_session()
        participant = session_permissions.create_participant(
            session=session,
            user=self.gm,
            role="player",
            granted_by=self.owner,
        )

        response = self.client.generic(
            "PATCH",
            reverse("participant-detail", kwargs={"pk": participant.id}),
            "roles=gm&roles=player",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(participant.participant_roles.values_list("role", flat=True)),
            {"gm", "player"},
        )

    def test_assign_roles_rejects_legacy_role_key_and_accepts_roles(self):
        session = self._create_session()

        legacy_response = self.client.post(
            reverse("session-assign-roles", kwargs={"pk": session.id}),
            {
                "participants": [
                    {"user_id": self.gm.id, "role": "player"},
                ],
            },
            format="json",
        )
        self.assertEqual(legacy_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", str(legacy_response.data))

        response = self.client.post(
            reverse("session-assign-roles", kwargs={"pk": session.id}),
            {
                "participants": [
                    {"user_id": self.gm.id, "roles": ["player"]},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            SessionParticipantRole.objects.filter(
                participant__session=session,
                participant__user=self.gm,
                role="player",
            ).exists()
        )

    def test_invite_rejects_legacy_role_key_and_accepts_roles(self):
        session = self._create_session()

        legacy_response = self.client.post(
            reverse("session-invite", kwargs={"pk": session.id}),
            {"user_id": self.gm.id, "role": "gm"},
            format="json",
        )
        self.assertEqual(legacy_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", str(legacy_response.data))

        response = self.client.post(
            reverse("session-invite", kwargs={"pk": session.id}),
            {"user_id": self.gm.id, "roles": ["gm"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation = self.gm.received_session_invitations.get(session=session)
        self.assertEqual(invitation.invited_role, "gm")

    def test_permissions_api_owner_can_list_grant_and_revoke_secret_keeper(self):
        session = self._create_session()

        list_response = self.client.get(reverse("session-permissions", kwargs={"pk": session.id}))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        owner_row = next(row for row in list_response.data["users"] if row["user_id"] == self.owner.id)
        self.assertEqual(owner_row["permission_roles"], ["owner"])

        grant_response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": session.id}),
            {
                "user_id": self.gm.id,
                "permission_roles": ["manager", "secret_keeper"],
            },
            format="json",
        )
        self.assertEqual(grant_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            SessionPermission.objects.filter(
                session=session,
                user=self.gm,
                role=SessionPermission.Role.SECRET_KEEPER,
            ).exists()
        )

        self.client.force_authenticate(user=self.gm)
        handout_management = self.client.get(
            f"/api/schedules/sessions/{session.id}/handouts/manage/",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(handout_management.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.owner)
        revoke_response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": session.id}),
            {
                "user_id": self.gm.id,
                "permission_roles": ["manager"],
            },
            format="json",
        )
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            SessionPermission.objects.filter(
                session=session,
                user=self.gm,
                role=SessionPermission.Role.SECRET_KEEPER,
            ).exists()
        )

        self.client.force_authenticate(user=self.gm)
        handout_management = self.client.get(
            f"/api/schedules/sessions/{session.id}/handouts/manage/",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(handout_management.status_code, status.HTTP_403_FORBIDDEN)

    def test_permissions_api_rejects_manager_and_allows_group_admin_without_secret_access(self):
        session = self._create_session()
        session_permissions.grant_session_permission(
            session,
            self.manager,
            SessionPermission.Role.MANAGER,
            granted_by=self.owner,
        )

        self.client.force_authenticate(user=self.manager)
        manager_response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": session.id}),
            {
                "user_id": self.gm.id,
                "permission_roles": ["secret_keeper"],
            },
            format="json",
        )
        self.assertEqual(manager_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.group_admin)
        handout_management = self.client.get(
            f"/api/schedules/sessions/{session.id}/handouts/manage/",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(handout_management.status_code, status.HTTP_403_FORBIDDEN)

        admin_response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": session.id}),
            {
                "user_id": self.gm.id,
                "permission_roles": ["secret_keeper"],
            },
            format="json",
        )
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            SessionPermission.objects.filter(
                session=session,
                user=self.gm,
                role=SessionPermission.Role.SECRET_KEEPER,
            ).exists()
        )

    def test_participant_api_updates_registered_and_guest_multiple_roles(self):
        session = self._create_session()
        registered = session_permissions.create_participant(
            session=session,
            user=self.gm,
            role="player",
            granted_by=self.owner,
        )
        guest = session_permissions.create_participant(
            session=session,
            user=None,
            guest_name="Guest Observer",
            role="player",
            granted_by=self.owner,
        )

        registered_response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": registered.id}),
            {"roles": ["gm", "player"]},
            format="json",
        )
        self.assertEqual(registered_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(registered.participant_roles.values_list("role", flat=True)),
            {"gm", "player"},
        )

        guest_response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": guest.id}),
            {"roles": ["gm", "observer"], "player_slot": None},
            format="json",
        )
        self.assertEqual(guest_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(guest.participant_roles.values_list("role", flat=True)),
            {"gm", "observer"},
        )

    def test_participant_api_adds_group_temporary_member_with_multiple_roles(self):
        session = self._create_session()
        identity = ParticipantIdentity.objects.create(
            group=self.group,
            created_by=self.owner,
            display_name="Temporary Keeper",
        )

        response = self.client.post(
            reverse("participant-list"),
            {
                "session": session.id,
                "participant_identity": identity.id,
                "roles": ["gm", "player"],
                "player_slot": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        participant = SessionParticipant.objects.get(pk=response.data["id"])
        self.assertEqual(participant.participant_identity_id, identity.id)
        self.assertEqual(participant.guest_name, "Temporary Keeper")
        self.assertEqual(participant.player_slot, 2)
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm", "player"})

    def test_participant_api_rejects_temporary_member_from_other_group(self):
        session = self._create_session()
        other_group = Group.objects.create(name="Other Group", created_by=self.owner)
        GroupMembership.objects.create(group=other_group, user=self.owner, role="admin")
        identity = ParticipantIdentity.objects.create(
            group=other_group,
            created_by=self.owner,
            display_name="Wrong Group Guest",
        )

        response = self.client.post(
            reverse("participant-list"),
            {
                "session": session.id,
                "participant_identity": identity.id,
                "roles": ["player"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SessionParticipant.objects.filter(session=session, participant_identity=identity).exists())

    def test_participant_claim_request_requires_manager_approval(self):
        session = self._create_session()
        identity = ParticipantIdentity.objects.create(
            group=self.group,
            created_by=self.owner,
            display_name="Claimable Guest",
        )
        participant = session_permissions.create_participant(
            session=session,
            participant_identity=identity,
            user=None,
            guest_name=identity.display_name,
            roles=[SessionParticipantRole.Role.PLAYER],
            granted_by=self.owner,
        )

        self.client.force_authenticate(user=self.observer)
        request_response = self.client.post(
            f"/api/participants/{participant.id}/claim-requests/",
            {"message": "これは自分です"},
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_201_CREATED)
        participant.refresh_from_db()
        self.assertIsNone(participant.user_id)

        claim = ParticipantClaimRequest.objects.get(pk=request_response.data["id"])
        self.assertEqual(claim.status, ParticipantClaimRequest.Status.PENDING)

        own_approve_response = self.client.post(
            f"/api/sessions/{session.id}/claim-requests/{claim.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(own_approve_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.owner)
        list_response = self.client.get(f"/api/sessions/{session.id}/claim-requests/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["claim_requests"]), 1)

        approve_response = self.client.post(
            f"/api/sessions/{session.id}/claim-requests/{claim.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        identity.refresh_from_db()
        claim.refresh_from_db()
        self.assertEqual(participant.user_id, self.observer.id)
        self.assertEqual(participant.guest_name, "")
        self.assertEqual(identity.user_id, self.observer.id)
        self.assertEqual(claim.status, ParticipantClaimRequest.Status.APPROVED)

    def test_invite_accepts_observer_and_still_rejects_multi_role_invite(self):
        session = self._create_session()

        response = self.client.post(
            reverse("session-invite", kwargs={"pk": session.id}),
            {"user_id": self.observer.id, "roles": ["observer"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation = self.observer.received_session_invitations.get(session=session)
        self.assertEqual(invitation.invited_role, "observer")

        response = self.client.post(
            reverse("session-invite", kwargs={"pk": session.id}),
            {"user_id": self.manager.id, "roles": ["gm", "player"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.observer)
        accept_response = self.client.post(
            reverse("session-invitation-accept", kwargs={"pk": invitation.id}),
            {},
            format="json",
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        participant = SessionParticipant.objects.get(session=session, user=self.observer)
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"observer"})

    def test_session_detail_renders_permission_and_role_controls_by_permission_level(self):
        session = self._create_session()
        session_permissions.create_participant(
            session=session,
            user=self.gm,
            role="player",
            granted_by=self.owner,
        )
        session_permissions.create_participant(
            session=session,
            user=None,
            guest_name="Guest Player",
            role="player",
            granted_by=self.owner,
        )

        response = self.client.get(
            f"/api/schedules/sessions/{session.id}/detail/",
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="sessionPermissionsModal"')
        self.assertContains(response, "session-permission-checkbox")
        self.assertContains(response, "participant-role-checkbox")
        self.assertContains(response, 'value="observer"')
        self.assertContains(response, 'id="guest_role_observer"')
        self.assertContains(response, 'id="guest_participant_identity"')
        self.assertContains(response, "loadGroupTemporaryMembers")
        self.assertContains(response, "sessionClaimRequestsList")

        session_permissions.grant_session_permission(
            session,
            self.manager,
            SessionPermission.Role.MANAGER,
            granted_by=self.owner,
        )
        self.client.force_authenticate(user=self.manager)
        manager_response = self.client.get(
            f"/api/schedules/sessions/{session.id}/detail/",
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(manager_response.status_code, status.HTTP_200_OK)
        self.assertNotContains(manager_response, 'id="sessionPermissionsModal"')
        self.assertContains(manager_response, "participant-role-checkbox")


class SessionPermissionDataMigrationTestCase(TransactionTestCase):
    migrate_from = "0045_remove_legacy_participant_identity_fields"
    migrate_to = "0046_session_permission_model"

    def _targets_for(self, schedules_migration):
        return [
            target
            for target in self.executor.loader.graph.leaf_nodes()
            if target[0] != "schedules"
        ] + [("schedules", schedules_migration)]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self._targets_for(self.migrate_from))
        self.old_targets = self._targets_for(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.old_targets).apps

    def tearDown(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self._targets_for(self.migrate_to))
        super().tearDown()

    def test_legacy_session_roles_and_permissions_are_backfilled(self):
        UserModel = self.old_apps.get_model("accounts", "CustomUser")
        GroupModel = self.old_apps.get_model("accounts", "Group")
        TRPGSessionModel = self.old_apps.get_model("schedules", "TRPGSession")
        SessionParticipantModel = self.old_apps.get_model("schedules", "SessionParticipant")
        ParticipantIdentityModel = self.old_apps.get_model("schedules", "ParticipantIdentity")

        owner = UserModel.objects.create(username="legacy-owner", email="owner@example.com")
        gm = UserModel.objects.create(username="legacy-gm", email="gm@example.com")
        player = UserModel.objects.create(username="legacy-player", email="player@example.com")
        group = GroupModel.objects.create(name="Legacy Group", created_by=owner)
        session = TRPGSessionModel.objects.create(
            title="Legacy Session",
            created_by=owner,
            gm=gm,
            group=group,
            date=timezone.now() + timedelta(days=1),
        )
        gm_participant = SessionParticipantModel.objects.create(
            session=session,
            user=gm,
            role="player",
        )
        player_identity = ParticipantIdentityModel.objects.create(display_name="Legacy Player")
        player_participant = SessionParticipantModel.objects.create(
            session=session,
            user=player,
            participant_identity=player_identity,
            role="player",
        )

        self.executor.loader.build_graph()
        self.executor.migrate(self._targets_for(self.migrate_to))
        new_targets = self._targets_for(self.migrate_to)
        new_apps = self.executor.loader.project_state(new_targets).apps
        SessionPermissionModel = new_apps.get_model("schedules", "SessionPermission")
        SessionParticipantRoleModel = new_apps.get_model("schedules", "SessionParticipantRole")
        ParticipantIdentityNewModel = new_apps.get_model("schedules", "ParticipantIdentity")

        self.assertTrue(
            SessionPermissionModel.objects.filter(
                session_id=session.id,
                user_id=owner.id,
                role="owner",
            ).exists()
        )
        self.assertTrue(
            SessionPermissionModel.objects.filter(
                session_id=session.id,
                user_id=gm.id,
                role="secret_keeper",
            ).exists()
        )
        self.assertEqual(
            set(
                SessionParticipantRoleModel.objects.filter(participant_id=gm_participant.id).values_list(
                    "role",
                    flat=True,
                )
            ),
            {"player", "gm"},
        )
        self.assertEqual(
            set(
                SessionParticipantRoleModel.objects.filter(participant_id=player_participant.id).values_list(
                    "role",
                    flat=True,
                )
            ),
            {"player"},
        )

        player_identity = ParticipantIdentityNewModel.objects.get(pk=player_identity.id)
        self.assertEqual(player_identity.group_id, group.id)
        self.assertEqual(player_identity.user_id, player.id)
