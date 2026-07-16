from schedules import session_permissions
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet, CharacterSheet6th
from accounts.models import CustomUser, Group, GroupMembership, ShareLink
from scenarios.models import Scenario, ScenarioHandout
from schedules.models import HandoutInfo, ParticipantIdentity, SessionParticipant, TRPGSession


class ShareLinkApiTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="share_owner",
            email="owner@example.com",
            password="pass123",
            nickname="Owner GM",
        )
        self.player = CustomUser.objects.create_user(
            username="share_player",
            email="player@example.com",
            password="pass123",
            nickname="Player Name",
        )
        self.group = Group.objects.create(
            name="Share Group",
            created_by=self.owner,
            visibility="private",
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.owner,
            role="admin",
        )

    def create_character(self, **overrides):
        values = {
            "user": self.player,
            "edition": "6th",
            "name": "Link Shared PC",
            "player_name": "PL Public Name",
            "age": 28,
            "str_value": 10,
            "con_value": 11,
            "pow_value": 12,
            "dex_value": 13,
            "app_value": 14,
            "siz_value": 15,
            "int_value": 16,
            "edu_value": 17,
            "hit_points_max": 13,
            "hit_points_current": 12,
            "magic_points_max": 12,
            "magic_points_current": 11,
            "sanity_starting": 60,
            "sanity_max": 99,
            "sanity_current": 55,
            "notes": "private character note",
            "version_note": "private version note",
            "access_scope": "link",
        }
        values.update(overrides)
        user = values.pop("user")
        edition = values.pop("edition")
        access_scope = values.pop("access_scope")
        character = CharacterSheet.objects.create(user=user, edition=edition, access_scope=access_scope)
        CharacterSheet6th.objects.create(character_sheet=character, **values)
        character.system_data.skills.create(
            skill_name="Library Use",
            category="知識系",
            base_value=25,
            occupation_points=30,
            interest_points=0,
            bonus_points=0,
            other_points=0,
        )
        return character

    def create_session(self, **overrides):
        values = {
            "title": "Link Shared Session",
            "description": "public session summary",
            "date": timezone.now() + timedelta(days=3),
            "location": "Online",
            "youtube_url": "https://www.youtube.com/watch?v=public",
            "gm": self.owner,
            "created_by": self.owner,
            "group": self.group,
            "status": "planned",
            "visibility": "link",
            "duration_minutes": 180,
        }
        values.update(overrides)
        return TRPGSession.objects.create(**values)

    def test_issue_share_link_for_link_session_and_shared_api_hides_secret_data(self):
        character = self.create_character(access_scope="public")
        session = self.create_session()
        participant = session_permissions.create_participant(
            session=session,
            user=self.player,
            role="player",
            character_name="Investigator Public",
            character_sheet_url="https://iachara.example/view/abc",
            character_sheet=character,
        )
        HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title="Secret HO",
            content="secret handout content",
            is_secret=True,
        )

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/share-links/",
            {
                "resource_type": "session",
                "object_id": session.id,
                "view_level": "standard",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = response.data["token"]
        self.assertEqual(response.data["resource_type"], "session")
        self.assertEqual(response.data["object_id"], session.id)
        self.assertIn("/share/sessions/", response.data["share_url"])

        self.client.force_authenticate(user=None)
        shared = self.client.get(f"/share/sessions/{token}/")

        self.assertEqual(shared.status_code, status.HTTP_200_OK)
        data = shared.json()
        self.assertEqual(data["title"], "Link Shared Session")
        self.assertEqual(data["gm_name"], "Owner GM")
        self.assertEqual(data["participants"][0]["character_name"], "Investigator Public")
        self.assertEqual(data["participants"][0]["character_sheet_url"], "https://iachara.example/view/abc")
        serialized = shared.content.decode()
        self.assertNotIn("Secret HO", serialized)
        self.assertNotIn("secret handout content", serialized)
        self.assertNotIn("owner@example.com", serialized)
        self.assertNotIn("player@example.com", serialized)

    def test_shared_session_uses_imported_gm_identity_without_internal_owner_name(self):
        session = self.create_session()
        identity = ParticipantIdentity.objects.create(
            display_name="Imported GM Display",
        )
        session_permissions.create_participant(
            session=session,
            user=None,
            guest_name="legacy-gm",
            participant_identity=identity,
            role="gm",
        )

        self.client.force_authenticate(self.owner)
        issue_response = self.client.post(
            "/api/share-links/",
            {
                "resource_type": "session",
                "object_id": session.id,
            },
            format="json",
        )
        token = issue_response.data["token"]

        self.client.force_authenticate(user=None)
        shared_response = self.client.get(f"/share/sessions/{token}/")

        self.assertEqual(shared_response.status_code, status.HTTP_200_OK)
        self.assertEqual(shared_response.json()["gm_name"], "Imported GM Display")
        serialized = shared_response.content.decode()
        self.assertNotIn("Owner GM", serialized)
        self.assertNotIn("owner@example.com", serialized)

    def test_link_character_is_not_public_by_id_but_is_readable_with_share_link(self):
        character = self.create_character()

        public_response = self.client.get(f"/api/accounts/character-sheets/{character.id}/public/")
        self.assertEqual(public_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.player)
        issue_response = self.client.post(
            "/api/share-links/",
            {
                "resource_type": "character",
                "object_id": character.id,
            },
            format="json",
        )

        self.assertEqual(issue_response.status_code, status.HTTP_201_CREATED)
        token = issue_response.data["token"]

        self.client.force_authenticate(user=None)
        shared_response = self.client.get(f"/share/characters/{token}/")

        self.assertEqual(shared_response.status_code, status.HTTP_200_OK)
        data = shared_response.json()
        self.assertEqual(data["name"], "Link Shared PC")
        self.assertIn("skills", data)
        serialized = shared_response.content.decode()
        self.assertNotIn("private character note", serialized)
        self.assertNotIn("private version note", serialized)
        self.assertNotIn("allowed_user", serialized)

    def test_scenario_share_link_returns_only_player_safe_fields(self):
        scenario = Scenario.objects.create(
            title="Shared Scenario",
            author="Scenario Author",
            summary="public summary",
            public_info="player-facing public info",
            gm_notes="private gm notes",
            created_by=self.owner,
            game_system="coc6",
            recommended_skills="Spot Hidden",
        )
        ScenarioHandout.objects.create(
            scenario=scenario,
            title="Public HO",
            content="public handout content",
            is_secret=False,
        )
        ScenarioHandout.objects.create(
            scenario=scenario,
            title="Secret HO",
            content="secret handout content",
            is_secret=True,
        )

        self.client.force_authenticate(self.owner)
        issue_response = self.client.post(
            "/api/share-links/",
            {
                "resource_type": "scenario",
                "object_id": scenario.id,
            },
            format="json",
        )

        self.assertEqual(issue_response.status_code, status.HTTP_201_CREATED)
        token = issue_response.data["token"]

        self.client.force_authenticate(user=None)
        shared_response = self.client.get(f"/share/scenarios/{token}/")

        self.assertEqual(shared_response.status_code, status.HTTP_200_OK)
        data = shared_response.json()
        self.assertEqual(data["title"], "Shared Scenario")
        self.assertEqual(data["public_info"], "player-facing public info")
        self.assertEqual([handout["title"] for handout in data["handout_templates"]], ["Public HO"])
        serialized = shared_response.content.decode()
        self.assertNotIn("private gm notes", serialized)
        self.assertNotIn("Secret HO", serialized)
        self.assertNotIn("secret handout content", serialized)
        self.assertNotIn("owner@example.com", serialized)

    def test_link_scenario_is_not_public_by_id_but_is_readable_with_share_link(self):
        scenario = Scenario.objects.create(
            title="Link Only Scenario",
            author="Scenario Author",
            summary="public summary",
            public_info="safe player info",
            gm_notes="private gm notes",
            created_by=self.owner,
            game_system="coc6",
            visibility="link",
        )

        public_response = self.client.get(f"/api/scenarios/scenarios/{scenario.id}/public/")
        self.assertEqual(public_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.owner)
        issue_response = self.client.post(
            "/api/share-links/",
            {
                "resource_type": "scenario",
                "object_id": scenario.id,
            },
            format="json",
        )

        self.assertEqual(issue_response.status_code, status.HTTP_201_CREATED)
        token = issue_response.data["token"]

        self.client.force_authenticate(user=None)
        shared_response = self.client.get(f"/share/scenarios/{token}/")

        self.assertEqual(shared_response.status_code, status.HTTP_200_OK)
        self.assertEqual(shared_response.json()["title"], "Link Only Scenario")
        self.assertNotIn("private gm notes", shared_response.content.decode())

    def test_revoked_and_expired_share_links_are_not_readable(self):
        session = self.create_session()
        active_link, token = ShareLink.issue(
            resource_type=ShareLink.ResourceType.SESSION,
            object_id=session.id,
            created_by=self.owner,
        )

        active_link.revoke()
        revoked_response = self.client.get(f"/share/sessions/{token}/")
        self.assertEqual(revoked_response.status_code, status.HTTP_404_NOT_FOUND)

        expired_link, expired_token = ShareLink.issue(
            resource_type=ShareLink.ResourceType.SESSION,
            object_id=session.id,
            created_by=self.owner,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(expired_link.is_active)

        expired_response = self.client.get(f"/share/sessions/{expired_token}/")
        self.assertEqual(expired_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_stats_token_returns_aggregate_without_user_identity_linking(self):
        session = self.create_session(status="completed", duration_minutes=240)
        identity = ParticipantIdentity.objects.create(
            display_name="Imported GM",
        )
        session_permissions.create_participant(
            session=session,
            user=self.owner,
            participant_identity=identity,
            role="gm",
            character_name="",
        )
        session_permissions.create_participant(
            session=session,
            user=None,
            guest_name="Legacy Player",
            role="player",
            character_name="Legacy PC",
            character_sheet_url="https://iachara.example/view/legacy",
        )
        link, token = ShareLink.issue(
            resource_type=ShareLink.ResourceType.PROFILE_STATS,
            object_id=session.id,
            created_by=self.owner,
        )

        response = self.client.get(f"/share/stats/{token}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["resource_type"], "session_participant_stats")
        self.assertEqual(data["session"]["title"], "Link Shared Session")
        self.assertEqual(data["totals"]["participation_count"], 2)
        self.assertEqual(data["totals"]["gm_count"], 1)
        self.assertEqual(data["totals"]["player_count"], 1)
        self.assertEqual(data["totals"]["duration_minutes"], 240)
        self.assertEqual(data["participants"][0]["display_name"], "Imported GM")
        serialized = response.content.decode()
        self.assertNotIn("owner@example.com", serialized)
        self.assertNotIn("user_id", serialized)

    def test_participant_identity_alias_is_name_based_and_not_user_linked(self):
        identity = ParticipantIdentity.objects.create(
            display_name="Kenta",
        )
        alias = identity.aliases.create(alias="Endo")

        self.assertEqual(identity.normalized_name, "kenta")
        self.assertEqual(alias.normalized_alias, "endo")
        self.assertIsNone(identity.user_id)
