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
            'edition': '6th',
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
            'hit_points_current': 14,
            'magic_points_current': 16,
            'sanity_current': 80,
            'skills': [
                {
                    'skill_name': 'archaeology',
                    'base_value': 1,
                    'occupation_points': 50,
                    'interest_points': 10,
                    'other_points': 0,
                },
                {
                    'skill_name': 'library_use',
                    'base_value': 25,
                    'occupation_points': 30,
                    'interest_points': 15,
                    'other_points': 0,
                },
                {
                    'skill_name': 'spot_hidden',
                    'base_value': 25,
                    'occupation_points': 20,
                    'interest_points': 0,
                    'other_points': 0,
                },
                {
                    'skill_name': 'dodge',
                    'base_value': 30,  # DEX×2 = 15×2 = 30
                    'occupation_points': 0,
                    'interest_points': 20,
                    'other_points': 0,
                },
                {
                    'skill_name': 'own_language',
                    'base_value': 90,  # EDU×5 = 18×5 = 90
                    'occupation_points': 0,
                    'interest_points': 0,
                    'other_points': 0,
                },
            ],
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
        skills = CharacterSkill.objects.filter(character_sheet=character)
        self.assertTrue(skills.exists())
        
        # Verify dodge skill calculation
        dodge_skill = skills.filter(skill_name='dodge').first()
        if dodge_skill:
            self.assertEqual(dodge_skill.base_value, 30)  # DEX×2
            
        # Verify own language skill
        language_skill = skills.filter(skill_name='own_language').first()
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
            client = Client()
            logged_in = client.login(username=self.user.username, password='testpass123')
            if not logged_in:
                raise AssertionError('Failed to authenticate test user')

            self.selenium.get(self.live_server_url)
            self.selenium.delete_all_cookies()
            session_cookie = client.cookies.get('sessionid')
            if not session_cookie:
                raise AssertionError('Session cookie not set')

            self.selenium.add_cookie({
                'name': 'sessionid',
                'value': session_cookie.value,
                'path': '/',
            })
            self.selenium.get(f'{self.live_server_url}/accounts/dashboard/')

            # Fallback: perform a UI login if session-cookie auth isn't recognized.
            if '/accounts/login/' in (self.selenium.current_url or ''):
                self.selenium.get(f'{self.live_server_url}/accounts/login/')
                username_input = WebDriverWait(self.selenium, 20).until(
                    EC.element_to_be_clickable((By.NAME, 'username'))
                )
                password_input = WebDriverWait(self.selenium, 20).until(
                    EC.element_to_be_clickable((By.NAME, 'password'))
                )
                username_input.clear()
                username_input.send_keys(self.user.username)
                password_input.clear()
                password_input.send_keys('testpass123')
                password_input.send_keys(Keys.RETURN)
                WebDriverWait(self.selenium, 20).until(
                    EC.url_contains('/accounts/dashboard/')
                )

        def open_main_tab(self, pane_id: str):
            """Open a main (top-level) tab in the character create UI."""
            tab = WebDriverWait(self.selenium, 20).until(
                EC.presence_of_element_located((By.ID, f'{pane_id}-tab'))
            )
            self.selenium.execute_script('arguments[0].click();', tab)
            WebDriverWait(self.selenium, 20).until(
                EC.visibility_of_element_located((By.ID, pane_id))
            )

        def open_skill_tab(self, pane_id: str):
            """Open a skill sub-tab (combat/exploration/.../all/recommended/allocated)."""
            tab = WebDriverWait(self.selenium, 20).until(
                EC.presence_of_element_located((By.ID, f'{pane_id}-tab'))
            )
            self.selenium.execute_script('arguments[0].click();', tab)
            WebDriverWait(self.selenium, 20).until(
                EC.visibility_of_element_located((By.ID, pane_id))
            )

        def test_dex_to_dodge_skill_synchronization(self):
            """Test that changing DEX updates dodge skill base value"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('abilities')
            dex_field = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'dex'))
            )

            # Set initial DEX value
            dex_field.clear()
            dex_field.send_keys('10')
            dex_field.send_keys(Keys.TAB)

            # Find dodge skill base value
            dodge_base = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'base_dodge'))
            )
            WebDriverWait(self.selenium, 10).until(
                lambda _driver: dodge_base.get_attribute('value') == '20'
            )

            # Change DEX value
            dex_field.clear()
            dex_field.send_keys('18')
            dex_field.send_keys(Keys.TAB)

            # Check dodge skill updated
            WebDriverWait(self.selenium, 10).until(
                lambda _driver: dodge_base.get_attribute('value') == '36'
            )

        def test_custom_skill_base_values(self):
            """Test editing custom base values for skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('skills')
            self.open_skill_tab('all')

            # Find archaeology skill base value
            archaeology_base = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'base_archaeology'))
            )
            original_value = archaeology_base.get_attribute('value')

            # Edit base value
            archaeology_base.clear()
            archaeology_base.send_keys('10')
            archaeology_base.send_keys(Keys.TAB)

            # Verify custom class applied
            WebDriverWait(self.selenium, 10).until(
                lambda _driver: 'customized' in archaeology_base.get_attribute('class')
            )

            # Right-click to reset
            self.selenium.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true, view: window, button: 2}));",
                archaeology_base,
            )

            # Check value reset
            WebDriverWait(self.selenium, 10).until(
                lambda _driver: archaeology_base.get_attribute('value') == original_value
            )
            self.assertNotIn('customized', archaeology_base.get_attribute('class'))

        def test_occupation_template_with_skills(self):
            """Test applying occupation template and allocating skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('abilities')
            edu_field = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'edu'))
            )
            edu_field.clear()
            edu_field.send_keys('16')
            edu_field.send_keys(Keys.TAB)

            self.open_main_tab('basic-info')
            template_button = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'occupationTemplateBtn'))
            )
            template_button.click()

            archaeologist_item = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[contains(@class,'occupation-template-item')][.//h6[normalize-space()='考古学者']]",
                ))
            )
            archaeologist_item.click()

            # Check occupation points
            self.open_main_tab('skills')
            occupation_total = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'occupationTotal'))
            )
            WebDriverWait(self.selenium, 10).until(
                lambda _driver: occupation_total.get_attribute('value') == '320'
            )

            # Allocate points to archaeology
            self.open_skill_tab('all')
            archaeology_occ = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'occ_archaeology'))
            )
            archaeology_occ.clear()
            archaeology_occ.send_keys('60')
            archaeology_occ.send_keys(Keys.TAB)

            # Check remaining points
            remaining = self.selenium.find_element(By.ID, 'occupationRemaining')
            WebDriverWait(self.selenium, 10).until(lambda _driver: remaining.text.strip() == '260')

        def test_multiple_skill_allocation(self):
            """Test allocating points to multiple skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('abilities')
            edu_field = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'edu'))
            )
            int_field = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'int'))
            )
            edu_field.clear()
            edu_field.send_keys('15')
            int_field.clear()
            int_field.send_keys('14')
            int_field.send_keys(Keys.TAB)

            # Allocate occupation points to multiple skills
            skills_to_allocate = [
                ('archaeology', 40),
                ('library_use', 30),
                ('spot_hidden', 25),
                ('history', 35),
                ('navigate', 20),
            ]

            self.open_main_tab('skills')
            self.open_skill_tab('all')
            for skill_id, points in skills_to_allocate:
                skill_input = self.selenium.find_element(
                    By.ID,
                    f'occ_{skill_id}'
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
                    By.ID,
                    f'int_{skill_id}'
                )
                skill_input.clear()
                skill_input.send_keys(str(points))
                skill_input.send_keys(Keys.TAB)
                time.sleep(0.2)

            occupation_remaining = self.selenium.find_element(By.ID, 'occupationRemaining')
            interest_remaining = self.selenium.find_element(By.ID, 'interestRemaining')
            WebDriverWait(self.selenium, 10).until(lambda _driver: occupation_remaining.text.strip() == '150')
            WebDriverWait(self.selenium, 10).until(lambda _driver: interest_remaining.text.strip() == '95')

        def test_allocated_skills_tab(self):
            """Test that allocated skills appear in the allocated tab"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('skills')
            self.open_skill_tab('all')

            # Allocate points to a skill
            archaeology_occ = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'occ_archaeology'))
            )
            archaeology_occ.clear()
            archaeology_occ.send_keys('50')
            archaeology_occ.send_keys(Keys.TAB)

            time.sleep(0.5)

            # Switch to allocated skills tab
            self.open_skill_tab('allocated')

            # Check that archaeology is visible
            allocated_names = [
                el.text.strip()
                for el in self.selenium.find_elements(By.CSS_SELECTOR, '#allocatedSkills .fw-bold')
            ]
            self.assertIn('考古学', allocated_names)

        def test_complete_character_creation_flow(self):
            """Test complete character creation with multiple skills"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            # Fill basic info (default tab)
            WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'character-name'))
            )

            self.selenium.find_element(By.ID, 'character-name').send_keys('完全なる探索者')
            self.selenium.find_element(By.ID, 'player-name').send_keys('テストプレイヤー')
            self.selenium.find_element(By.ID, 'age').send_keys('35')
            Select(self.selenium.find_element(By.ID, 'gender')).select_by_value('男性')
            self.selenium.find_element(By.ID, 'occupation').send_keys('私立探偵')

            # Set ability scores (required)
            self.open_main_tab('abilities')
            for ability_id, value in {
                'str': 10,
                'con': 10,
                'pow': 10,
                'dex': 10,
                'app': 10,
                'siz': 10,
                'int': 14,
                'edu': 16,
            }.items():
                field = WebDriverWait(self.selenium, 10).until(
                    EC.element_to_be_clickable((By.ID, ability_id))
                )
                field.clear()
                field.send_keys(str(value))

            # Allocate some skills
            self.open_main_tab('skills')
            self.open_skill_tab('all')
            skills = [
                ('spot_hidden', 40),
                ('psychology', 30),
                ('library_use', 20)
            ]

            for skill_id, points in skills:
                skill_input = self.selenium.find_element(
                    By.ID,
                    f'occ_{skill_id}'
                )
                skill_input.clear()
                skill_input.send_keys(str(points))
                skill_input.send_keys(Keys.TAB)
                time.sleep(0.2)

            # Submit form (AJAX) and accept the success alert
            self.selenium.execute_script("document.getElementById('character-sheet-form').requestSubmit();")
            WebDriverWait(self.selenium, 10).until(EC.alert_is_present())
            self.selenium.switch_to.alert.accept()

            # Wait for redirect
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/character/list/')
            )

            # Verify character was created
            self.assertTrue(
                CharacterSheet.objects.filter(name='完全なる探索者').exists()
            )

            # Verify skills were saved
            character = CharacterSheet.objects.get(name='完全なる探索者')
            saved_skills = CharacterSkill.objects.filter(character_sheet=character)
            self.assertGreater(saved_skills.count(), 0)

            # Check specific skills
            spot_hidden = saved_skills.filter(skill_name='目星').first()
            if spot_hidden:
                self.assertEqual(spot_hidden.occupation_points, 40)
