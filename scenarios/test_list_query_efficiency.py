from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import CustomUser, Group, GroupMembership
from scenarios.models import PlayHistory, Scenario, ScenarioHandout, ScenarioHandoutRecommendedSkill
from schedules.models import TRPGSession


class ScenarioListQueryTests(APITestCase):
    def test_query_count_stays_bounded_with_nested_handouts_and_history(self):
        user = CustomUser.objects.create_user(username="scenario-query-owner")
        self.client.force_authenticate(user)
        expected = {}
        for number in range(5):
            scenario = Scenario.objects.create(title=f"試験{number}", created_by=user, gm_notes="所有者メモ")
            session = TRPGSession.objects.create(
                title="記録", gm=user, duration_minutes=120, actual_duration_minutes=90
            )
            for unused in range(2):
                PlayHistory.objects.create(
                    scenario=scenario, user=user, session=session, played_date=timezone.now(), role="gm"
                )
            PlayHistory.objects.create(scenario=scenario, user=user, played_date=timezone.now(), role="player")
            handout = ScenarioHandout.objects.create(scenario=scenario, code="HO1", name="秘密", is_secret=True)
            ScenarioHandoutRecommendedSkill.objects.create(handout=handout, name="目星")
            expected[scenario.pk] = (3, 180)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/api/scenarios/scenarios/")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 6)
        for row in response.data:
            self.assertEqual((row["play_count"], row["total_play_time"]), expected[row["id"]])
            self.assertEqual(row["gm_notes"], "所有者メモ")
            self.assertEqual(row["handout_templates"][0]["recommended_skill_items"][0]["name"], "目星")
        viewer = CustomUser.objects.create_user(username="scenario-query-viewer")
        for number in range(2):
            group = Group.objects.create(name=f"共通{number}", created_by=user)
            GroupMembership.objects.get_or_create(group=group, user=user)
            GroupMembership.objects.create(group=group, user=viewer)
        outsider = CustomUser.objects.create_user(username="scenario-query-outsider")
        Scenario.objects.create(title="対象外", created_by=outsider)
        self.client.force_authenticate(viewer)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/api/scenarios/scenarios/")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 6)
        self.assertEqual({row["id"] for row in response.data}, set(expected))
        for row in response.data:
            self.assertEqual((row["play_count"], row["total_play_time"]), expected[row["id"]])
            self.assertNotIn("gm_notes", row)
            self.assertEqual(row["handout_templates"], [])
