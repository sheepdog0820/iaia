"""
Simple JavaScript Error Detection Test

Directly tests the character creation page for JavaScript errors without login.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.test import override_settings
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
        """Test that character creation page renders without template errors"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertEqual(response.status_code, 200)
        
        # Check that required JavaScript functions are present
        content = response.content.decode('utf-8')
        
        # Check for core functions
        self.assertIn('function rollDice', content)
        self.assertIn('function calculateDerivedStats', content)
        self.assertIn('function updateSkillTotals', content)
        self.assertIn('function updateDynamicSkillBases', content)
        
        # Check that console.log statements are commented out
        self.assertNotIn("console.log('updateSkillTotals called');", content)
        self.assertNotIn("console.log('推奨技能:', occupation.skills);", content)
        
        # Check for skill definitions
        self.assertIn('ALL_SKILLS_6TH', content)
        self.assertIn('COMBAT_SKILLS', content)
        
        # Check for proper jQuery usage
        self.assertIn('$(document).ready', content)
        
        # Check for form elements
        self.assertIn('id="character_name"', content)
        self.assertIn('id="dex"', content)
        self.assertIn('id="base_dodge"', content)
        
    def test_javascript_syntax_check(self):
        """Check for common JavaScript syntax errors"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        # Check for unclosed brackets/parentheses
        open_braces = content.count('{')
        close_braces = content.count('}')
        # Allow some difference due to template syntax
        self.assertLess(abs(open_braces - close_braces), 10, 
            f"Mismatched braces: {open_braces} open, {close_braces} close")
        
        # Check for common syntax errors
        self.assertNotIn('function ()', content)  # Anonymous function without name
        self.assertNotIn(';;', content)  # Double semicolon
        
        # Check that updateDynamicSkillBases is called properly
        self.assertIn('updateDynamicSkillBases();', content)
        
    def test_skill_base_value_functionality(self):
        """Test that skill base value editing functionality is properly implemented"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        # Check for custom base value storage
        self.assertIn('window.customBaseValues', content)
        
        # Check for base value input event handlers
        self.assertIn("$('body').on('input', '[id^=\"base_\"]'", content)
        self.assertIn("$('body').on('contextmenu', '[id^=\"base_\"]'", content)
        
        # Check for visual feedback classes
        self.assertIn('skill-base-input', content)
        self.assertIn('custom-base', content)
        
    def test_dex_dodge_skill_synchronization(self):
        """Test that DEX to dodge skill synchronization is implemented"""
        response = self.client.get('/accounts/character/create/6th/')
        content = response.content.decode('utf-8')
        
        # Check updateDynamicSkillBases function
        self.assertIn('function updateDynamicSkillBases()', content)
        
        # Check DEX calculation for dodge
        self.assertIn('const dex = parseInt(document.getElementById(\'dex\')?.value) || 0;', content)
        self.assertIn('const dodgeBaseEl = document.getElementById(\'base_dodge\');', content)
        self.assertIn('dodgeBaseEl.value = dex * 2;', content)
        
        # Check that it's called on DEX change
        self.assertIn('calculateDerivedStats', content)
        self.assertIn('updateDynamicSkillBases', content)