from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterImage, CharacterSheet
from accounts.models import CustomUser, Group, GroupMembership
from scenarios.models import Scenario, ScenarioHandout
from schedules import session_permissions
from schedules.models import HandoutInfo, TRPGSession


class FixedShareUrlTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="fixed_share_owner",
            email="fixed-owner@example.com",
            password="pass123",
        )
        self.other_user = CustomUser.objects.create_user(
            username="fixed_share_other",
            email="fixed-other@example.com",
            password="pass123",
        )
        self.group = Group.objects.create(
            name="Fixed Share Group",
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
            "user": self.owner,
            "edition": "6th",
            "name": "Fixed URL Investigator",
            "player_name": "Player",
            "age": 30,
            "str_value": 10,
            "con_value": 11,
            "pow_value": 12,
            "dex_value": 13,
            "app_value": 14,
            "siz_value": 15,
            "int_value": 16,
            "edu_value": 17,
            "hit_points_max": 13,
            "hit_points_current": 13,
            "magic_points_max": 12,
            "magic_points_current": 12,
            "sanity_starting": 60,
            "sanity_max": 99,
            "sanity_current": 60,
            "access_scope": "private",
            "notes": "private notes must not render",
        }
        values.update(overrides)
        return CharacterSheet.objects.create(**values)

    def create_session(self, **overrides):
        values = {
            "title": "Fixed URL Session",
            "description": "safe session text",
            "date": timezone.now() + timedelta(days=1),
            "gm": self.owner,
            "created_by": self.owner,
            "group": self.group,
            "visibility": "private",
            "status": "planned",
            "duration_minutes": 120,
        }
        values.update(overrides)
        return TRPGSession.objects.create(**values)

    def create_scenario(self, **overrides):
        values = {
            "title": "Fixed URL Scenario",
            "summary": "safe scenario summary",
            "public_info": "safe player info",
            "gm_notes": "secret gm notes must not render",
            "created_by": self.owner,
            "visibility": "private",
            "game_system": "coc6",
        }
        values.update(overrides)
        return Scenario.objects.create(**values)

    def issue_fixed_url(self, resource_type, object_id, auto_enable_link=True):
        return self.client.post(
            "/api/share-links/fixed-url/",
            {
                "resource_type": resource_type,
                "object_id": object_id,
                "auto_enable_link": auto_enable_link,
            },
            format="json",
        )

    def test_character_fixed_share_url_is_stable_and_uses_no_id_path(self):
        character = self.create_character()
        self.assertIsNotNone(character.share_token)

        self.client.force_authenticate(self.owner)
        first = self.issue_fixed_url("character", character.id)
        second = self.issue_fixed_url("character", character.id)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["share_url"], second.data["share_url"])
        self.assertIn(f"/share/characters/{character.share_token}/view/", first.data["share_url"])
        self.assertNotIn(f"/characters/{character.id}/view/", first.data["share_url"])

        character.refresh_from_db()
        self.assertEqual(character.access_scope, "link")

        owner_response = self.client.get(f"/share/characters/{character.share_token}/view/")
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertContains(owner_response, 'data-public-view="false"')
        self.assertContains(owner_response, 'id="editButton"')
        self.assertNotIn(f"/characters/{character.id}/view/", owner_response.wsgi_request.path)

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(f"/share/characters/{character.share_token}/view/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_200_OK)
        self.assertContains(anonymous_response, "Fixed URL Investigator")
        self.assertContains(anonymous_response, 'data-public-view="true"')
        self.assertContains(
            anonymous_response,
            f'data-character-images-api-url="/share/characters/{character.share_token}/images/"',
        )
        self.assertContains(
            anonymous_response,
            f'data-character-images-zip-url="/share/characters/{character.share_token}/images.zip"',
        )
        self.assertContains(anonymous_response, 'id="characterImagesDownloadLink"')
        self.assertContains(
            anonymous_response,
            f'data-character-ccfolia-json-url="/share/characters/{character.share_token}/ccfolia.json"',
        )
        self.assertContains(
            anonymous_response,
            f'data-character-reference-url="/share/characters/{character.share_token}/view/"',
        )
        self.assertContains(anonymous_response, 'id="ccfoliaExportLink"')
        self.assertContains(anonymous_response, "ココフォリア用コピー")
        self.assertNotContains(anonymous_response, 'download="character-')
        self.assertNotContains(anonymous_response, 'id="editButton"')
        self.assertNotContains(anonymous_response, "private notes must not render")

        ccfolia_response = self.client.get(f"/share/characters/{character.share_token}/ccfolia.json")
        self.assertEqual(ccfolia_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ccfolia_response.data["kind"], "character")
        self.assertEqual(ccfolia_response.data["data"]["name"], "Fixed URL Investigator")

        self.client.force_authenticate(self.other_user)
        logged_in_response = self.client.get(f"/share/characters/{character.share_token}/view/")
        self.assertEqual(logged_in_response.status_code, status.HTTP_200_OK)
        self.assertContains(logged_in_response, "Fixed URL Investigator")
        self.assertNotContains(logged_in_response, 'id="editButton"')

        character.access_scope = "private"
        character.save(update_fields=["access_scope"])
        closed_response = self.client.get(f"/share/characters/{character.share_token}/view/")
        self.assertEqual(closed_response.status_code, status.HTTP_404_NOT_FOUND)
        closed_ccfolia_response = self.client.get(f"/share/characters/{character.share_token}/ccfolia.json")
        self.assertEqual(closed_ccfolia_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_character_fixed_share_og_image_uses_main_character_image_record(self):
        character = self.create_character(
            access_scope="link",
            character_image="character_sheets/legacy.png",
        )
        CharacterImage.objects.create(
            character_sheet=character,
            image="character_images/2026/07/first.png",
            is_main=False,
            order=0,
        )
        CharacterImage.objects.create(
            character_sheet=character,
            image="character_images/2026/07/main.png",
            is_main=True,
            order=1,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/share/characters/{character.share_token}/view/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preview_image_url = f"http://testserver/share/characters/{character.share_token}/preview-image/"
        self.assertContains(
            response,
            f'<meta property="og:image" content="{preview_image_url}">',
        )
        self.assertContains(
            response,
            f'<meta name="twitter:image" content="{preview_image_url}">',
        )
        self.assertNotContains(response, "character_sheets/legacy.png")
        self.assertNotContains(response, "first.png")
        self.assertNotContains(response, "main.png")

    def test_character_fixed_share_og_image_uses_first_character_image_when_no_main(self):
        character = self.create_character(access_scope="link")
        CharacterImage.objects.create(
            character_sheet=character,
            image="character_images/2026/07/first.png",
            is_main=False,
            order=0,
        )
        CharacterImage.objects.create(
            character_sheet=character,
            image="character_images/2026/07/second.png",
            is_main=False,
            order=1,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/share/characters/{character.share_token}/view/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(
            response,
            f'<meta property="og:image" content="http://testserver/share/characters/{character.share_token}/preview-image/">',
        )
        self.assertNotContains(response, "first.png")
        self.assertNotContains(response, "second.png")

    def test_character_fixed_share_og_image_keeps_legacy_fallback(self):
        character = self.create_character(
            access_scope="link",
            character_image="character_sheets/legacy.png",
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/share/characters/{character.share_token}/view/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(
            response,
            f'<meta property="og:image" content="http://testserver/share/characters/{character.share_token}/preview-image/">',
        )
        self.assertNotContains(response, "character_sheets/legacy.png")

    def test_session_fixed_share_url_reuses_existing_share_token(self):
        session = self.create_session()
        participant = session_permissions.create_participant(
            session=session,
            user=self.other_user,
            role="player",
        )
        HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title="Owner Secret Handout",
            content="Only the session manager should see this",
        )

        self.client.force_authenticate(self.owner)
        response = self.issue_fixed_url("session", session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(f"/share/sessions/{session.share_token}/view/", response.data["share_url"])
        self.assertNotIn(f"/sessions/{session.id}/view/", response.data["share_url"])

        session.refresh_from_db()
        self.assertEqual(session.visibility, "link")

        owner_response = self.client.get(f"/share/sessions/{session.share_token}/view/")
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertContains(owner_response, 'id="editSessionModal"')
        self.assertContains(owner_response, 'id="inviteMembersModal"')
        self.assertContains(owner_response, "Owner Secret Handout")

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(f"/share/sessions/{session.share_token}/view/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_200_OK)
        self.assertContains(anonymous_response, "Fixed URL Session")
        self.assertNotContains(anonymous_response, 'id="editSessionModal"')
        self.assertNotContains(anonymous_response, 'id="inviteMembersModal"')
        self.assertNotContains(anonymous_response, "Owner Secret Handout")

        session.visibility = "group"
        session.save(update_fields=["visibility"])
        closed_response = self.client.get(f"/share/sessions/{session.share_token}/view/")
        self.assertEqual(closed_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_gm_participant_role_can_issue_fixed_share_url(self):
        session = self.create_session(gm=None)
        session_permissions.create_participant(
            session=session,
            user=self.other_user,
            role="gm",
        )

        self.client.force_authenticate(self.other_user)
        response = self.issue_fixed_url("session", session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(f"/share/sessions/{session.share_token}/view/", response.data["share_url"])

    def test_scenario_fixed_share_url_is_stable_and_safe(self):
        scenario = self.create_scenario(gm_notes="Owner-only GM note")
        ScenarioHandout.objects.create(
            scenario=scenario,
            title="Secret Owner HO",
            content="Secret owner handout content",
            is_secret=True,
            handout_number=1,
        )
        self.assertIsNotNone(scenario.share_token)

        self.client.force_authenticate(self.owner)
        first = self.issue_fixed_url("scenario", scenario.id)
        second = self.issue_fixed_url("scenario", scenario.id)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["share_url"], second.data["share_url"])
        self.assertIn(f"/share/scenarios/{scenario.share_token}/view/", first.data["share_url"])
        self.assertNotIn(f"/scenarios/{scenario.id}/view/", first.data["share_url"])

        scenario.refresh_from_db()
        self.assertEqual(scenario.visibility, "link")

        owner_response = self.client.get(f"/share/scenarios/{scenario.share_token}/view/")
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertContains(owner_response, 'data-testid="editScenarioLink"')
        self.assertContains(owner_response, "Owner-only GM note")
        self.assertContains(owner_response, "Secret Owner HO")

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(f"/share/scenarios/{scenario.share_token}/view/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_200_OK)
        self.assertContains(anonymous_response, "Fixed URL Scenario")
        self.assertNotContains(anonymous_response, 'data-testid="editScenarioLink"')
        self.assertNotContains(anonymous_response, "Owner-only GM note")
        self.assertNotContains(anonymous_response, "Secret Owner HO")

    def test_non_owner_cannot_issue_fixed_share_url(self):
        character = self.create_character()

        self.client.force_authenticate(self.other_user)
        response = self.issue_fixed_url("character", character.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
