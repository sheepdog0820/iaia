from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Scenario, PlayHistory

User = get_user_model()


class BasicScenarioTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='scenariouser',
            email='scenario@example.com',
            password='pass123',
            nickname='Scenario User'
        )

    def test_scenario_creation(self):
        """基本シナリオ作成のテスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )
        self.assertEqual(scenario.title, 'Test Scenario')
        self.assertEqual(scenario.author, 'Test Author')
        self.assertEqual(scenario.created_by, self.user)

    def test_scenario_str_representation(self):
        """シナリオ文字列表現のテスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )
        self.assertEqual(str(scenario), 'Test Scenario')

    def test_scenario_with_optional_fields(self):
        """オプションフィールド付きシナリオのテスト"""
        scenario = Scenario.objects.create(
            title='Complex Scenario',
            author='Complex Author',
            created_by=self.user,
            game_system='coc',
            summary='A complex scenario description',
            recommended_players='3-5人',
            estimated_time=180,
            difficulty='intermediate'
        )
        self.assertEqual(scenario.recommended_players, '3-5人')
        self.assertEqual(scenario.estimated_time, 180)
        self.assertEqual(scenario.difficulty, 'intermediate')

    def test_play_history_creation(self):
        """プレイ履歴作成のテスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )
        
        play_history = PlayHistory.objects.create(
            scenario=scenario,
            user=self.user,
            played_date=timezone.now(),
            role='gm'
        )
        
        self.assertEqual(play_history.scenario, scenario)
        self.assertEqual(play_history.user, self.user)
        self.assertEqual(play_history.role, 'gm')

    def test_play_history_str_representation(self):
        """プレイ履歴文字列表現のテスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )
        
        play_history = PlayHistory.objects.create(
            scenario=scenario,
            user=self.user,
            played_date=timezone.now(),
            role='player'
        )
        
        expected_str = f'{self.user.nickname} played {scenario.title} (player)'
        self.assertEqual(str(play_history), expected_str)
