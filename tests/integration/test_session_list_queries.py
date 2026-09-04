from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APIRequestFactory

from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, Group
from scenarios.models import Scenario, ScenarioRecommendedSkill
from schedules.models import (
    HandoutInfo,
    SessionImage,
    SessionParticipant,
    SessionParticipantRole,
    SessionYouTubeLink,
    TRPGSession,
)
from schedules.serializers import TRPGSessionSerializer


class SessionListQueryTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="list-owner")
        self.player = get_user_model().objects.create_user(username="list-player")
        self.outsider = get_user_model().objects.create_user(username="list-outsider")
        self.group = Group.objects.create(name="List group", created_by=self.owner)
        self.client = APIClient()

    def make_session(self, populated):
        session = TRPGSession.objects.create(
            title="Query fixture", gm=self.owner, created_by=self.owner, group=self.group, visibility="public"
        )
        if not populated:
            return session
        scenario = Scenario.objects.create(title="Scenario", created_by=self.owner)
        ScenarioRecommendedSkill.objects.create(scenario=scenario, name="目星", order=2)
        ScenarioRecommendedSkill.objects.create(scenario=scenario, name="聞き耳", order=1)
        session.scenario = scenario
        session.save(update_fields=["scenario"])
        participant = SessionParticipant.objects.create(session=session, user=self.player, player_slot=1)
        edition = "6th" if session.pk % 2 else "7th"
        character = CharacterSheet.objects.create(user=self.player, edition=edition)
        detail_model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
        detail_model.objects.create(character_sheet=character, name="探索者")
        participant.character_sheet = character
        participant.save(update_fields=["character_sheet"])
        SessionParticipantRole.objects.create(participant=participant, role="player")
        guest = SessionParticipant.objects.create(session=session, guest_name="ゲスト")
        for title, secret, assigned, slot in [
            ("public", False, guest, None),
            ("own", True, participant, None),
            ("slot", True, guest, 1),
            ("hidden", True, guest, 2),
        ]:
            HandoutInfo.objects.create(
                session=session, title=title, is_secret=secret, participant=assigned, assigned_player_slot=slot
            )
        SessionYouTubeLink.objects.bulk_create(
            [SessionYouTubeLink(session=session, video_id="test-video", duration_seconds=125, added_by=self.owner)]
        )
        SessionImage.objects.bulk_create([SessionImage(session=session, uploaded_by=self.owner)])
        return session

    def read_list(self, user):
        self.client.force_authenticate(user=user)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/api/schedules/sessions/?period=all")
            self.assertEqual(response.status_code, 200)
            rows = response.json()
        return rows, len(queries)

    def test_query_count_does_not_grow_with_empty_or_populated_sessions(self):
        for populated in (False, True):
            with self.subTest(populated=populated):
                TRPGSession.objects.all().delete()
                self.make_session(populated)
                self.make_session(populated)
                _, small_count = self.read_list(self.player)
                for _ in range(8):
                    self.make_session(populated)
                rows, large_count = self.read_list(self.player)
                self.assertEqual(len(rows), 10)
                self.assertLessEqual(large_count, small_count + 1)

    def test_list_preserves_detail_fields_and_handout_permissions(self):
        session = self.make_session(True)
        for user, titles in [
            (self.owner, {"public", "own", "slot", "hidden"}),
            (self.player, {"public", "own", "slot"}),
            (self.outsider, set()),
        ]:
            with self.subTest(user=user.username):
                request = APIRequestFactory().get("/api/schedules/sessions/?period=all")
                request.user = user
                expected = TRPGSessionSerializer(
                    TRPGSession.objects.get(pk=session.pk), context={"request": request}
                ).data
                rows, _ = self.read_list(user)
                self.assertEqual(rows[0], expected)
                self.assertEqual({h["title"] for h in rows[0]["handouts_detail"]}, titles)
                self.assertEqual(rows[0]["participant_count"], 1)
                self.assertEqual(rows[0]["guest_count"], 1)
                self.assertEqual(rows[0]["youtube_total_duration"], 125)
                self.assertEqual(rows[0]["youtube_video_count"], 1)
                self.assertEqual(
                    [s["name"] for s in rows[0]["scenario_detail"]["recommended_skill_items"]], ["聞き耳", "目星"]
                )

    def test_role_gm_can_read_secrets_but_owner_and_manager_roles_cannot(self):
        session = self.make_session(True)
        participant = SessionParticipant.objects.create(session=session, user=self.outsider)
        for role, titles in [
            ("owner", {"public"}),
            ("manager", {"public"}),
            ("gm", {"public", "own", "slot", "hidden"}),
        ]:
            with self.subTest(role=role):
                participant.participant_roles.all().delete()
                SessionParticipantRole.objects.create(participant=participant, role=role)
                rows, _ = self.read_list(self.outsider)
                self.assertEqual({h["title"] for h in rows[0]["handouts_detail"]}, titles)
                request = APIRequestFactory().get("/api/schedules/sessions/?period=all")
                request.user = self.outsider
                expected = TRPGSessionSerializer(
                    TRPGSession.objects.get(pk=session.pk), context={"request": request}
                ).data
                self.assertEqual(rows[0], expected)
