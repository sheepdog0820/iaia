from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import CharacterSheet
from accounts.test_character_factories import create_character_with_system_data
from accounts.models import Group as CustomGroup
from scenarios.models import Scenario

from . import session_permissions
from .models import ParticipantIdentity, SessionParticipantRole, TRPGSession
from .recommended_skill_comparison import _canonical_skill_name, build_recommended_skill_comparison

User = get_user_model()


class RecommendedSkillComparisonServiceTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user(username="comparison-gm", password="pass123")
        self.player = User.objects.create_user(username="comparison-player", password="pass123")
        self.scenario = Scenario.objects.create(
            title="技能比較シナリオ",
            game_system="coc6",
            created_by=self.gm,
        )
        self.session = TRPGSession.objects.create(
            title="技能比較セッション",
            gm=self.gm,
            created_by=self.gm,
            scenario=self.scenario,
        )

    def create_character(self, *, edition="6th", name="比較探索者", dex_value=None, edu_value=None):
        is_seventh = edition == "7th"
        character, _ = create_character_with_system_data(
            user=self.player,
            edition=edition,
            name=name,
            str_value=50 if is_seventh else 10,
            con_value=50 if is_seventh else 10,
            pow_value=50 if is_seventh else 10,
            dex_value=dex_value if dex_value is not None else (50 if is_seventh else 10),
            app_value=50 if is_seventh else 10,
            siz_value=50 if is_seventh else 10,
            int_value=50 if is_seventh else 10,
            edu_value=edu_value if edu_value is not None else (50 if is_seventh else 10),
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )
        participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role="player",
            character_sheet=character,
        )
        return character, participant

    def comparison_for(self, participant):
        return build_recommended_skill_comparison(self.scenario, [participant])

    def test_parses_deduplicates_and_prioritizes_recommended_skills(self):
        self.scenario.recommended_skills = " 目星、図書館\n目星 "
        self.scenario.semi_recommended_skills = "図書館, 聞き耳，心理学"
        self.scenario.save()
        _, participant = self.create_character()

        comparison = self.comparison_for(participant)

        self.assertEqual(
            [(row["name"], row["level"]) for row in comparison["rows"]],
            [
                ("目星", "recommended"),
                ("図書館", "recommended"),
                ("聞き耳", "semi_recommended"),
                ("心理学", "semi_recommended"),
            ],
        )

    def test_uses_saved_current_value_and_sixth_edition_initial_value(self):
        self.scenario.recommended_skills = "目星, 母国語, 回避, こぶし（パンチ）"
        self.scenario.save()
        character, participant = self.create_character(edu_value=14, dex_value=12)
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
        )

        comparison = self.comparison_for(participant)

        spot_hidden = comparison["rows"][0]["cells"][0]["matches"][0]
        own_language = comparison["rows"][1]["cells"][0]["matches"][0]
        dodge = comparison["rows"][2]["cells"][0]["matches"][0]
        fist = comparison["rows"][3]["cells"][0]["matches"][0]
        self.assertEqual(spot_hidden, {"name": "目星", "value": 65, "is_initial": False})
        self.assertEqual(own_language, {"name": "母国語", "value": 70, "is_initial": True})
        self.assertEqual(dodge, {"name": "回避", "value": 24, "is_initial": True})
        self.assertEqual(fist, {"name": "こぶし（パンチ）", "value": 50, "is_initial": True})

    def test_calculates_seventh_edition_ability_based_initial_values(self):
        self.scenario.game_system = "coc7"
        self.scenario.recommended_skills = "回避, 母国語"
        self.scenario.save()
        _, participant = self.create_character(edition="7th", dex_value=70, edu_value=80)

        comparison = self.comparison_for(participant)

        dodge = comparison["rows"][0]["cells"][0]["matches"][0]
        own_language = comparison["rows"][1]["cells"][0]["matches"][0]
        self.assertEqual(dodge["value"], 35)
        self.assertTrue(dodge["is_initial"])
        self.assertEqual(own_language["value"], 80)
        self.assertTrue(own_language["is_initial"])

    def test_lists_all_specializations_for_a_general_recommended_skill(self):
        self.scenario.recommended_skills = "芸術"
        self.scenario.save()
        character, participant = self.create_character()
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="芸術（絵画）",
            base_value=5,
            occupation_points=55,
        )
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="芸術(歌唱)",
            base_value=5,
            interest_points=35,
        )

        comparison = self.comparison_for(participant)

        matches = comparison["rows"][0]["cells"][0]["matches"]
        self.assertTrue(comparison["rows"][0]["cells"][0]["show_match_names"])
        self.assertEqual(
            matches,
            [
                {"name": "芸術（絵画）", "value": 60, "is_initial": False},
                {"name": "芸術(歌唱)", "value": 40, "is_initial": False},
            ],
        )

    def test_specific_specialization_only_matches_the_requested_skill(self):
        self.scenario.recommended_skills = "芸術（絵画）"
        self.scenario.save()
        character, participant = self.create_character()
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="芸術（絵画）",
            base_value=5,
            occupation_points=55,
        )
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="芸術（歌唱）",
            base_value=5,
            interest_points=35,
        )

        comparison = self.comparison_for(participant)

        self.assertEqual(
            comparison["rows"][0]["cells"][0]["matches"],
            [{"name": "芸術（絵画）", "value": 60, "is_initial": False}],
        )
        self.assertFalse(comparison["rows"][0]["cells"][0]["show_match_names"])

        character.system_data.skills.filter(skill_name="芸術（歌唱）").delete()
        self.scenario.recommended_skills = "芸術"
        self.scenario.save()

        general_comparison = self.comparison_for(participant)

        self.assertTrue(general_comparison["rows"][0]["cells"][0]["show_match_names"])

    def test_maps_legacy_sixth_edition_names_to_seventh_edition_skills(self):
        self.scenario.game_system = "coc7"
        self.scenario.recommended_skills = "拳銃"
        self.scenario.save()
        character, participant = self.create_character(edition="7th")
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="射撃（拳銃）",
            base_value=20,
            occupation_points=40,
        )

        comparison = self.comparison_for(participant)

        self.assertEqual(
            comparison["rows"][0]["cells"][0]["matches"],
            [{"name": "射撃（拳銃）", "value": 60, "is_initial": False}],
        )

    def test_matches_specialized_seventh_edition_skill_after_alias_conversion(self):
        self.scenario.game_system = "coc7"
        self.scenario.recommended_skills = "芸術（絵画）"
        self.scenario.save()
        character, participant = self.create_character(edition="7th")
        character.system_data.skills.model.objects.create(
            character_sheet=character.system_data,
            skill_name="芸術／製作（絵画）",
            base_value=5,
            occupation_points=45,
        )

        comparison = self.comparison_for(participant)

        self.assertEqual(
            comparison["rows"][0]["cells"][0]["matches"],
            [{"name": "芸術／製作（絵画）", "value": 50, "is_initial": False}],
        )

    def test_uses_fixed_and_specialized_initial_values_for_both_editions(self):
        self.scenario.game_system = "coc7"
        self.scenario.recommended_skills = "拳銃, 芸術（絵画）"
        self.scenario.save()
        _, seventh_participant = self.create_character(edition="7th")

        seventh_comparison = self.comparison_for(seventh_participant)

        self.assertEqual(seventh_comparison["rows"][0]["cells"][0]["matches"][0]["value"], 20)
        self.assertEqual(seventh_comparison["rows"][1]["cells"][0]["matches"][0]["value"], 5)

        self.session.sessionparticipant_set.all().delete()
        self.scenario.game_system = "coc6"
        self.scenario.recommended_skills = "芸術（彫刻）, 未知技能"
        self.scenario.save()
        _, sixth_participant = self.create_character(edition="6th")

        sixth_comparison = self.comparison_for(sixth_participant)

        self.assertEqual(sixth_comparison["rows"][0]["cells"][0]["matches"][0]["value"], 5)
        self.assertEqual(sixth_comparison["rows"][1]["cells"][0]["matches"], [])

    def test_normalizes_empty_and_legacy_language_skill_names(self):
        self.assertEqual(_canonical_skill_name("", "6th"), "")
        self.assertEqual(_canonical_skill_name("他国語", "6th"), "他の言語")
        self.assertEqual(_canonical_skill_name("他国語（英語）", "6th"), "他の言語（英語）")

    def test_comparison_without_scenario_returns_none(self):
        self.assertIsNone(build_recommended_skill_comparison(None, []))


class RecommendedSkillComparisonViewTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user(username="comparison-view-gm", password="pass123")
        self.player = User.objects.create_user(username="comparison-view-player", password="pass123")
        self.observer = User.objects.create_user(username="comparison-view-observer", password="pass123")
        self.group = CustomGroup.objects.create(name="技能比較グループ", created_by=self.gm)
        self.group.members.add(self.gm, self.player, self.observer)
        self.scenario = Scenario.objects.create(
            title="表示比較シナリオ",
            game_system="coc6",
            recommended_skills="目星, 芸術",
            semi_recommended_skills="聞き耳",
            created_by=self.gm,
        )
        self.session = TRPGSession.objects.create(
            title="表示比較セッション",
            gm=self.gm,
            created_by=self.gm,
            group=self.group,
            scenario=self.scenario,
        )
        self.character, _ = create_character_with_system_data(
            user=self.player,
            edition="6th",
            name="表示比較探索者",
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )
        self.participant = session_permissions.create_participant(
            session=self.session,
            user=self.player,
            role="player",
            character_sheet=self.character,
        )
        self.character.system_data.skills.model.objects.create(
            character_sheet=self.character.system_data,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
        )
        self.character.system_data.skills.model.objects.create(
            character_sheet=self.character.system_data,
            skill_name="芸術（絵画）",
            base_value=5,
            interest_points=35,
        )
        self.detail_url = reverse("session_detail", kwargs={"pk": self.session.id})

    def test_gm_and_non_premium_player_can_view_comparison(self):
        for user in (self.gm, self.player):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.detail_url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-bs-target="#recommendedSkillComparisonModal"')
                self.assertContains(response, 'id="recommendedSkillComparisonModal"')
                self.assertContains(response, 'id="recommendedSkillComparison"')
                self.assertContains(response, "表示比較探索者")
                self.assertContains(response, "65%")
                self.assertContains(response, "芸術（絵画）")
                self.client.logout()

    def test_claim_requests_modal_is_only_shown_when_temporary_member_participates(self):
        self.client.force_login(self.gm)

        response_without_temporary_member = self.client.get(self.detail_url)

        self.assertEqual(response_without_temporary_member.status_code, 200)
        self.assertNotContains(response_without_temporary_member, 'id="sessionClaimRequestsModal"')
        self.assertNotContains(
            response_without_temporary_member,
            'data-bs-target="#sessionClaimRequestsModal"',
        )

        identity = ParticipantIdentity.objects.create(
            group=self.group,
            created_by=self.gm,
            display_name="紐付け対象PL",
        )
        session_permissions.create_participant(
            session=self.session,
            participant_identity=identity,
            user=None,
            guest_name=identity.display_name,
            roles=[SessionParticipantRole.Role.PLAYER],
            granted_by=self.gm,
        )

        response_with_temporary_member = self.client.get(self.detail_url)

        self.assertEqual(response_with_temporary_member.status_code, 200)
        self.assertContains(
            response_with_temporary_member,
            'data-bs-target="#sessionClaimRequestsModal"',
        )
        self.assertContains(response_with_temporary_member, 'id="sessionClaimRequestsModal"')
        self.assertContains(response_with_temporary_member, 'id="sessionClaimRequestsList"')
        self.assertNotContains(response_with_temporary_member, 'id="sessionClaimRequestsPanel"')

    def test_player_cards_use_aligned_action_layout(self):
        self.client.force_login(self.gm)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "session-participant-card")
        self.assertContains(response, "participant-summary")
        self.assertContains(response, "participant-name")
        self.assertContains(response, "participant-character-name")
        self.assertContains(response, "participant-output-actions")
        self.assertContains(response, "participant-card-actions")
        self.assertContains(response, "participant-character-url-copy")
        self.assertContains(response, "text-start")
        self.assertContains(response, "justify-content-start")
        self.assertContains(response, "参照")

    def test_player_card_actions_use_internal_character_direct_url(self):
        self.client.force_login(self.gm)
        character_url = reverse("character_detail_6th", kwargs={"character_id": self.character.id})

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "participant-reference-action")
        self.assertContains(response, "participant-edit-action")
        self.assertContains(response, "participant-delete-action")
        self.assertContains(response, "participant-character-export")
        self.assertContains(response, f'href="{character_url}"')
        self.assertContains(response, 'target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, f'data-copy-url="{character_url}"')
        self.assertContains(response, f'data-character-detail-url="{character_url}"')
        self.assertContains(response, "出力")
        self.assertContains(response, "JSON形式でコピー")

    def test_external_character_reference_and_copy_use_registered_url(self):
        self.participant.character_sheet = None
        self.participant.character_sheet_url = "https://example.com/sheet"
        self.participant.save(update_fields=["character_sheet", "character_sheet_url"])
        self.client.force_login(self.gm)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="https://example.com/sheet"')
        self.assertContains(response, 'data-copy-url="https://example.com/sheet"')
        self.assertNotContains(response, 'aria-label="出力（JSON形式）"')

    def test_non_participant_group_member_cannot_view_comparison(self):
        self.client.force_login(self.observer)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="recommendedSkillComparison"')

    def test_public_share_view_does_not_show_comparison(self):
        self.session.visibility = "public"
        self.session.save(update_fields=["visibility"])

        response = self.client.get(
            reverse("fixed-shared-session-view", kwargs={"share_token": self.session.share_token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="recommendedSkillComparison"')

    def test_comparison_is_hidden_without_required_data(self):
        cases = (
            ("no-scenario", {"scenario": None}),
            ("no-recommended-skills", {"recommended_skills": "", "semi_recommended_skills": ""}),
            ("no-internal-character", {"character_sheet": None, "character_sheet_url": "https://example.com/sheet"}),
        )
        self.client.force_login(self.gm)

        for label, changes in cases:
            with self.subTest(case=label):
                if "scenario" in changes:
                    self.session.scenario = changes["scenario"]
                    self.session.save(update_fields=["scenario"])
                if "recommended_skills" in changes:
                    self.scenario.recommended_skills = changes["recommended_skills"]
                    self.scenario.semi_recommended_skills = changes["semi_recommended_skills"]
                    self.scenario.save(update_fields=["recommended_skills", "semi_recommended_skills"])
                if "character_sheet" in changes:
                    self.participant.character_sheet = changes["character_sheet"]
                    self.participant.character_sheet_url = changes["character_sheet_url"]
                    self.participant.save(update_fields=["character_sheet", "character_sheet_url"])

                response = self.client.get(self.detail_url)

                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'id="recommendedSkillComparison"')

                self.session.scenario = self.scenario
                self.session.save(update_fields=["scenario"])
                self.scenario.recommended_skills = "目星"
                self.scenario.semi_recommended_skills = "聞き耳"
                self.scenario.save(update_fields=["recommended_skills", "semi_recommended_skills"])
                self.participant.character_sheet = self.character
                self.participant.character_sheet_url = ""
                self.participant.save(update_fields=["character_sheet", "character_sheet_url"])
