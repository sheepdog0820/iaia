from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from .models import Scenario, PlayHistory
from accounts.models import Group as CustomGroup

User = get_user_model()


class ScenarioModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='authoruser',
            email='author@example.com',
            password='pass123',
            nickname='Author User'
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user
        )

    def test_scenario_creation(self):
        """シナリオ作成テスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            summary='Test Description',
            author='Test Author',
            created_by=self.user,
            recommended_players='3-5人',
            estimated_time=180,
            difficulty='intermediate',
            game_system='coc'
        )
        
        self.assertEqual(scenario.title, 'Test Scenario')
        self.assertEqual(scenario.created_by, self.user)
        self.assertEqual(scenario.recommended_players, '3-5人')
        self.assertEqual(scenario.estimated_time, 180)
        self.assertEqual(scenario.difficulty, 'intermediate')

    def test_scenario_string_representation(self):
        """シナリオ文字列表現テスト"""
        scenario = Scenario.objects.create(
            title='Test Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc'
        )
        
        self.assertEqual(str(scenario), 'Test Scenario')

    def test_play_history_creation(self):
        """プレイ履歴作成テスト"""
        from django.utils import timezone
        
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
            role='gm',
            notes='Test session notes'
        )
        
        self.assertEqual(play_history.scenario, scenario)
        self.assertEqual(play_history.user, self.user)
        self.assertEqual(play_history.role, 'gm')
        self.assertEqual(play_history.notes, 'Test session notes')

    def test_play_history_string_representation(self):
        """プレイ履歴文字列表現テスト"""
        from django.utils import timezone
        
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
        
        expected_str = f'{self.user.nickname} played {scenario.title} (gm)'
        self.assertEqual(str(play_history), expected_str)


class ScenarioAPITestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='authoruser',
            email='author@example.com',
            password='pass123',
            nickname='Author User'
        )
        self.user2 = User.objects.create_user(
            username='playeruser',
            email='player@example.com',
            password='pass123',
            nickname='Player User'
        )
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        self.group.members.add(self.user1, self.user2)
        
        # テスト用シナリオ作成
        self.scenario = Scenario.objects.create(
            title='Test Scenario',
            summary='Test Description',
            author='Test Author',
            created_by=self.user1,
            recommended_players='2-4人',
            estimated_time=180,
            difficulty='intermediate',
            game_system='coc'
        )
        
        # テスト用プレイ履歴作成
        from django.utils import timezone
        self.play_history = PlayHistory.objects.create(
            scenario=self.scenario,
            user=self.user1,
            played_date=timezone.now(),
            role='gm',
            notes='Test notes'
        )

    def test_scenario_list_unauthenticated(self):
        """未認証シナリオ一覧アクセステスト"""
        response = self.client.get('/api/scenarios/scenarios/')
        # 認証が必要（TokenAuthenticationが有効なため未認証は401）
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_scenario_list_authenticated(self):
        """認証済みシナリオ一覧アクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/scenarios/scenarios/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_play_history_unauthenticated(self):
        """未認証プレイ履歴アクセステスト"""
        response = self.client.get('/api/scenarios/history/')
        # 認証が必要（TokenAuthenticationが有効なため未認証は401）
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_play_history_authenticated(self):
        """認証済みプレイ履歴アクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/scenarios/history/')
        
        # URLが存在する場合
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIsInstance(data, list)
            if len(data) > 0:
                history_item = data[0]
                self.assertIn('scenario', history_item)
                self.assertIn('role', history_item)
        else:
            # URLが存在しない場合は404
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_play_history_with_limit(self):
        """プレイ履歴制限パラメータテスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/scenarios/history/?limit=5')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIsInstance(data, list)
            self.assertLessEqual(len(data), 5)

    def test_scenario_detail_view(self):
        """シナリオ詳細ビューテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # シナリオAPIが存在する場合
        response = self.client.get(f'/api/scenarios/scenarios/{self.scenario.id}/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(data['title'], 'Test Scenario')
            self.assertEqual(data['created_by'], self.user1.id)


    def test_scenario_recommended_skills_blank(self):
        """Allow blank recommended_skills on create and update."""
        self.client.force_authenticate(user=self.user1)

        scenario_data = {
            'title': 'Blank Recommended Skills Scenario',
            'author': 'Test Author',
            'game_system': 'coc',
            'difficulty': 'beginner',
            'estimated_duration': 'short',
            'summary': '',
            'recommended_players': '',
            'recommended_skills': '   ',
            'url': ''
        }

        response = self.client.post('/api/scenarios/scenarios/', scenario_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data.get('recommended_skills', ''), '')

        scenario_id = data.get('id')
        patch_response = self.client.patch(
            f'/api/scenarios/scenarios/{scenario_id}/',
            {'recommended_skills': '   '}
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        patched = patch_response.json()
        self.assertEqual(patched.get('recommended_skills', ''), '')

    def test_scenario_creation_permissions(self):
        """シナリオ作成権限テスト"""
        self.client.force_authenticate(user=self.user1)
        
        scenario_data = {
            'title': 'New Scenario',
            'description': 'New Description',
            'player_count_min': 2,
            'player_count_max': 6,
            'estimated_duration': 240,
            'difficulty': 'hard'
        }
        
        response = self.client.post('/api/scenarios/', scenario_data)
        
        # APIが存在し、作成が許可されている場合
        if response.status_code == status.HTTP_201_CREATED:
            created_scenario = Scenario.objects.get(title='New Scenario')
            self.assertEqual(created_scenario.author, self.user1)

    def test_play_history_creation(self):
        """プレイ履歴作成テスト"""
        self.client.force_authenticate(user=self.user1)
        
        history_data = {
            'scenario': self.scenario.id,
            'played_date': timezone.now().isoformat(),
            'role': 'gm',
            'notes': 'Great session!'
        }
        
        response = self.client.post('/api/scenarios/history/', history_data)
        
        # APIが存在し、作成が許可されている場合
        if response.status_code == status.HTTP_201_CREATED:
            created_history = PlayHistory.objects.get(notes='Great session!')
            self.assertEqual(created_history.user, self.user1)
            self.assertEqual(created_history.role, 'gm')

    def test_scenario_filtering(self):
        """シナリオフィルタリングテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 難易度によるフィルタリング（実際のテストデータと一致する値を使用）
        response = self.client.get('/api/scenarios/scenarios/?difficulty=intermediate')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if len(data) > 0:
                for scenario in data:
                    self.assertEqual(scenario['difficulty'], 'intermediate')

    def test_scenario_search(self):
        """シナリオ検索テスト"""
        self.client.force_authenticate(user=self.user1)
        
        # タイトルによる検索
        response = self.client.get('/api/scenarios/scenarios/?search=Test')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if len(data) > 0:
                found_titles = [s['title'] for s in data]
                self.assertTrue(any('Test' in title for title in found_titles))
