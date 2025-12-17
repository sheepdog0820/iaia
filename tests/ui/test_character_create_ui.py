"""
UI tests for Character Creation page (6th Edition)

Focuses on UI rendering, form structure, and a few interactive behaviors.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import json
import time
from unittest import skip

# Optional imports for Selenium tests
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from accounts.character_models import CharacterSheet

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
        """Page renders and shows key sections"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'クトゥルフ神話TRPG 6版探索者作成')
        self.assertContains(response, '基本情報')
        self.assertContains(response, '能力値')
        self.assertContains(response, '技能')

    def test_all_form_fields_present(self):
        """Required form fields exist"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertContains(response, 'id="character-name"')
        self.assertContains(response, 'id="player-name"')
        self.assertContains(response, 'id="age"')
        self.assertContains(response, 'id="gender"')
        self.assertContains(response, 'id="occupation"')

        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            self.assertContains(response, f'id="{ability}"')

        self.assertContains(response, 'id="hp"')
        self.assertContains(response, 'id="mp"')
        self.assertContains(response, 'id="san"')

    def test_javascript_assets_present(self):
        """JS bundle and form hook are included"""
        response = self.client.get('/accounts/character/create/6th/')
        self.assertContains(response, 'accounts/js/character6th.js')
        self.assertContains(response, 'id="character-sheet-form"')

    def test_form_submission_creates_character(self):
        """API POST creates a character"""
        data = {
            'edition': '6th',
            'name': 'Test Explorer',
            'player_name': 'Test Player',
            'age': 25,
            'gender': '男性',
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '大阪',
            'str_value': 10,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 13,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 17,
            'hit_points_current': 14,
            'magic_points_current': 14,
            'sanity_current': 70
        }

        response = self.client.post(
            '/api/accounts/character-sheets/',
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(CharacterSheet.objects.filter(name='Test Explorer').exists())


if SELENIUM_AVAILABLE:
    @skip("Selenium UI tests are disabled in this environment")
    class CharacterCreateSeleniumTest(StaticLiveServerTestCase):
        """Selenium-based smoke tests for character creation UI"""

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
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
            """Helper method to log in via dev-login shortcut"""
            self.selenium.get(f'{self.live_server_url}/accounts/dev-login/')
            login_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'form button.login-btn:not([disabled])'))
            )
            login_btn.click()
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/dev-login/')
            )

        def open_create_page(self):
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character-name'))
            )

        def test_roll_all_abilities_sets_values(self):
            """Clicking roll-all populates abilities"""
            self.open_create_page()
            roll_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'rollAllAbilities'))
            )
            roll_btn.click()
            time.sleep(0.5)

            abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            for ability in abilities:
                value = self.selenium.find_element(By.ID, ability).get_attribute('value')
                self.assertTrue(value.isdigit())

        def test_derived_stats_calculation(self):
            """Derived stats update from ability inputs"""
            self.open_create_page()
            con_field = self.selenium.find_element(By.ID, 'con')
            siz_field = self.selenium.find_element(By.ID, 'siz')
            pow_field = self.selenium.find_element(By.ID, 'pow')

            for field, val in [(con_field, '14'), (siz_field, '12'), (pow_field, '16')]:
                field.clear()
                field.send_keys(val)

            pow_field.send_keys(Keys.TAB)
            time.sleep(0.5)

            hp_value = self.selenium.find_element(By.ID, 'hp').get_attribute('value')
            mp_value = self.selenium.find_element(By.ID, 'mp').get_attribute('value')
            san_value = self.selenium.find_element(By.ID, 'san').get_attribute('value')

            self.assertEqual(hp_value, '13')   # (14+12)/2
            self.assertEqual(mp_value, '16')   # POW
            self.assertEqual(san_value, '80')  # POW*5

        def test_skill_tab_navigation(self):
            """Skill tabs switch properly"""
            self.open_create_page()
            knowledge_tab = self.selenium.find_element(By.ID, 'knowledge-tab')
            knowledge_tab.click()
            time.sleep(0.3)
            self.assertIn('active', knowledge_tab.get_attribute('class'))

            combat_tab = self.selenium.find_element(By.ID, 'combat-tab')
            combat_tab.click()
            time.sleep(0.3)
            self.assertIn('active', combat_tab.get_attribute('class'))
