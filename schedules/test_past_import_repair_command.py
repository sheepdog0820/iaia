from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.character_models import CharacterSheet
from accounts.models import Group
from scenarios.models import Scenario
from schedules.models import SessionParticipant, TRPGSession


class RepairPastImportCharacterLinkTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.owner = User.objects.create_user(
            username='sheepdog1919',
            email='owner@example.com',
            password='pass123',
            nickname='Owner',
        )
        self.player = User.objects.create_user(
            username='player1',
            email='player@example.com',
            password='pass123',
            nickname='Player',
        )
        self.group = Group.objects.create(
            name='Past Import Test Group',
            created_by=self.owner,
        )
        self.scenario = Scenario.objects.create(
            title='Target Scenario',
            created_by=self.owner,
        )
        self.session = TRPGSession.objects.create(
            title='Target Session',
            date=timezone.now(),
            gm=self.owner,
            group=self.group,
            scenario=self.scenario,
            created_by=self.owner,
        )

    def test_links_unique_character_sheet_by_source_scenario(self):
        character = self._create_character('Linked Character', source_scenario=self.scenario)
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player',
            character_name='Imported Name',
        )

        out = StringIO()
        call_command('repair_past_import_data', group_name=self.group.name, stdout=out)

        participant.refresh_from_db()
        self.assertEqual(participant.character_sheet_id, character.id)
        self.assertEqual(participant.character_name, 'Linked Character')
        self.assertIn('character_sheets_linked=1', out.getvalue())

    def test_skips_ambiguous_character_sheet_candidates(self):
        self._create_character('Candidate A', source_scenario=self.scenario)
        self._create_character('Candidate B', source_scenario=self.scenario)
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player',
            character_name='Imported Name',
        )

        out = StringIO()
        call_command('repair_past_import_data', group_name=self.group.name, stdout=out)

        participant.refresh_from_db()
        self.assertIsNone(participant.character_sheet_id)
        self.assertIn('character_sheets_skipped_ambiguous=1', out.getvalue())

    def test_prefers_unique_character_name_over_scenario_candidates(self):
        target = self._create_character('Imported Name')
        self._create_character('Other Scenario Character', source_scenario=self.scenario)
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player',
            character_name='Imported Name',
        )

        out = StringIO()
        call_command('repair_past_import_data', group_name=self.group.name, stdout=out)

        participant.refresh_from_db()
        self.assertEqual(participant.character_sheet_id, target.id)
        self.assertEqual(participant.character_name, 'Imported Name')
        self.assertIn('character_sheets_linked=1', out.getvalue())

    def _create_character(self, name, source_scenario=None):
        return CharacterSheet.objects.create(
            user=self.player,
            edition='6th',
            name=name,
            age=30,
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
            source_scenario=source_scenario,
            source_scenario_title=source_scenario.title if source_scenario else '',
            source_scenario_game_system=source_scenario.game_system if source_scenario else '',
        )
