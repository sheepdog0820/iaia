"""
Advanced UI tests for Character Creation with multiple skills

Tests comprehensive UI functionality including:
- DEX to Dodge skill synchronization
- Custom skill base value editing
- Multiple skill allocation
- Complex character creation scenarios
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import time
import json
from decimal import Decimal

# Optional imports for Selenium tests
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from accounts.character_models import CharacterSheet, CharacterSkill

User = get_user_model()


class CharacterCreateAdvancedUITest(TestCase):
    """Non-Selenium UI tests for advanced character creation features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_create_character_with_multiple_skills(self):
        """Test creating a character with multiple skills allocated"""
        data = {
            'name': 'Advanced Explorer',
            'player_name': 'Test Player',
            'age': 30,
            'gender': '女性',
            'occupation': '考古学者',
            'str_value': 12,
            'con_value': 14,
            'pow_value': 16,
            'dex_value': 15,  # This affects dodge skill
            'app_value': 10,
            'siz_value': 13,
            'int_value': 17,  # High INT for more hobby points
            'edu_value': 18,  # High EDU for more occupation points
            'hit_points_max': 14,  # (14+13)/2 = 13.5 -> 14
            'hit_points_current': 14,
            'magic_points_max': 16,
            'magic_points_current': 16,
            'sanity_max': 80,
            'sanity_current': 80,
            'skills': [
                {
                    'skill_id': 'archaeology',
                    'base_value': 1,
                    'occupation_points': 50,
                    'interest_points': 10,
                    'other_points': 0
                },
                {
                    'skill_id': 'library_use',
                    'base_value': 25,
                    'occupation_points': 30,
                    'interest_points': 15,
                    'other_points': 0
                },
                {
                    'skill_id': 'spot_hidden',
                    'base_value': 25,
                    'occupation_points': 20,
                    'interest_points': 0,
                    'other_points': 0
                },
                {
                    'skill_id': 'dodge',
                    'base_value': 30,  # DEX×2 = 15×2 = 30
                    'occupation_points': 0,
                    'interest_points': 20,
                    'other_points': 0
                },
                {
                    'skill_id': 'own_language',
                    'base_value': 90,  # EDU×5 = 18×5 = 90
                    'occupation_points': 0,
                    'interest_points': 0,
                    'other_points': 0
                }
            ]
        }
        
        response = self.client.post(
            '/api/accounts/character-sheets/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verify character was created with skills
        character = CharacterSheet.objects.get(name='Advanced Explorer')
        self.assertEqual(character.dex_value, 15)
        
        # Check skills were created
        skills = CharacterSkill.objects.filter(character=character)
        self.assertTrue(skills.exists())
        
        # Verify dodge skill calculation
        dodge_skill = skills.filter(skill_id='dodge').first()
        if dodge_skill:
            self.assertEqual(dodge_skill.base_value, 30)  # DEX×2
            
        # Verify own language skill
        language_skill = skills.filter(skill_id='own_language').first()
        if language_skill:
            self.assertEqual(language_skill.base_value, 90)  # EDU×5


if SELENIUM_AVAILABLE:
    class CharacterCreateAdvancedSeleniumTest(StaticLiveServerTestCase):
        """Selenium-based UI tests for advanced character creation features"""
        
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            
            # Chrome options for headless testing
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            try:
                cls.selenium = webdriver.Chrome(options=options)
            except Exception:
                # Try with Chromium if Chrome fails
                options.binary_location = '/usr/bin/chromium-browser'
                cls.selenium = webdriver.Chrome(options=options)
                
            cls.selenium.implicitly_wait(10)
            
        @classmethod
        def tearDownClass(cls):
            cls.selenium.quit()
            super().tearDownClass()
            
        def setUp(self):
            self.user = User.objects.create_user(
                username='testuser',
                password='testpass123'
            )
            
        def login(self):
            """Helper method to log in via Selenium"""
            self.selenium.get(f'{self.live_server_url}/accounts/login/')
            username_input = self.selenium.find_element(By.NAME, 'login')
            password_input = self.selenium.find_element(By.NAME, 'password')
            username_input.send_keys('testuser')
            password_input.send_keys('testpass123')
            password_input.send_keys(Keys.RETURN)
            
            # Wait for redirect
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/profile/')
            )
            
        def test_dex_to_dodge_skill_synchronization(self):
            """Test that changing DEX updates dodge skill base value"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for page to load
            dex_field = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'dex'))
            )
            
            # Set initial DEX value
            dex_field.clear()
            dex_field.send_keys('10')
            dex_field.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Find dodge skill base value
            dodge_base = self.selenium.find_element(By.ID, 'base_dodge')
            self.assertEqual(dodge_base.get_attribute('value'), '20')  # 10×2
            
            # Change DEX value
            dex_field.clear()
            dex_field.send_keys('18')
            dex_field.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Check dodge skill updated
            self.assertEqual(dodge_base.get_attribute('value'), '36')  # 18×2
            
        def test_custom_skill_base_values(self):
            """Test editing custom base values for skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for skills to load
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'skillsList'))
            )
            
            # Find archaeology skill base value
            archaeology_base = self.selenium.find_element(By.ID, 'base_archaeology')
            original_value = archaeology_base.get_attribute('value')
            
            # Edit base value
            archaeology_base.clear()
            archaeology_base.send_keys('10')
            archaeology_base.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Verify custom class applied
            self.assertIn('custom-base', archaeology_base.get_attribute('class'))
            
            # Right-click to reset
            actions = ActionChains(self.selenium)
            actions.context_click(archaeology_base).perform()
            
            time.sleep(0.5)
            
            # Check value reset
            self.assertEqual(archaeology_base.get_attribute('value'), original_value)
            
        def test_occupation_template_with_skills(self):
            """Test applying occupation template and allocating skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Set EDU for skill points
            edu_field = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'edu'))
            )
            edu_field.clear()
            edu_field.send_keys('16')
            edu_field.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Select archaeologist template
            occupation_select = self.selenium.find_element(By.ID, 'occupationTemplate')
            Select(occupation_select).select_by_value('考古学者')
            
            # Apply template
            apply_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="applySelectedTemplate()"]')
            apply_btn.click()
            
            time.sleep(0.5)
            
            # Check occupation points
            occupation_points = self.selenium.find_element(By.ID, 'occupationPointsDisplay')
            self.assertIn('320', occupation_points.text)  # EDU×20
            
            # Allocate points to archaeology
            archaeology_occ = self.selenium.find_element(By.CSS_SELECTOR, '[data-skill="archaeology"].skill-occupation-input')
            archaeology_occ.clear()
            archaeology_occ.send_keys('60')
            archaeology_occ.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Check remaining points
            remaining = self.selenium.find_element(By.ID, 'remainingOccupationPoints')
            self.assertIn('260', remaining.text)
            
        def test_multiple_skill_allocation(self):
            """Test allocating points to multiple skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Set ability scores
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'edu'))
            )
            
            # Set EDU and INT for skill points
            self.selenium.find_element(By.ID, 'edu').send_keys('15')
            self.selenium.find_element(By.ID, 'int').send_keys('14')
            self.selenium.find_element(By.ID, 'int').send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Allocate occupation points to multiple skills
            skills_to_allocate = [
                ('archaeology', 40),
                ('library_use', 30),
                ('spot_hidden', 25),
                ('history', 35),
                ('other_language', 20)
            ]
            
            for skill_id, points in skills_to_allocate:
                skill_input = self.selenium.find_element(
                    By.CSS_SELECTOR, 
                    f'[data-skill="{skill_id}"].skill-occupation-input'
                )
                skill_input.clear()
                skill_input.send_keys(str(points))
                skill_input.send_keys(Keys.TAB)
                time.sleep(0.2)
                
            # Allocate interest points
            interest_skills = [
                ('dodge', 20),
                ('handgun', 15),
                ('first_aid', 10)
            ]
            
            for skill_id, points in interest_skills:
                skill_input = self.selenium.find_element(
                    By.CSS_SELECTOR, 
                    f'[data-skill="{skill_id}"].skill-interest-input'
                )
                skill_input.clear()
                skill_input.send_keys(str(points))
                skill_input.send_keys(Keys.TAB)
                time.sleep(0.2)
                
        def test_allocated_skills_tab(self):
            """Test that allocated skills appear in the allocated tab"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for skills to load
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'skillsList'))
            )
            
            # Allocate points to a skill
            archaeology_occ = self.selenium.find_element(
                By.CSS_SELECTOR, 
                '[data-skill="archaeology"].skill-occupation-input'
            )
            archaeology_occ.clear()
            archaeology_occ.send_keys('50')
            archaeology_occ.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Switch to allocated skills tab
            allocated_tab = self.selenium.find_element(By.CSS_SELECTOR, '[data-category="allocated"]')
            allocated_tab.click()
            
            time.sleep(0.5)
            
            # Check that archaeology is visible
            allocated_skills = self.selenium.find_elements(By.CSS_SELECTOR, '#skillsList .skill-item:not([style*="display: none"])')
            skill_names = [skill.find_element(By.CSS_SELECTOR, '.skill-name').text for skill in allocated_skills]
            
            self.assertIn('考古学', skill_names)
            
        def test_complete_character_creation_flow(self):
            """Test complete character creation with multiple skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Fill basic info
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character_name'))
            )
            
            self.selenium.find_element(By.ID, 'character_name').send_keys('完全なる探索者')
            self.selenium.find_element(By.ID, 'player_name').send_keys('テストプレイヤー')
            self.selenium.find_element(By.ID, 'age').send_keys('35')
            Select(self.selenium.find_element(By.ID, 'gender')).select_by_value('男性')
            
            # Roll all abilities
            roll_all_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="rollAllAbilities()"]')
            roll_all_btn.click()
            
            time.sleep(1)
            
            # Apply occupation template
            Select(self.selenium.find_element(By.ID, 'occupationTemplate')).select_by_value('私立探偵')
            self.selenium.find_element(By.CSS_SELECTOR, '[onclick="applySelectedTemplate()"]').click()
            
            time.sleep(0.5)
            
            # Allocate some skills
            skills = [
                ('spot_hidden', 40),
                ('psychology', 30),
                ('library_use', 20)
            ]
            
            for skill_id, points in skills:
                skill_input = self.selenium.find_element(
                    By.CSS_SELECTOR, 
                    f'[data-skill="{skill_id}"].skill-occupation-input'
                )
                skill_input.clear()
                skill_input.send_keys(str(points))
                skill_input.send_keys(Keys.TAB)
                time.sleep(0.2)
                
            # Submit form
            submit_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="validateAndSubmit()"]')
            submit_btn.click()
            
            # Wait for redirect
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/character-sheets/')
            )
            
            # Verify character was created
            self.assertTrue(
                CharacterSheet.objects.filter(name='完全なる探索者').exists()
            )
            
            # Verify skills were saved
            character = CharacterSheet.objects.get(name='完全なる探索者')
            skills = CharacterSkill.objects.filter(character=character)
            self.assertGreater(skills.count(), 0)
            
            # Check specific skills
            spot_hidden = skills.filter(skill_id='spot_hidden').first()
            if spot_hidden:
                self.assertEqual(spot_hidden.occupation_points, 40)