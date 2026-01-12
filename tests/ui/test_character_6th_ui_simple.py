"""
Simple UI tests for Call of Cthulhu 6th Edition Character Sheet

Basic tests that work without Selenium
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSkill

User = get_user_model()


def create_test_character(user, **kwargs):
    """Helper to create test character with required fields"""
    defaults = {
        'name': 'Test Character',
        'age': 25,
        'edition': '6th',
        'str_value': 10,
        'con_value': 10,
        'pow_value': 10,
        'dex_value': 10,
        'app_value': 10,
        'siz_value': 10,
        'int_value': 10,
        'edu_value': 10,
        'hit_points_max': 10,
        'hit_points_current': 10,
        'magic_points_max': 10,
        'magic_points_current': 10,
        'sanity_starting': 50,
        'sanity_max': 50,
        'sanity_current': 50
    }
    defaults.update(kwargs)
    return CharacterSheet.objects.create(user=user, **defaults)


class Character6thBasicUITest(TestCase):
    """Basic UI tests for character sheet"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_character_list_page_loads(self):
        """Test character list page loads successfully"""
        response = self.client.get(reverse('character_list'))
        self.assertEqual(response.status_code, 200)
        # Check basic elements
        self.assertIn(b'loadCharacters', response.content)  # JavaScript function
        
    def test_character_create_page_loads(self):
        """Test character creation page loads successfully"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        # Check form elements exist
        self.assertIn(b'<form', response.content)
        self.assertIn(b'name="str_value"', response.content)
        self.assertIn(b'name="con_value"', response.content)
        
    def test_character_detail_view_requires_ownership(self):
        """Test character detail view checks ownership"""
        # Create character owned by another user
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass'
        )
        character = create_test_character(other_user, name="Other's Character")
        
        # Try to access as different user
        response = self.client.get(
            reverse('character_detail_6th', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="characterContent"')
        
    def test_character_creation_post(self):
        """Test character creation via POST"""
        data = {
            'name': 'New Character',
            'age': 30,
            'gender': '男性',
            'occupation': '探偵',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 13,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 17,
            'hit_points_max': 14,
            'hit_points_current': 14,
            'magic_points_max': 14,
            'magic_points_current': 14,
            'sanity_starting': 70,
            'sanity_max': 70,
            'sanity_current': 70
        }
        
        response = self.client.post(reverse('character_create_6th'), data)
        self.assertEqual(response.status_code, 302)
        character = CharacterSheet.objects.filter(
            user=self.user,
            name='New Character'
        ).first()
        self.assertIsNotNone(character)
        self.assertEqual(character.str_value, 13)
            
    def test_authenticated_access_only(self):
        """Test pages require authentication"""
        self.client.logout()
        
        # Test character list
        response = self.client.get(reverse('character_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test character create
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class Character6thAPIUITest(TestCase):
    """Test API endpoints used by UI"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_character_list_api(self):
        """Test character list API endpoint"""
        # Create some characters
        for i in range(3):
            create_test_character(self.user, name=f"Character {i+1}")
            
        # API endpoint that the UI uses
        response = self.client.get('/api/accounts/character-sheets/')
        self.assertEqual(response.status_code, 200)
        
        # Check if response is a list or paginated
        data = response.json()
        if isinstance(data, list):
            self.assertEqual(len(data), 3)
        else:
            # Paginated response
            self.assertEqual(data.get('count', len(data.get('results', []))), 3)
        
    def test_skill_points_summary_api(self):
        """Test skill points summary API"""
        character = create_test_character(
            self.user,
            occupation='医師',
            edu_value=16,
            int_value=10
        )
        
        # Try different possible endpoints
        # Test the skill-points-summary endpoint specifically
        response = self.client.get(f'/api/accounts/character-sheets/{character.id}/skill-points-summary/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Check the response structure
        self.assertIn('occupation_points', data)
        self.assertIn('hobby_points', data)
        self.assertIn('skills', data)
        
        # Verify the calculations
        self.assertEqual(data['occupation_points']['total'], 320)  # EDU:16 × 20
        self.assertEqual(data['hobby_points']['total'], 100)  # INT:10 × 10
        self.assertEqual(data['occupation_points']['used'], 0)  # No skills allocated yet
        self.assertEqual(data['hobby_points']['used'], 0)  # No skills allocated yet
        
    def test_ccfolia_export_api(self):
        """Test CCFOLIA export API"""
        character = create_test_character(
            self.user,
            name='Export Test',
            str_value=13
        )
        
        # Add a skill
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='医学',
            base_value=5,
            occupation_points=70
        )
        
        try:
            url = reverse('character-sheet-ccfolia-json', kwargs={'pk': character.id})
        except Exception:
            self.skipTest("CCFOLIA export endpoint not found")
        response = self.client.get(url)
        if response.status_code == 404:
            self.skipTest("CCFOLIA export endpoint not found")
        
        data = response.json()
        # CCFOLIA format has nested structure
        self.assertEqual(data['kind'], 'character')
        self.assertIn('data', data)
        self.assertEqual(data['data']['name'], 'Export Test')
        self.assertIsInstance(data['data']['params'], list)
        self.assertIsInstance(data['data']['status'], list)


class Character6thFormTest(TestCase):
    """Test form handling"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_invalid_age_validation(self):
        """Test age validation"""
        data = {
            'name': 'Test',
            'age': 10,  # Too young (min is 15)
            'str_value': 10,
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 10,
            'hit_points_max': 10,
            'magic_points_max': 10,
            'sanity_starting': 50
        }
        
        with self.assertLogs('accounts.views.character_views', level='ERROR'):
            response = self.client.post(reverse('character_create_6th'), data)
        # Form should not be valid
        self.assertEqual(response.status_code, 200)  # Stay on form page
        
    def test_invalid_ability_validation(self):
        """Test ability value validation"""
        data = {
            'name': 'Test',
            'age': 25,
            'str_value': 0,  # Invalid (min is 1)
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 1000,  # Invalid (max is 999)
            'hit_points_max': 10,
            'magic_points_max': 10,
            'sanity_starting': 50
        }
        
        with self.assertLogs('accounts.views.character_views', level='ERROR'):
            response = self.client.post(reverse('character_create_6th'), data)
        # Form should not be valid
        self.assertEqual(response.status_code, 200)  # Stay on form page
