from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import PlayHistory, Scenario


class PlayHistoryCacheTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="history-cache-owner")
        self.other = get_user_model().objects.create_user(username="history-cache-other")
        self.scenario = Scenario.objects.create(title="履歴確認", created_by=self.user, game_system="coc6")
        self.history = PlayHistory.objects.create(
            scenario=self.scenario, user=self.user, played_date=timezone.now(), role="gm", notes="変更前"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/scenarios/history/{self.history.pk}/"

    def assert_not_cached(self, response, status):
        self.assertEqual(response.status_code, status)
        directives = {item.strip() for item in response.get("Cache-Control", "").split(",")}
        self.assertTrue({"private", "no-store", "no-cache", "max-age=0"}.issubset(directives))

    def test_history_reads_and_writes_are_not_cached(self):
        self.assert_not_cached(self.client.get("/api/scenarios/history/?limit=8"), 200)
        self.assert_not_cached(self.client.get(self.url), 200)
        self.assert_not_cached(self.client.patch(self.url, {"notes": "変更後"}, format="json"), 200)
        self.assertEqual(self.client.get(self.url).data["notes"], "変更後")
        created = self.client.post(
            "/api/scenarios/history/",
            {"scenario": self.scenario.pk, "played_date": timezone.now().isoformat(), "role": "gm"},
            format="json",
        )
        self.assert_not_cached(created, 201)
        self.assert_not_cached(self.client.delete(self.url), 204)
        self.assert_not_cached(self.client.get(self.url), 404)

    def test_denials_are_not_cached_and_other_user_cannot_read_history(self):
        self.client.force_authenticate(self.other)
        self.assert_not_cached(self.client.get(self.url), 404)
        self.client.force_authenticate(None)
        self.assert_not_cached(self.client.get(self.url), 401)
