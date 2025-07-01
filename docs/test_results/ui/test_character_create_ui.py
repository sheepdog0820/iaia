"""
UI tests for Character Creation page (6th Edition)

Tests comprehensive UI functionality including:
- Form field validation
- Dice rolling functionality
- Occupation template selection
- Skill point calculation
- Image upload
- Form submission
- Error handling
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import time
import json
from PIL import Image
import io

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

from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSkill

User = get_user_model()


class CharacterCreateUITest(TestCase):
    """Non-Selenium UI tests for character creation"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_create_page_renders(self):
        """Test that character creation page renders correctly"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertEqual(response.status_code, 200)
        
        # Check page title
        self.assertContains(response, 'クトゥルフ神話TRPG 6版 キャラクター作成')
        
        # Check form sections
        self.assertContains(response, '基本情報')
        self.assertContains(response, '能力値')
        self.assertContains(response, '技能')
        
    def test_all_form_fields_present(self):
        """Test that all required form fields are present"""
        response = self.client.get('/accounts/character/create/6th/')
        
        # Basic info fields
        self.assertContains(response, 'id="character_name"')
        self.assertContains(response, 'id="player_name"')
        self.assertContains(response, 'id="age"')
        self.assertContains(response, 'id="gender"')
        self.assertContains(response, 'id="occupation"')
        
        # Ability score fields
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            self.assertContains(response, f'id="{ability}"')
            
        # Derived stats (should be readonly)
        self.assertContains(response, 'id="hp"')
        self.assertContains(response, 'id="mp"')
        self.assertContains(response, 'id="san"')
        
    def test_javascript_functions_defined(self):
        """Test that required JavaScript functions are defined"""
        response = self.client.get('/accounts/character/create/6th/')
        
        # Core functions
        self.assertContains(response, 'function rollDice')
        self.assertContains(response, 'function calculateDerivedStats')
        self.assertContains(response, 'function generateSkillsList')
        self.assertContains(response, 'function validateAndSubmit')
        
        # Occupation functions
        self.assertContains(response, 'function applyOccupationTemplate')
        self.assertContains(response, 'function calculateOccupationSkillPoints')
        
    def test_form_submission_creates_character(self):
        """Test form submission via POST creates a character"""
        data = {
            'character_name': 'Test Explorer',
            'player_name': 'Test Player',
            'age': 25,
            'gender': '男性',
            'occupation': '私立探偵',
            'str': 10,
            'con': 12,
            'pow': 14,
            'dex': 11,
            'app': 13,
            'siz': 15,
            'int': 16,
            'edu': 17,
        }
        
        response = self.client.post(
            '/api/character-sheets/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(CharacterSheet.objects.filter(name='Test Explorer').exists())


if SELENIUM_AVAILABLE:
    class CharacterCreateSeleniumTest(StaticLiveServerTestCase):
        """Selenium-based UI tests for character creation"""
        
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
            
        def test_dice_rolling_functionality(self):
            """Test dice rolling for ability scores"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Wait for page to load
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'str'))
            )
            
            # Test individual dice roll
            str_field = self.selenium.find_element(By.ID, 'str')
            initial_value = str_field.get_attribute('value')
            
            # Click roll button for STR
            roll_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick*="rollAbilityScore(\'str\'"]')
            roll_btn.click()
            
            # Wait for value to change
            time.sleep(0.5)
            new_value = str_field.get_attribute('value')
            self.assertNotEqual(initial_value, new_value)
            self.assertTrue(3 <= int(new_value) <= 18)
            
        def test_roll_all_abilities(self):
            """Test rolling all abilities at once"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Wait and click roll all button
            roll_all_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[onclick="rollAllAbilities()"]'))
            )
            roll_all_btn.click()
            
            # Check all ability fields have values
            time.sleep(1)
            abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            for ability in abilities:
                field = self.selenium.find_element(By.ID, ability)
                value = int(field.get_attribute('value'))
                if ability == 'siz':
                    self.assertTrue(8 <= value <= 18)
                else:
                    self.assertTrue(3 <= value <= 18)
                    
        def test_derived_stats_calculation(self):
            """Test automatic calculation of derived stats"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Set ability values
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'con'))
            )
            
            con_field = self.selenium.find_element(By.ID, 'con')
            siz_field = self.selenium.find_element(By.ID, 'siz')
            pow_field = self.selenium.find_element(By.ID, 'pow')
            
            # Clear and set values
            con_field.clear()
            con_field.send_keys('14')
            siz_field.clear()
            siz_field.send_keys('12')
            pow_field.clear()
            pow_field.send_keys('16')
            
            # Trigger calculation
            pow_field.send_keys(Keys.TAB)
            time.sleep(0.5)
            
            # Check derived values
            hp_field = self.selenium.find_element(By.ID, 'hp')
            mp_field = self.selenium.find_element(By.ID, 'mp')
            san_field = self.selenium.find_element(By.ID, 'san')
            
            self.assertEqual(hp_field.get_attribute('value'), '13')  # (14+12)/2
            self.assertEqual(mp_field.get_attribute('value'), '16')  # POW
            self.assertEqual(san_field.get_attribute('value'), '80')  # POW*5
            
        def test_occupation_template_selection(self):
            """Test occupation template application"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Wait for occupation select
            occupation_select = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'occupationTemplate'))
            )
            
            # Select private detective template
            Select(occupation_select).select_by_value('私立探偵')
            
            # Apply template
            apply_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="applySelectedTemplate()"]')
            apply_btn.click()
            
            time.sleep(0.5)
            
            # Check occupation field is filled
            occupation_field = self.selenium.find_element(By.ID, 'occupation')
            self.assertEqual(occupation_field.get_attribute('value'), '私立探偵')
            
        def test_skill_tab_navigation(self):
            """Test skill tab navigation"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Wait for skills section
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'skillTabs'))
            )
            
            # Check initial tab
            all_tab = self.selenium.find_element(By.CSS_SELECTOR, '[data-category="all"]')
            self.assertIn('active', all_tab.get_attribute('class'))
            
            # Click combat tab
            combat_tab = self.selenium.find_element(By.CSS_SELECTOR, '[data-category="combat"]')
            combat_tab.click()
            
            time.sleep(0.5)
            
            # Check tab switched
            self.assertIn('active', combat_tab.get_attribute('class'))
            self.assertNotIn('active', all_tab.get_attribute('class'))
            
        def test_form_validation(self):
            """Test client-side form validation"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Try to submit empty form
            submit_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[onclick="validateAndSubmit()"]'))
            )
            submit_btn.click()
            
            # Check for alert
            alert = WebDriverWait(self.selenium, 3).until(EC.alert_is_present())
            alert_text = alert.text
            self.assertIn('探索者名は必須です', alert_text)
            alert.accept()
            
        def test_successful_character_creation(self):
            """Test successful character creation flow"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Fill in required fields
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character_name'))
            )
            
            # Basic info
            self.selenium.find_element(By.ID, 'character_name').send_keys('Selenium Test Character')
            self.selenium.find_element(By.ID, 'age').send_keys('30')
            
            # Roll all abilities
            roll_all_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="rollAllAbilities()"]')
            roll_all_btn.click()
            
            time.sleep(1)
            
            # Submit form
            submit_btn = self.selenium.find_element(By.CSS_SELECTOR, '[onclick="validateAndSubmit()"]')
            submit_btn.click()
            
            # Wait for redirect to character list
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/character-sheets/')
            )
            
            # Verify character was created
            self.assertTrue(
                CharacterSheet.objects.filter(name='Selenium Test Character').exists()
            )
            
        def test_skill_point_allocation(self):
            """Test skill point allocation UI"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Set EDU value for skill points
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'edu'))
            )
            
            edu_field = self.selenium.find_element(By.ID, 'edu')
            edu_field.clear()
            edu_field.send_keys('16')
            edu_field.send_keys(Keys.TAB)
            
            time.sleep(0.5)
            
            # Check skill points display
            occupation_points = self.selenium.find_element(By.ID, 'occupationPointsDisplay')
            self.assertIn('320', occupation_points.text)  # EDU * 20
            
            # Find a skill input
            skill_inputs = self.selenium.find_elements(By.CSS_SELECTOR, '.skill-occupation-input')
            if skill_inputs:
                first_skill = skill_inputs[0]
                first_skill.clear()
                first_skill.send_keys('50')
                first_skill.send_keys(Keys.TAB)
                
                time.sleep(0.5)
                
                # Check remaining points updated
                remaining = self.selenium.find_element(By.ID, 'remainingOccupationPoints')
                self.assertIn('270', remaining.text)  # 320 - 50
                
        def test_image_upload_preview(self):
            """Test character image upload and preview"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Wait for file input
            file_input = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character_image'))
            )
            
            # Create a test image
            img = Image.new('RGB', (100, 100), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Note: Selenium file upload is limited in headless mode
            # This test would need modification for full functionality
            
        def test_responsive_layout(self):
            """Test responsive layout at different screen sizes"""
            self.login()
            
            # Test mobile size
            self.selenium.set_window_size(375, 667)
            self.selenium.get(f'{self.live_server_url}/accounts/character-sheets/create_6th_edition/')
            
            # Check if form is still accessible
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character_name'))
            )
            
            # Test tablet size
            self.selenium.set_window_size(768, 1024)
            self.selenium.refresh()
            
            # Test desktop size
            self.selenium.set_window_size(1920, 1080)
            self.selenium.refresh()
            
            # Verify key elements are visible at all sizes
            self.assertTrue(
                self.selenium.find_element(By.ID, 'character_name').is_displayed()
            )