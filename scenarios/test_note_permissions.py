from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Scenario, ScenarioNote


class ScenarioNotePermissionTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="note-owner")
        self.reader = get_user_model().objects.create_user(username="note-reader")
        self.scenario = Scenario.objects.create(title="公開シナリオ", created_by=self.owner, visibility="public")
        self.note = ScenarioNote.objects.create(
            scenario=self.scenario, user=self.owner, title="作成者のメモ", content="元の内容", is_private=False
        )
        self.url = f"/api/scenarios/notes/{self.note.pk}/"

    def test_other_user_can_read_public_note(self):
        self.client.force_authenticate(self.reader)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["content"], "元の内容")

    def test_other_user_cannot_modify_or_delete_public_note(self):
        self.client.force_authenticate(self.reader)
        for method in ("patch", "put", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url,
                    {"scenario": self.scenario.pk, "title": "改変", "content": "変更内容", "is_private": False},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(str(response.data["detail"]), "メモの変更・削除は作成者のみ可能です。")
                self.note.refresh_from_db()
                self.assertEqual(self.note.title, "作成者のメモ")
                self.assertEqual(self.note.content, "元の内容")
                self.assertFalse(self.note.is_private)

    def test_other_user_cannot_access_private_note(self):
        self.note.is_private = True
        self.note.save(update_fields=["is_private"])
        self.client.force_authenticate(self.reader)
        for method in ("get", "patch", "put", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.url).status_code, 404)

    def test_owner_can_update_and_delete_private_note(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(self.url, {"is_private": True, "content": "更新済み"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.put(
            self.url,
            {"scenario": self.scenario.pk, "title": "更新", "content": "再更新", "is_private": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(self.url).data["content"], "再更新")
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(ScenarioNote.objects.filter(pk=self.note.pk).exists())

    def test_anonymous_user_cannot_read_or_modify_note(self):
        for method in ("get", "patch", "put", "delete"):
            with self.subTest(method=method):
                self.assertIn(getattr(self.client, method)(self.url).status_code, (401, 403))
