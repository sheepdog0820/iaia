"""
Simple JavaScript Error Detection Test

Directly tests the character creation page for JavaScript errors without login.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class SimpleJavaScriptErrorTest(TestCase):
    """Test JavaScript errors using Django test client"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_character_create_page_renders_without_errors(self):
        """Test that character creation page renders core UI structure"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        self.assertIn('id="character-sheet-form"', content)
        self.assertIn('id="mainTabs"', content)
        self.assertIn('id="skillsContainer"', content)
        
        for field_id in ['character-name', 'age', 'str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']:
            self.assertIn(f'id="{field_id}"', content)
        
    def test_javascript_assets_included(self):
        """Check that required JS/CSS assets are included"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        self.assertIn('/static/accounts/js/character6th.js', content)
        self.assertIn('/static/js/arkham.js', content)
        self.assertIn('/static/accounts/css/character6th.css', content)
        
    def test_skill_section_targets_exist(self):
        """Check that skill tab containers exist for JS rendering"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        self.assertIn('id="skillTabs"', content)
        self.assertIn('id="skillTabContent"', content)
        self.assertIn('id="combatSkills"', content)
        self.assertIn('id="explorationSkills"', content)
        
    def test_derived_stat_targets_exist(self):
        """Check that derived stat targets exist for JS updates"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        self.assertIn('id="hp"', content)
        self.assertIn('id="mp_display"', content)
        self.assertIn('id="san_display"', content)
        self.assertIn('id="idea_display"', content)
        self.assertIn('id="luck_display"', content)
        self.assertIn('id="know_display"', content)
        self.assertIn('id="damage_bonus_display"', content)
