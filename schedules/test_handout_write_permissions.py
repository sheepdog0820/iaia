from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from schedules import session_permissions
from schedules.models import HandoutInfo, TRPGSession


class HandoutWritePermissionTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gm = user_model.objects.create_user(username="handout_writer")
        self.player = user_model.objects.create_user(username="handout_reader")
        self.other_gm = user_model.objects.create_user(username="other_handout_writer")
        self.session = TRPGSession.objects.create(title="元の卓", gm=self.gm, date=timezone.now())
        self.destination = TRPGSession.objects.create(title="別の卓", gm=self.other_gm, date=timezone.now())
        self.participant = session_permissions.create_participant(session=self.session, user=self.player, role="player")
        self.destination_participant = session_permissions.create_participant(
            session=self.destination, user=self.player, role="player"
        )

    def create_handout(self, is_secret=True):
        return HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant,
            title="個別情報",
            content="元の内容",
            is_secret=is_secret,
        )

    def test_recipient_cannot_modify_or_delete_readable_handouts(self):
        self.client.force_authenticate(self.player)
        for endpoint in ("handouts", "gm-handouts"):
            for is_secret in (True, False):
                for method in ("patch", "put", "delete"):
                    with self.subTest(endpoint=endpoint, secret=is_secret, method=method):
                        handout = self.create_handout(is_secret)
                        url = f"/api/schedules/{endpoint}/{handout.pk}/"
                        self.assertEqual(self.client.get(url).status_code, 200)
                        payload = {
                            "session": self.session.pk,
                            "participant": self.participant.pk,
                            "title": "改変",
                            "content": "改変",
                            # Handout visibility flag, not an authentication secret.
                            "is_secret": False,  # nosec B105
                        }
                        response = getattr(self.client, method)(url, payload, format="json")
                        self.assertEqual(response.status_code, 403)
                        handout.refresh_from_db()
                        self.assertEqual(handout.title, "個別情報")
                        self.assertEqual(handout.content, "元の内容")
                        self.assertEqual(handout.is_secret, is_secret)

    def test_gm_cannot_move_handout_to_another_managers_session(self):
        self.client.force_authenticate(self.gm)
        for endpoint in ("handouts", "gm-handouts"):
            with self.subTest(endpoint=endpoint):
                handout = self.create_handout()
                response = self.client.patch(
                    f"/api/schedules/{endpoint}/{handout.pk}/",
                    {"session": self.destination.pk, "participant": self.destination_participant.pk},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)
                handout.refresh_from_db()
                self.assertEqual(handout.session_id, self.session.pk)
                self.assertEqual(handout.participant_id, self.participant.pk)

    def test_gm_can_update_and_delete_own_handout(self):
        self.client.force_authenticate(self.gm)
        for endpoint in ("handouts", "gm-handouts"):
            with self.subTest(endpoint=endpoint):
                handout = self.create_handout()
                url = f"/api/schedules/{endpoint}/{handout.pk}/"
                response = self.client.patch(url, {"content": "更新済み"}, format="json")
                self.assertEqual(response.status_code, 200)
                handout.refresh_from_db()
                self.assertEqual(handout.content, "更新済み")
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertFalse(HandoutInfo.objects.filter(pk=handout.pk).exists())

    def test_gm_can_move_handout_between_managed_sessions(self):
        self.destination.gm = self.gm
        self.destination.save(update_fields=["gm"])
        self.client.force_authenticate(self.gm)
        for endpoint in ("handouts", "gm-handouts"):
            with self.subTest(endpoint=endpoint):
                handout = self.create_handout()
                response = self.client.patch(
                    f"/api/schedules/{endpoint}/{handout.pk}/",
                    {"session": self.destination.pk, "participant": self.destination_participant.pk},
                    format="json",
                )
                self.assertEqual(response.status_code, 200)
                handout.refresh_from_db()
                self.assertEqual(handout.session_id, self.destination.pk)

    def test_delegated_gm_can_manage_handout(self):
        session_permissions.create_participant(session=self.session, user=self.other_gm, role="gm")
        self.client.force_authenticate(self.other_gm)
        for endpoint in ("handouts", "gm-handouts"):
            with self.subTest(endpoint=endpoint):
                handout = self.create_handout()
                url = f"/api/schedules/{endpoint}/{handout.pk}/"
                self.assertEqual(self.client.patch(url, {"content": "共同GM更新"}).status_code, 200)
                self.assertEqual(self.client.delete(url).status_code, 204)
