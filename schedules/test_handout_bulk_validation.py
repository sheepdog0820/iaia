from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from schedules import session_permissions
from schedules.models import HandoutInfo, TRPGSession


class HandoutBulkValidationTests(APITestCase):
    def setUp(self):
        self.gm = get_user_model().objects.create_user(username="bulk_handout_gm")
        self.player = get_user_model().objects.create_user(username="bulk_handout_player")
        self.session = TRPGSession.objects.create(title="一括作成", gm=self.gm, date=timezone.now())
        self.participant = session_permissions.create_participant(session=self.session, user=self.player, role="player")
        self.url = "/api/schedules/gm-handouts/bulk_create/"
        self.client.force_authenticate(self.gm)

    def test_invalid_collection_returns_japanese_validation_error_without_writes(self):
        for value in (None, 1, True, "invalid", {"title": "誤った形式"}):
            with self.subTest(value=value):
                response = self.client.post(self.url, {"session_id": self.session.pk, "handouts": value}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"], "ハンドアウトは配列で指定してください。")
                self.assertFalse(HandoutInfo.objects.exists())

    def test_valid_entries_keep_partial_success_and_japanese_item_errors(self):
        response = self.client.post(
            self.url,
            {
                "session_id": self.session.pk,
                "handouts": [
                    {"participant": self.participant.pk, "title": "配布資料", "content": "内容"},
                    None,
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(response.data["error_count"], 1)
        self.assertEqual(
            response.data["errors"][0]["errors"]["non_field_errors"],
            ["ハンドアウトは項目名と値の形式で指定してください。"],
        )
        self.assertEqual(HandoutInfo.objects.get().content, "内容")
