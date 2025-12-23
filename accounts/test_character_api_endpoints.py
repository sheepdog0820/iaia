"""
Test character API endpoints
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.character_models import CharacterSheet, CharacterSkill, GrowthRecord

User = get_user_model()


class CharacterAPIEndpointsTest(TestCase):
    """Test custom character API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test character
        self.character = CharacterSheet.objects.create(
            user=self.user,
            edition='6th',
            name='Test Character',
            age=25,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=16,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
            occupation_multiplier=20
        )
        
    def test_skill_points_summary_endpoint(self):
        """Test skill-points-summary endpoint"""
        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/skill-points-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('occupation_points', data)
        self.assertIn('hobby_points', data)
        self.assertIn('skills', data)
        
        # Check calculations
        self.assertEqual(data['occupation_points']['total'], 320)  # EDU:16 × 20
        self.assertEqual(data['hobby_points']['total'], 100)  # INT:10 × 10
        
    def test_ccfolia_json_endpoint(self):
        """Test ccfolia-json endpoint"""
        url = reverse('character-sheet-ccfolia-json', kwargs={'pk': self.character.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['kind'], 'character')
        self.assertIn('data', data)
        self.assertEqual(data['data']['name'], 'Test Character')
        
    def test_allocate_skill_points_endpoint(self):
        """Test allocate-skill-points endpoint"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='医学',
            base_value=5
        )
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/allocate_skill_points/',
            {
                'skill_id': skill.id,
                'occupation_points': 50,
                'interest_points': 10
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        skill.refresh_from_db()
        self.assertEqual(skill.occupation_points, 50)
        self.assertEqual(skill.interest_points, 10)
        
    def test_batch_allocate_skill_points_endpoint(self):
        """Test batch-allocate-skill-points endpoint"""
        skill_a = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='Pistol',
            base_value=20
        )
        skill_b = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='Dodge',
            base_value=20
        )

        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/batch_allocate_skill_points/',
            {
                'allocations': [
                    {
                        'skill_id': skill_a.id,
                        'occupation_points': 30,
                        'interest_points': 0
                    },
                    {
                        'skill_id': skill_b.id,
                        'occupation_points': 0,
                        'interest_points': 20
                    }
                ]
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['updated_count'], 2)


    def test_combat_summary_endpoint(self):
        """Test combat-summary endpoint"""
        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/combat_summary/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('damage_bonus', data)
        self.assertIn('total_armor_points', data)
        self.assertIn('weapons_count', data)
        self.assertIn('armor_count', data)
        self.assertIn('weapons', data)
        self.assertIn('armors', data)


    def test_growth_summary_endpoint(self):
        """Test growth-summary endpoint"""
        GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date='2024-01-01',
            scenario_name='Test Scenario',
            sanity_gained=1,
            sanity_lost=2,
            experience_gained=5
        )

        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/growth_summary/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['total_sessions'], 1)
        self.assertIn('recent_scenarios', data)


    def test_background_endpoint(self):
        """Test background endpoint"""
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/background/',
            {
                'personal_description': 'A brave investigator',
                'ideals_and_beliefs': 'Truth above all',
                'significant_people': 'My mentor, Professor Smith',
                'meaningful_locations': 'The old library',
                'treasured_possessions': 'My father\'s watch',
                'traits': 'Curious and stubborn'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = response.json()
        self.assertEqual(data['personal_description'], 'A brave investigator')
        self.assertEqual(data['ideals_and_beliefs'], 'Truth above all')
