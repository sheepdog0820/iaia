from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.character_models import CharacterSheet, CharacterSheet6th
from accounts.models import Group
from schedules.models import SessionParticipant, TRPGSession

from .models import PlayHistory, Scenario


class CharacterPlayHistoryTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="history-owner")
        self.other = get_user_model().objects.create_user(username="history-other")
        self.group = Group.objects.create(name="履歴", created_by=self.owner)
        self.scenario = Scenario.objects.create(title="履歴シナリオ", created_by=self.owner)
        self.character = CharacterSheet.objects.create(user=self.owner, edition="6th")
        CharacterSheet6th.objects.create(character_sheet=self.character, name="履歴探索者")
        self.session = TRPGSession.objects.create(title="対象セッション", gm=self.owner, group=self.group)
        SessionParticipant.objects.create(session=self.session, user=self.owner, character_sheet=self.character)
        self.target = self.make_history(self.owner, self.session)
        self.unrelated = self.make_history(self.owner, None)
        self.other_history = self.make_history(self.other, self.session)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.url = f"/api/scenarios/history/?character_sheet={self.character.pk}"

    def make_history(self, user, session):
        return PlayHistory.objects.create(
            user=user, session=session, scenario=self.scenario, played_date=timezone.now(), role="player"
        )

    def test_filters_to_own_history_for_selected_character(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [self.target.pk])
        self.assertIn("no-store", response["Cache-Control"])

    def test_unfiltered_history_keeps_existing_behavior(self):
        response = self.client.get("/api/scenarios/history/")
        self.assertEqual({row["id"] for row in response.data}, {self.target.pk, self.unrelated.pk})

    def test_other_user_cannot_query_even_a_public_character_history(self):
        self.character.access_scope = "public"
        self.character.save(update_fields=["access_scope"])
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_anonymous_cannot_query_character_history(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_invalid_or_missing_character_does_not_fall_back_to_all_history(self):
        for value in ("", "abc", "0", "-1", "１", "9223372036854775808", "9999999999999999999999999999"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(f"/api/scenarios/history/?character_sheet={value}").status_code, 404)

    def test_participant_must_be_the_owner_not_another_user(self):
        SessionParticipant.objects.filter(session=self.session).update(user=self.other)
        self.assertEqual(self.client.get(self.url).data, [])

    def test_other_character_in_same_group_is_not_included(self):
        second = CharacterSheet.objects.create(user=self.owner, edition="6th")
        session = TRPGSession.objects.create(title="別探索者", gm=self.owner, group=self.group)
        SessionParticipant.objects.create(session=session, user=self.owner, character_sheet=second)
        self.make_history(self.owner, session)
        self.assertEqual([row["id"] for row in self.client.get(self.url).data], [self.target.pk])

    def test_owner_page_shows_history_and_other_viewer_page_does_not(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(f"/accounts/character/6th/{self.character.pk}/"), 'id="play-history-tab"')
        self.character.access_scope = "public"
        self.character.save(update_fields=["access_scope"])
        self.client.force_login(self.other)
        response = self.client.get(f"/accounts/character/6th/{self.character.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="play-history-tab"')
