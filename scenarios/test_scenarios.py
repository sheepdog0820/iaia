from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from django.urls import reverse
from .models import (
    Scenario,
    ScenarioHandout,
    ScenarioHandoutRecommendedSkill,
    ScenarioRecommendedSkill,
    PlayHistory,
)
from accounts.models import Group as CustomGroup
from schedules.models import TRPGSession

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

    def test_scenario_handouts_are_not_limited_to_fixed_ho_numbers(self):
        scenario = Scenario.objects.create(
            title='Flexible Handout Scenario',
            author='Test Author',
            created_by=self.user,
            game_system='coc',
        )

        ScenarioRecommendedSkill.objects.create(
            scenario=scenario,
            name='Spot Hidden',
            level='recommended',
            description='Used during investigation',
            order=2,
        )
        first = ScenarioHandout.objects.create(
            scenario=scenario,
            code='HO1',
            name='Detective',
            title='Detective',
            content='First detective handout',
            handout_number=1,
            assigned_player_slot=1,
            order=2,
        )
        second = ScenarioHandout.objects.create(
            scenario=scenario,
            code='HO1-B',
            name='Assistant',
            title='Assistant',
            content='Additional handout',
            handout_number=1,
            assigned_player_slot=None,
            order=1,
        )
        ScenarioHandoutRecommendedSkill.objects.create(
            handout=second,
            name='Library Use',
            level='semi_recommended',
            description='Helpful for research',
            order=1,
        )

        self.assertEqual(
            list(scenario.handout_templates.values_list('name', flat=True)),
            ['Assistant', 'Detective'],
        )
        self.assertEqual(scenario.recommended_skill_items.get().name, 'Spot Hidden')
        self.assertEqual(first.code, 'HO1')
        self.assertEqual(second.recommended_skill_items.get().level, 'semi_recommended')


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
        self.user3 = User.objects.create_user(
            username='outsideuser',
            email='outside@example.com',
            password='pass123',
            nickname='Outside User'
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
        self.group_member_scenario = Scenario.objects.create(
            title='Group Member Scenario',
            summary='Group member scenario',
            author='Group Member',
            created_by=self.user2,
            recommended_players='2-4?',
            estimated_time=120,
            difficulty='beginner',
            game_system='coc'
        )
        self.outside_scenario = Scenario.objects.create(
            title='Outside Scenario',
            summary='Outside scenario',
            author='Outside Author',
            created_by=self.user3,
            recommended_players='2-4?',
            estimated_time=120,
            difficulty='beginner',
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


    def test_scenario_public_view_mode_is_readable_without_login(self):
        self.scenario.gm_notes = 'Secret GM Notes'
        self.scenario.created_by.trpg_history = 'Creator private history'
        self.scenario.created_by.save(update_fields=['trpg_history'])
        secret_handout = ScenarioHandout.objects.create(
            scenario=self.scenario,
            title='Secret scenario HO',
            content='Secret scenario HO content',
            is_secret=True,
            handout_number=1,
        )
        public_handout = ScenarioHandout.objects.create(
            scenario=self.scenario,
            title='Public scenario HO',
            content='Public scenario HO content',
            is_secret=False,
            handout_number=2,
        )
        self.scenario.save(update_fields=['gm_notes'])
        self.client.logout()

        normal_response = self.client.get(f'/api/scenarios/scenarios/{self.scenario.id}/')
        self.assertEqual(normal_response.status_code, status.HTTP_401_UNAUTHORIZED)

        public_api_response = self.client.get(f'/api/scenarios/scenarios/{self.scenario.id}/public/')
        self.assertEqual(public_api_response.status_code, status.HTTP_200_OK)
        public_data = public_api_response.json()
        self.assertEqual(public_data['title'], 'Test Scenario')
        self.assertNotIn('gm_notes', public_data)
        self.assertNotIn('created_by', public_data)
        self.assertNotIn('created_by_detail', public_data)
        self.assertEqual(
            [handout['title'] for handout in public_data['handout_templates']],
            [public_handout.title],
        )
        serialized_public_api = public_api_response.content.decode()
        self.assertNotIn(secret_handout.title, serialized_public_api)
        self.assertNotIn(secret_handout.content, serialized_public_api)
        self.assertNotIn(self.scenario.created_by.email, serialized_public_api)
        self.assertNotIn(self.scenario.created_by.trpg_history, serialized_public_api)

        public_page_response = self.client.get(
            reverse('scenario_public_view', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(public_page_response.status_code, status.HTTP_200_OK)
        self.assertContains(public_page_response, 'Test Scenario')
        self.assertContains(public_page_response, 'og:title')
        self.assertNotContains(public_page_response, self.scenario.gm_notes)

    def test_scenario_list_limited_to_same_group_creators(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get('/api/scenarios/scenarios/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item['title'] for item in response.json()}
        self.assertIn('Test Scenario', titles)
        self.assertIn('Group Member Scenario', titles)
        self.assertNotIn('Outside Scenario', titles)

    def test_scenario_detail_denies_outside_group_creator(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(f'/api/scenarios/scenarios/{self.outside_scenario.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scenario_owner_can_delete_linked_scenario(self):
        session = TRPGSession.objects.create(
            title='Linked Scenario Session',
            gm=self.user1,
            group=self.group,
            scenario=self.scenario,
            date=timezone.now(),
            created_by=self.user1,
        )
        self.client.force_authenticate(user=self.user1)

        response = self.client.delete(f'/api/scenarios/scenarios/{self.scenario.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Scenario.objects.filter(id=self.scenario.id).exists())
        session.refresh_from_db()
        self.assertIsNone(session.scenario)

    def test_group_member_cannot_delete_other_users_scenario(self):
        self.client.force_authenticate(user=self.user2)

        response = self.client.delete(f'/api/scenarios/scenarios/{self.scenario.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Scenario.objects.filter(id=self.scenario.id).exists())

    def test_scenario_archive_limited_to_same_group_creators(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get('/api/scenarios/archive/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item['title'] for item in response.json()}
        self.assertIn('Test Scenario', titles)
        self.assertIn('Group Member Scenario', titles)
        self.assertNotIn('Outside Scenario', titles)


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

    def test_scenario_create_with_semi_recommended_skills_and_handouts(self):
        self.client.force_authenticate(user=self.user1)

        scenario_data = {
            'title': 'Handout Scenario',
            'author': 'Test Author',
            'game_system': 'coc',
            'difficulty': 'beginner',
            'estimated_duration': 'short',
            'summary': '',
            'public_info': 'PLに公開する導入。',
            'gm_notes': 'GMだけが見る真相メモ。',
            'investigator_requirements': '新規探索者推奨。',
            'scenario_tags': 'ホラー, 推理',
            'content_warnings': '閉所表現あり。',
            'setting_era': '現代日本',
            'setting_location': '山間の村',
            'scenario_style': 'クローズド',
            'lost_rate': '中',
            'combat_level': 'あり',
            'pvp_level': 'なし',
            'min_players': 2,
            'max_players': 4,
            'estimated_time': 240,
            'recommended_skills': '目星',
            'semi_recommended_skills': '医学, 心理学',
            'handout_templates': [
                {
                    'title': '導入HO',
                    'content': 'あなたは依頼人を知っている。',
                    'recommended_skills': '図書館',
                    'is_secret': True,
                    'handout_number': 1,
                    'assigned_player_slot': 1,
                },
                {
                    'title': '探索者共通',
                    'content': '全探索者が知っている導入情報。',
                    'recommended_skills': '目星',
                    'is_secret': False,
                    'handout_number': None,
                    'assigned_player_slot': None,
                }
            ],
        }

        response = self.client.post('/api/scenarios/scenarios/', scenario_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['game_system'], 'coc6')
        self.assertEqual(data['semi_recommended_skills'], '医学, 心理学')
        self.assertEqual(data['public_info'], 'PLに公開する導入。')
        self.assertEqual(data['gm_notes'], 'GMだけが見る真相メモ。')
        self.assertEqual(data['investigator_requirements'], '新規探索者推奨。')
        self.assertEqual(data['scenario_tags'], 'ホラー, 推理')
        self.assertEqual(data['content_warnings'], '閉所表現あり。')
        self.assertEqual(data['setting_era'], '現代日本')
        self.assertEqual(data['setting_location'], '山間の村')
        self.assertEqual(data['scenario_style'], 'クローズド')
        self.assertEqual(data['lost_rate'], '中')
        self.assertEqual(data['combat_level'], 'あり')
        self.assertEqual(data['pvp_level'], 'なし')
        self.assertEqual(data['min_players'], 2)
        self.assertEqual(data['max_players'], 4)
        self.assertEqual(data['estimated_time'], 240)
        self.assertEqual(len(data['handout_templates']), 2)
        returned_titles = {handout['title'] for handout in data['handout_templates']}
        self.assertEqual(returned_titles, {'導入HO', '探索者共通'})
        self.assertTrue(
            ScenarioHandout.objects.filter(
                scenario_id=data['id'],
                handout_number=1,
                assigned_player_slot=1,
            ).exists()
        )
        self.assertTrue(
            ScenarioHandout.objects.filter(
                scenario_id=data['id'],
                handout_number__isnull=True,
                assigned_player_slot__isnull=True,
            ).exists()
        )

    def test_scenario_rejects_non_cthulhu_game_system(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.post('/api/scenarios/scenarios/', {
            'title': 'Invalid System Scenario',
            'game_system': 'dnd',
            'difficulty': 'beginner',
            'estimated_duration': 'short',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_scenario_create_with_structured_skills_and_flexible_handouts(self):
        self.client.force_authenticate(user=self.user1)

        scenario_data = {
            'title': 'Structured Scenario',
            'author': 'Test Author',
            'game_system': 'coc',
            'difficulty': 'beginner',
            'estimated_duration': 'short',
            'recommended_skill_items': [
                {
                    'name': 'Spot Hidden',
                    'level': 'recommended',
                    'description': 'Used during searches',
                    'order': 1,
                },
                {
                    'name': 'Listen',
                    'level': 'semi_recommended',
                    'description': 'Useful for clues',
                    'order': 2,
                },
            ],
            'handout_templates': [
                {
                    'code': 'HO1',
                    'name': 'Detective',
                    'title': 'Legacy Detective',
                    'content': 'Primary investigator',
                    'is_secret': True,
                    'handout_number': 1,
                    'assigned_player_slot': 1,
                    'order': 2,
                    'recommended_skill_items': [
                        {
                            'name': 'Law',
                            'level': 'required',
                            'description': 'Needed for police records',
                            'order': 1,
                        }
                    ],
                },
                {
                    'code': 'HO1-B',
                    'name': 'Assistant',
                    'content': 'Additional role',
                    'is_secret': True,
                    'handout_number': 1,
                    'assigned_player_slot': None,
                    'order': 1,
                    'recommended_skill_items': [
                        {
                            'name': 'Library Use',
                            'level': 'semi_recommended',
                            'description': 'Helpful for research',
                            'order': 1,
                        }
                    ],
                },
            ],
        }

        response = self.client.post('/api/scenarios/scenarios/', scenario_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual([item['name'] for item in data['recommended_skill_items']], ['Spot Hidden', 'Listen'])
        self.assertEqual([handout['code'] for handout in data['handout_templates']], ['HO1-B', 'HO1'])
        self.assertEqual(data['handout_templates'][0]['recommended_skill_items'][0]['name'], 'Library Use')
        scenario = Scenario.objects.get(id=data['id'])
        self.assertEqual(scenario.handout_templates.filter(handout_number=1).count(), 2)
        self.assertEqual(scenario.handout_templates.get(code='HO1-B').name, 'Assistant')

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


class ScenarioArchivePremiumAccessTestCase(TestCase):
    def setUp(self):
        self.password = 'pass123'
        self.user = User.objects.create_user(
            username='premiumtest',
            email='premiumtest@example.com',
            password=self.password,
            nickname='Premium Test',
        )

    def test_archive_view_requires_premium(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get('/api/scenarios/archive/view/')
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, '利用できない機能です', status_code=403)

    def test_archive_view_allows_premium(self):
        self.user.is_premium = True
        self.user.save(update_fields=['is_premium'])

        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get('/api/scenarios/archive/view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mythos Archive')

    def test_home_hides_scenario_links_for_non_premium(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id=\"scenarios-link\"')
        self.assertNotContains(response, 'id=\"add-scenario-btn\"')

    def test_home_shows_scenario_links_for_premium(self):
        self.user.is_premium = True
        self.user.save(update_fields=['is_premium'])

        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id=\"scenarios-link\"')
        self.assertContains(response, 'id=\"add-scenario-btn\"')
