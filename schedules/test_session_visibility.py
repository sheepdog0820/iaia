from schedules import session_permissions
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import HandoutInfo, SessionParticipant, TRPGSession

User = get_user_model()


class SessionVisibilitySerializerTestCase(APITestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username="session_visibility_gm",
            email="session_visibility_gm@example.com",
            password="pass1234",
        )
        self.player = User.objects.create_user(
            username="session_visibility_player",
            email="session_visibility_player@example.com",
            password="pass1234",
        )
        self.outsider = User.objects.create_user(
            username="session_visibility_outsider",
            email="session_visibility_outsider@example.com",
            password="pass1234",
        )
        self.group = Group.objects.create(
            name="Session Visibility Group",
            created_by=self.gm,
            visibility="public",
        )
        self.session = TRPGSession.objects.create(
            title="Public session with private handouts",
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            visibility="public",
        )
        self.participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role="player",
            player_slot=1,
        )
        self.secret_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant,
            title="Secret handout title",
            content="Secret handout content",
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1,
        )
        self.shared_handout = HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant,
            title="Shared handout title",
            content="Shared handout content",
            is_secret=False,
            handout_number=2,
        )

    def test_public_session_detail_hides_handouts_from_non_participant(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["handouts_detail"], [])
        self.assertNotIn("email", response.data["gm_detail"])
        self.assertNotIn("trpg_history", response.data["gm_detail"])
        participant_detail = response.data["participants_detail"][0]["user_detail"]
        self.assertNotIn("email", participant_detail)
        self.assertNotIn("trpg_history", participant_detail)

    def test_public_session_detail_shows_visible_handouts_to_participant(self):
        self.client.force_authenticate(user=self.player)

        response = self.client.get(f"/api/schedules/sessions/{self.session.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        handout_ids = {handout["id"] for handout in response.data["handouts_detail"]}
        self.assertEqual(handout_ids, {self.secret_handout.id, self.shared_handout.id})
        for handout in response.data["handouts_detail"]:
            user_detail = handout["participant_detail"]["user_detail"]
            self.assertNotIn("email", user_detail)
            self.assertNotIn("trpg_history", user_detail)

    def test_session_detail_json_uses_request_context_for_handout_visibility(self):
        self.client.force_authenticate(user=self.player)

        response = self.client.get(
            f"/api/schedules/sessions/{self.session.id}/detail/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        handout_ids = {handout["id"] for handout in response.data["handouts_detail"]}
        self.assertEqual(handout_ids, {self.secret_handout.id, self.shared_handout.id})

    def test_session_detail_json_hides_handouts_from_non_participant(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(
            f"/api/schedules/sessions/{self.session.id}/detail/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["handouts_detail"], [])

    def test_private_session_share_token_url_is_not_publicly_readable(self):
        private_session = TRPGSession.objects.create(
            title="Private token session",
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            visibility="private",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/sessions/{private_session.share_token}/view/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotContains(
            response,
            private_session.title,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def test_private_session_short_share_url_is_not_publicly_readable(self):
        private_session = TRPGSession.objects.create(
            title="Private short token session",
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            visibility="private",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/s/{private_session.share_token}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotContains(
            response,
            private_session.title,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def test_group_session_share_token_url_is_not_publicly_readable(self):
        group_session = TRPGSession.objects.create(
            title="Group token session",
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            visibility="group",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/sessions/{group_session.share_token}/view/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotContains(
            response,
            group_session.title,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def test_group_session_short_share_url_is_not_publicly_readable(self):
        group_session = TRPGSession.objects.create(
            title="Group short token session",
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            visibility="group",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/s/{group_session.share_token}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotContains(
            response,
            group_session.title,
            status_code=status.HTTP_404_NOT_FOUND,
        )
