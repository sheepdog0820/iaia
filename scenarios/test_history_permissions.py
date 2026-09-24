from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Group
from schedules.models import TRPGSession

from .models import PlayHistory, Scenario


class PlayHistoryPermissionTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="history-private-owner")
        self.reader = get_user_model().objects.create_user(username="history-private-reader")
        self.hidden = Scenario.objects.create(title="非公開題名", created_by=self.owner, visibility="private")
        self.visible = Scenario.objects.create(title="公開題名", created_by=self.owner, visibility="public")
        group = Group.objects.create(name="非公開グループ", created_by=self.owner)
        self.session = TRPGSession.objects.create(
            title="非公開セッション", gm=self.owner, group=group, visibility="private"
        )
        self.client.force_authenticate(self.reader)
        self.payload = {"scenario": self.visible.pk, "played_date": timezone.now().isoformat(), "role": "player"}

    def test_cannot_create_history_for_unreadable_scenario(self):
        response = self.client.post(
            "/api/scenarios/history/", {**self.payload, "scenario": self.hidden.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.hidden.title, str(response.data))
        self.assertFalse(PlayHistory.objects.filter(user=self.reader).exists())

    def test_cannot_create_history_for_unreadable_session(self):
        response = self.client.post(
            "/api/scenarios/history/", {**self.payload, "session": self.session.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.session.title, str(response.data))

    def test_cannot_retarget_own_history_to_unreadable_objects(self):
        history = PlayHistory.objects.create(
            user=self.reader, scenario=self.visible, played_date=timezone.now(), role="player"
        )
        for data in ({"scenario": self.hidden.pk}, {"session": self.session.pk}):
            with self.subTest(data=data):
                response = self.client.patch(f"/api/scenarios/history/{history.pk}/", data, format="json")
                self.assertEqual(response.status_code, 400)
        history.refresh_from_db()
        self.assertEqual(history.scenario_id, self.visible.pk)
        self.assertIsNone(history.session_id)

    def test_existing_history_does_not_disclose_revoked_related_objects(self):
        history = PlayHistory.objects.create(
            user=self.reader,
            scenario=self.hidden,
            session=self.session,
            played_date=timezone.now(),
            role="player",
            notes="自分の記録",
        )
        for url in ("/api/scenarios/history/", f"/api/scenarios/history/{history.pk}/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(self.hidden.title, str(response.data))
            self.assertNotIn(self.session.title, str(response.data))
            self.assertIn("自分の記録", str(response.data))

    def test_public_scenario_and_null_session_are_allowed(self):
        response = self.client.post("/api/scenarios/history/", {**self.payload, "session": None}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["scenario_detail"]["title"], self.visible.title)

    def test_owner_can_record_own_private_scenario(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/scenarios/history/", {**self.payload, "scenario": self.hidden.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["scenario_detail"]["title"], self.hidden.title)

    def test_owner_can_record_private_session(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/scenarios/history/", {**self.payload, "session": self.session.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["session_title"], self.session.title)

    def test_public_session_is_allowed_then_redacted_when_made_private(self):
        self.session.visibility = "public"
        self.session.save(update_fields=["visibility"])
        response = self.client.post(
            "/api/scenarios/history/", {**self.payload, "session": self.session.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.session.visibility = "private"
        self.session.save(update_fields=["visibility"])
        response = self.client.get(f"/api/scenarios/history/{response.data['id']}/")
        self.assertIsNone(response.data["session"])
        self.assertNotIn("session_title", response.data)

    def test_history_notes_remain_editable_after_scenario_visibility_changes(self):
        response = self.client.post("/api/scenarios/history/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.visible.visibility = "private"
        self.visible.save(update_fields=["visibility"])
        response = self.client.patch(
            f"/api/scenarios/history/{response.data['id']}/", {"notes": "自分の追記"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notes"], "自分の追記")
        self.assertEqual(response.data["scenario_detail"]["title"], "閲覧できないシナリオ")
        self.assertNotIn(self.visible.title, str(response.data))
