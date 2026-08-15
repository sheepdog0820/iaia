from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import SessionParticipant, TRPGSession

User = get_user_model()


class GrouplessSessionCreationAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="groupless-owner",
            email="groupless-owner@example.com",
            password="password",
            nickname="作成者",
        )
        self.invitee = User.objects.create_user(
            username="groupless-invitee",
            email="groupless-invitee@example.com",
            password="password",
            nickname="招待相手",
        )
        self.client.force_authenticate(self.owner)

    def test_omitted_group_and_visibility_create_private_session(self):
        response = self.client.post(
            "/api/schedules/sessions/",
            {"title": "個別セッション", "as_gm": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(pk=response.data["id"])
        self.assertIsNone(session.group)
        self.assertEqual(session.visibility, "private")
        self.assertFalse(Group.objects.filter(name__endswith=" Default Group").exists())

    def test_groupless_group_visibility_is_rejected(self):
        response = self.client.post(
            "/api/schedules/sessions/",
            {
                "title": "不正な公開範囲",
                "group": None,
                "visibility": "group",
                "as_gm": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["visibility"][0],
            "グループなしでは「グループ内のみ」を選択できません。",
        )
        self.assertFalse(TRPGSession.objects.filter(title="不正な公開範囲").exists())

    def test_group_session_keeps_group_visibility_default(self):
        group = Group.objects.create(name="所属グループ", created_by=self.owner)
        group.members.add(self.owner)

        response = self.client.post(
            "/api/schedules/sessions/",
            {"title": "グループセッション", "group": group.id, "as_gm": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(pk=response.data["id"])
        self.assertEqual(session.group, group)
        self.assertEqual(session.visibility, "group")

    def test_groupless_session_can_be_explicitly_public(self):
        response = self.client.post(
            "/api/schedules/sessions/",
            {
                "title": "公開個別セッション",
                "group": None,
                "visibility": "public",
                "as_gm": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(pk=response.data["id"])
        self.assertIsNone(session.group)
        self.assertEqual(session.visibility, "public")

        self.client.force_authenticate(self.invitee)
        detail_response = self.client.get(f"/api/schedules/sessions/{session.id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_private_groupless_session_becomes_visible_after_invitation_acceptance(self):
        create_response = self.client.post(
            "/api/schedules/sessions/",
            {
                "title": "招待制個別セッション",
                "group": None,
                "visibility": "private",
                "as_gm": True,
            },
            format="json",
        )
        session_id = create_response.data["id"]

        invite_response = self.client.post(
            f"/api/schedules/sessions/{session_id}/invite/",
            {"user_id": self.invitee.id},
            format="json",
        )
        self.assertEqual(invite_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.invitee)
        hidden_response = self.client.get(f"/api/schedules/sessions/{session_id}/")
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

        accept_response = self.client.post(
            f"/api/schedules/session-invitations/{invite_response.data['invitation_id']}/accept/"
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertTrue(SessionParticipant.objects.filter(session_id=session_id, user=self.invitee).exists())

        visible_response = self.client.get(f"/api/schedules/sessions/{session_id}/")
        self.assertEqual(visible_response.status_code, status.HTTP_200_OK)


class GrouplessSessionModelDefaultsTests(APITestCase):
    def test_new_session_model_defaults_to_private_without_creating_group(self):
        owner = User.objects.create_user(username="model-owner", password="password")

        session = TRPGSession.objects.create(title="モデル既定値", gm=owner, created_by=owner)

        self.assertIsNone(session.group)
        self.assertEqual(session.visibility, "private")
        self.assertFalse(Group.objects.filter(name__endswith=" Default Group").exists())
