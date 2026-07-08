from datetime import timedelta

from django.apps import apps
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
    HandoutInfo,
    ParticipantClaimRequest,
    ParticipantIdentity,
    SessionParticipant,
    SessionParticipantRole,
    TRPGSession,
)


User = get_user_model()


class SessionRoleServiceTestCase(TestCase):
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
        self.group = Group.objects.create(name="Permission Group", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.group_admin, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.group_member, role="member")
        self.session = TRPGSession.objects.create(
            title="Permission Session",
            created_by=self.owner,
            group=self.group,
            visibility="group",
            date=timezone.now() + timedelta(days=1),
        )

    def test_owner_manager_and_gm_can_manage_but_only_gm_sees_secret_content(self):
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
            self.assertTrue(session_permissions.can_manage_share_links(user, self.session))
            self.assertTrue(session_permissions.can_manage_permissions(user, self.session))

        self.assertFalse(session_permissions.can_view_secret_content(self.owner, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.manager, self.session))
        self.assertTrue(session_permissions.can_view_secret_content(self.gm, self.session))

    def test_group_admin_can_manage_without_secret_access(self):
        self.assertTrue(session_permissions.can_edit_session_basic(self.group_admin, self.session))
        self.assertTrue(session_permissions.can_manage_participants(self.group_admin, self.session))
        self.assertTrue(session_permissions.can_manage_permissions(self.group_admin, self.session))
        self.assertFalse(session_permissions.can_view_secret_content(self.group_admin, self.session))

    def test_participant_role_is_single_and_observer_is_rejected(self):
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role=SessionParticipantRole.Role.PLAYER,
        )

        session_permissions.set_participant_roles(participant, [SessionParticipantRole.Role.GM])
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm"})

        session_permissions.set_participant_roles(participant, [SessionParticipantRole.Role.PLAYER])
        participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"player"})
        self.assertEqual(participant.participant_roles.count(), 1)

        with self.assertRaises(ValueError):
            session_permissions.set_participant_roles(participant, ["observer"])
        with self.assertRaises(ValueError):
            session_permissions.set_participant_roles(
                participant,
                [SessionParticipantRole.Role.GM, SessionParticipantRole.Role.PLAYER],
            )

    def test_create_session_with_permissions_creates_owner_participant_and_removes_permission_model(self):
        personal = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            title="Personal Session",
            visibility="private",
            date=timezone.now() + timedelta(days=2),
        )

        participant = SessionParticipant.objects.get(session=personal, user=self.owner)
        self.assertEqual(session_permissions.get_primary_participant_role(participant), "owner")
        self.assertIsNone(personal.group_id)
        self.assertFalse(session_permissions.can_view_secret_content(self.owner, personal))
        with self.assertRaises(LookupError):
            apps.get_model("schedules", "SessionPermission")

    def test_create_session_with_self_as_gm_keeps_creator_role_and_legacy_gm(self):
        session = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            gm=self.owner,
            title="Self GM Session",
            visibility="private",
            date=timezone.now() + timedelta(days=3),
        )

        participant = SessionParticipant.objects.get(session=session, user=self.owner)
        self.assertEqual(session.gm_id, self.owner.id)
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"owner"})
        self.assertTrue(session_permissions.is_session_gm(self.owner, session))
        self.assertTrue(session_permissions.can_view_secret_content(self.owner, session))


class SessionRoleApiTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="view-owner", email="view-owner@example.com", password="pass")
        self.gm = User.objects.create_user(username="view-gm", email="view-gm@example.com", password="pass")
        self.manager = User.objects.create_user(
            username="view-manager",
            email="view-manager@example.com",
            password="pass",
        )
        self.player = User.objects.create_user(
            username="view-player",
            email="view-player@example.com",
            password="pass",
        )
        self.group_member = User.objects.create_user(
            username="view-member",
            email="view-member@example.com",
            password="pass",
        )
        self.group = Group.objects.create(name="View Permission Group", created_by=self.owner)
        for user in [self.owner, self.gm, self.manager, self.player, self.group_member]:
            GroupMembership.objects.create(group=self.group, user=user, role="member")

        self.session = session_permissions.create_session_with_permissions(
            created_by=self.owner,
            title="View Migration Session",
            date=timezone.now() + timedelta(days=1),
            group=self.group,
            visibility="group",
            duration_minutes=180,
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

    def test_session_creator_is_owner_and_cannot_be_changed_from_permissions_api(self):
        response = self.client.get(reverse("session-permissions", kwargs={"pk": self.session.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner_row = next(row for row in response.data["users"] if row["user_id"] == self.owner.id)
        self.assertEqual(owner_row["participant_roles"], ["owner"])

        patch_response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": self.session.id}),
            {"participant_id": owner_row["participant_id"], "roles": ["player"]},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def test_permissions_api_switches_player_between_gm_and_pl_only(self):
        response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": self.session.id}),
            {"participant_id": self.player_participant.id, "roles": ["gm"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.player_participant.refresh_from_db()
        self.session.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(self.player_participant), {"gm"})
        self.assertEqual(self.session.gm_id, self.player.id)

        response = self.client.patch(
            reverse("session-permissions", kwargs={"pk": self.session.id}),
            {"participant_id": self.player_participant.id, "roles": ["manager"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_participant_create_update_accepts_one_visible_role(self):
        response = self.client.post(
            reverse("participant-list"),
            {
                "session": self.session.id,
                "user": self.group_member.id,
                "roles": ["gm"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        participant = SessionParticipant.objects.get(pk=response.data["id"])
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm"})

        update_response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": participant.id}),
            {"roles": ["player"]},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"player"})

        multi_role_response = self.client.patch(
            reverse("participant-detail", kwargs={"pk": participant.id}),
            {"roles": ["gm", "player"]},
            format="json",
        )
        self.assertEqual(multi_role_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_accepts_gm_or_player_and_rejects_observer_and_manager(self):
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

        self.client.force_authenticate(user=self.group_member)
        accept_response = self.client.post(
            reverse("session-invitation-accept", kwargs={"pk": invitation.id}),
            {},
            format="json",
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        participant = SessionParticipant.objects.get(session=self.session, user=self.group_member)
        self.assertEqual(session_permissions.get_participant_role_values(participant), {"gm"})

    def test_participant_claim_request_requires_manager_approval(self):
        identity = ParticipantIdentity.objects.create(
            group=self.group,
            created_by=self.owner,
            display_name="Claimable Guest",
        )
        participant = session_permissions.create_participant(
            session=self.session,
            participant_identity=identity,
            user=None,
            guest_name=identity.display_name,
            roles=[SessionParticipantRole.Role.PLAYER],
            granted_by=self.owner,
        )

        self.client.force_authenticate(user=self.group_member)
        request_response = self.client.post(
            f"/api/participants/{participant.id}/claim-requests/",
            {"message": "Please assign this guest to me."},
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_201_CREATED)
        claim = ParticipantClaimRequest.objects.get(pk=request_response.data["id"])
        self.assertEqual(claim.status, ParticipantClaimRequest.Status.PENDING)

        own_approve_response = self.client.post(
            f"/api/sessions/{self.session.id}/claim-requests/{claim.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(own_approve_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.owner)
        approve_response = self.client.post(
            f"/api/sessions/{self.session.id}/claim-requests/{claim.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        identity.refresh_from_db()
        claim.refresh_from_db()
        self.assertEqual(participant.user_id, self.group_member.id)
        self.assertEqual(participant.guest_name, "")
        self.assertEqual(identity.user_id, self.group_member.id)
        self.assertEqual(claim.status, ParticipantClaimRequest.Status.APPROVED)

    def test_session_detail_uses_permission_modal_and_removes_inline_role_controls(self):
        session_permissions.create_participant(
            session=self.session,
            user=None,
            guest_name="Guest Player",
            role=SessionParticipantRole.Role.PLAYER,
            granted_by=self.owner,
        )

        response = self.client.get(
            f"/api/schedules/sessions/{self.session.id}/detail/",
            HTTP_ACCEPT="text/html",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="sessionPermissionsModal"')
        self.assertContains(response, "permission-panel-participant-role-select")
        self.assertContains(response, "NPC設定")
        self.assertNotContains(response, "担当PC/NPC設定")
        self.assertNotContains(response, "担当PC/NPC:")
        self.assertContains(response, "GM")
        self.assertContains(response, "グループ管理者")
        self.assertContains(response, "ゲスト")
        self.assertNotContains(response, "メインGM")
        self.assertNotContains(response, "ゲスト参加者")
        self.assertNotContains(response, "main GM")
        self.assertNotContains(response, "group admin")
        self.assertNotContains(response, "guest participant")
        self.assertNotContains(response, "session-permission-checkbox")
        self.assertNotContains(response, "participant-role-checkbox")
        self.assertNotContains(response, 'value="observer"')
        self.assertNotContains(response, 'id="guest_role_observer"')
        self.assertNotContains(response, 'id="link_player_slot"')
        self.assertNotContains(response, 'id="guest_player_slot"')
        self.assertContains(response, 'id="guest_character_url_lookup_status"')
        self.assertContains(response, "タブレノのキャラクターURLの場合、キャラクター名を自動取得します。")

    def test_character_setting_player_slots_use_handout_options(self):
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.player_participant,
            title="探偵HO",
            content="",
            handout_number=1,
            assigned_player_slot=1,
        )
        HandoutInfo.objects.create(
            session=self.session,
            participant=self.player_participant,
            title="医師HO",
            content="",
            handout_number=3,
            assigned_player_slot=3,
        )

        response = self.client.get(
            f"/api/schedules/sessions/{self.session.id}/detail/",
            HTTP_ACCEPT="text/html",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="link_player_slot"')
        self.assertContains(response, 'id="guest_player_slot"')
        self.assertContains(response, "プレイヤー枠（ハンドアウト）")
        self.assertContains(response, 'value="1"')
        self.assertContains(response, "HO1")
        self.assertNotContains(response, "HO1: 探偵HO")
        self.assertContains(response, 'value="3"')
        self.assertContains(response, "HO3")
        self.assertNotContains(response, "HO3: 医師HO")
        self.assertNotContains(response, ">プレイヤー2<")

        self.client.force_authenticate(user=self.gm)
        response = self.client.get(
            f"/api/schedules/sessions/{self.session.id}/detail/",
            HTTP_ACCEPT="text/html",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="link_player_slot"')
        self.assertContains(response, 'id="guest_player_slot"')
        self.assertContains(response, 'value="1"')
        self.assertContains(response, "HO1: 探偵HO")
        self.assertContains(response, 'value="3"')
        self.assertContains(response, "HO3: 医師HO")
        self.assertNotContains(response, ">プレイヤー2<")


class SessionRoleDataMigrationTestCase(TransactionTestCase):
    migrate_from = "0050_participantclaimrequest"
    migrate_to = "0051_unify_session_roles"

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

    def test_legacy_permissions_and_observer_roles_are_unified(self):
        UserModel = self.old_apps.get_model("accounts", "CustomUser")
        GroupModel = self.old_apps.get_model("accounts", "Group")
        TRPGSessionModel = self.old_apps.get_model("schedules", "TRPGSession")
        SessionParticipantModel = self.old_apps.get_model("schedules", "SessionParticipant")
        SessionParticipantRoleModel = self.old_apps.get_model("schedules", "SessionParticipantRole")
        SessionPermissionModel = self.old_apps.get_model("schedules", "SessionPermission")
        SessionInvitationModel = self.old_apps.get_model("schedules", "SessionInvitation")

        owner = UserModel.objects.create(username="legacy-owner", email="owner@example.com")
        gm = UserModel.objects.create(username="legacy-gm", email="gm@example.com")
        manager = UserModel.objects.create(username="legacy-manager", email="manager@example.com")
        observer = UserModel.objects.create(username="legacy-observer", email="observer@example.com")
        group = GroupModel.objects.create(name="Legacy Group", created_by=owner)
        session = TRPGSessionModel.objects.create(
            title="Legacy Session",
            created_by=owner,
            gm=gm,
            group=group,
            date=timezone.now() + timedelta(days=1),
        )
        gm_participant = SessionParticipantModel.objects.create(session=session, user=gm)
        observer_participant = SessionParticipantModel.objects.create(session=session, user=observer)
        SessionParticipantRoleModel.objects.create(participant=gm_participant, role="player")
        SessionParticipantRoleModel.objects.create(participant=gm_participant, role="gm")
        SessionParticipantRoleModel.objects.create(participant=observer_participant, role="player")
        SessionParticipantRoleModel.objects.create(participant=observer_participant, role="observer")
        SessionPermissionModel.objects.create(session=session, user=owner, role="owner")
        SessionPermissionModel.objects.create(session=session, user=manager, role="manager")
        invitation = SessionInvitationModel.objects.create(
            session=session,
            inviter=owner,
            invitee=observer,
            invited_role="observer",
        )

        self.executor.loader.build_graph()
        self.executor.migrate(self._targets_for(self.migrate_to))
        new_apps = self.executor.loader.project_state(self._targets_for(self.migrate_to)).apps
        NewParticipant = new_apps.get_model("schedules", "SessionParticipant")
        NewParticipantRole = new_apps.get_model("schedules", "SessionParticipantRole")
        NewInvitation = new_apps.get_model("schedules", "SessionInvitation")

        with self.assertRaises(LookupError):
            new_apps.get_model("schedules", "SessionPermission")

        owner_participant = NewParticipant.objects.get(session_id=session.id, user_id=owner.id)
        manager_participant = NewParticipant.objects.get(session_id=session.id, user_id=manager.id)
        self.assertEqual(
            list(NewParticipantRole.objects.filter(participant=owner_participant).values_list("role", flat=True)),
            ["owner"],
        )
        self.assertEqual(
            list(NewParticipantRole.objects.filter(participant=manager_participant).values_list("role", flat=True)),
            ["manager"],
        )
        self.assertEqual(
            list(NewParticipantRole.objects.filter(participant_id=gm_participant.id).values_list("role", flat=True)),
            ["gm"],
        )
        self.assertEqual(
            list(
                NewParticipantRole.objects.filter(participant_id=observer_participant.id).values_list(
                    "role",
                    flat=True,
                )
            ),
            ["player"],
        )
        for participant in NewParticipant.objects.filter(session_id=session.id):
            self.assertEqual(NewParticipantRole.objects.filter(participant=participant).count(), 1)

        invitation = NewInvitation.objects.get(pk=invitation.id)
        self.assertEqual(invitation.invited_role, "player")
