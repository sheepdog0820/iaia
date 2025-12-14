"""
Test character API endpoints
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.character_models import CharacterSheet, CharacterSkill

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
        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/ccfolia-json/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['kind'], 'character')
        self.assertIn('data', data)
        self.assertEqual(data['data']['name'], 'Test Character')
        
    def test_allocate_skill_points_endpoint(self):
        """Test allocate-skill-points endpoint"""
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/allocate-skill-points/',
            {
                'skill_name': '医学',
                'occupation_points': 50,
                'interest_points': 10
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('skill', data)
        self.assertEqual(data['skill']['name'], '医学')
        self.assertEqual(data['skill']['occupation_points'], 50)
        
    def test_batch_allocate_skill_points_endpoint(self):
        """Test batch-allocate-skill-points endpoint"""
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/batch-allocate-skill-points/',
            {
                'skills': [
                    {
                        'skill_name': '拳銃',
                        'base_value': 20,
                        'occupation_points': 30
                    },
                    {
                        'skill_name': '回避',
                        'base_value': 20,  # DEX×2
                        'interest_points': 20
                    }
                ]
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('skills', data)
        self.assertEqual(len(data['skills']), 2)
        
    def test_combat_summary_endpoint(self):
        """Test combat-summary endpoint"""
        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/combat-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('damage_bonus', data)
        self.assertIn('weapons', data)
        self.assertIn('combat_skills', data)
        self.assertIn('hp', data)
        
    def test_growth_summary_endpoint(self):
        """Test growth-summary endpoint"""
        response = self.client.get(
            f'/api/accounts/character-sheets/{self.character.id}/growth-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('session_count', data)
        self.assertIn('growth_records', data)
        self.assertIn('version_history', data)
        
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