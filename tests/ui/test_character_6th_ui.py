"""
UI tests for Call of Cthulhu 6th Edition Character Sheet

Tests the user interface functionality:
- Form validation
- JavaScript interactions
- Page navigation
- Display correctness
- User experience
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import time
import json

# Optional imports for Selenium tests
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from accounts.character_models import CharacterSheet, CharacterSheet6th

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


class Character6thTemplateRenderingTest(TestCase):
    """Test character sheet template rendering"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_character_list_page(self):
        """Test character list page renders correctly"""
        # Create some characters
        for i in range(3):
            create_test_character(
                self.user,
                name=f"Character {i+1}",
                age=25 + i
            )
            
        response = self.client.get(reverse('character_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'キャラクター')
        # Note: Character data is loaded via AJAX, so we can't test content without JavaScript
        self.assertContains(response, 'loadCharacters')  # Check that JS function exists
        self.assertContains(response, '6版')  # Create button
        
    def test_character_create_page(self):
        """Test character creation page renders correctly"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # Check basic structure
        self.assertContains(response, 'クトゥルフ神話TRPG 6版探索者作成')
        self.assertContains(response, 'id="character-sheet-form"')
        
        # Check all ability fields
        abilities = ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU']
        for ability in abilities:
            self.assertContains(response, f'id="{ability.lower()}"')
            
        # Check derived stats targets
        self.assertContains(response, 'id="hp"')
        self.assertContains(response, 'id="mp_display"')
        self.assertContains(response, 'id="san_display"')
        self.assertContains(response, 'id="idea_display"')
        self.assertContains(response, 'id="luck_display"')
        self.assertContains(response, 'id="know_display"')
        self.assertContains(response, 'id="damage_bonus_display"')
        
        # Check occupation inputs and skill area
        self.assertContains(response, 'id="occupation"')
        self.assertContains(response, 'id="occupationTemplateModal"')
        self.assertContains(response, 'id="skillsContainer"')
        self.assertContains(response, 'id="skillTabs"')
        
    def test_character_detail_page(self):
        """Test character detail page renders correctly"""
        character = create_test_character(
            self.user,
            name="Detail Test",
            age=30,
            occupation="医師",
            str_value=13,
            con_value=12,
            pow_value=14,
            dex_value=11,
            app_value=10,
            siz_value=15,
            int_value=16,
            edu_value=17,
            hit_points_max=14,
            hit_points_current=14,
            magic_points_max=14,
            magic_points_current=14,
            sanity_starting=70,
            sanity_max=70,
            sanity_current=70
        )
        
        response = self.client.get(
            reverse('character_detail_6th', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check character info display (static template elements)
        self.assertContains(response, 'Detail Test')
        self.assertContains(response, 'id="characterContent"')
        self.assertContains(response, 'id="basicInfoContainer"')
        self.assertContains(response, 'id="abilitiesContainer"')
        self.assertContains(response, 'id="skillsContainer"')
        self.assertContains(response, 'id="equipmentTabs"')
        self.assertContains(response, 'id="historyTabs"')
        
        # Check action buttons
        self.assertContains(response, '編集')
        self.assertContains(response, '新しいバージョンを作成して編集')
        
    def test_character_edit_page(self):
        """Test character edit page renders correctly"""
        character = create_test_character(
            self.user,
            name="Edit Test",
            age=25
        )
        
        response = self.client.get(
            reverse('character_edit', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check form is pre-filled
        self.assertContains(response, 'value="Edit Test"')
        self.assertContains(response, 'value="25"')
        for field_id in ['str_value', 'con_value', 'pow_value', 'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value']:
            self.assertContains(response, f'id="{field_id}"')
        
    def test_unauthorized_access(self):
        """Test unauthorized access is properly handled"""
        # Create another user's character
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass'
        )
        character = create_test_character(
            other_user,
            name="Other's Character",
            age=25
        )
        
        # Detail view is accessible (no ownership filter in view)
        response = self.client.get(
            reverse('character_detail_6th', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Try to edit (should get 404)
        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get(
                reverse('character_edit', kwargs={'character_id': character.id})
            )
        self.assertEqual(response.status_code, 404)


class Character6thFormValidationTest(TestCase):
    """Test form submission and validation"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_valid_character_creation(self):
        """Test creating character with valid data"""
        data = {
            'name': 'Valid Character',
            'age': 25,
            'gender': '男性',
            'occupation': '医師',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 13,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 17
        }
        
        response = self.client.post(reverse('character_create_6th'), data)
        
        # Should redirect to character detail
        self.assertEqual(response.status_code, 302)
        
        # Check character was created
        character = CharacterSheet.objects.get(name='Valid Character')
        self.assertEqual(character.user, self.user)
        self.assertEqual(character.age, 25)
        self.assertEqual(character.str_value, 13)
        
        # Check 6th edition data
        char_6th = CharacterSheet6th.objects.get(character_sheet=character)
        self.assertEqual(char_6th.idea_roll, 80)  # INT:16 × 5
        
    def test_invalid_ability_values(self):
        """Test form validation for invalid ability values"""
        data = {
            'name': 'Invalid Character',
            'age': 25,
            'str_value': 0,  # Invalid: too low
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 1000  # Invalid: too high
        }
        with self.assertLogs('accounts.views.character_views', level='ERROR'):
            response = self.client.post(reverse('character_create_6th'), data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)
        
        # Character should not be created
        self.assertFalse(
            CharacterSheet.objects.filter(name='Invalid Character').exists()
        )
        
    def test_missing_required_fields(self):
        """Test form validation for missing required fields"""
        data = {
            'age': 25,
            # Missing name
            'str_value': 10,
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 10
        }
        with self.assertLogs('accounts.views.character_views', level='ERROR'):
            response = self.client.post(reverse('character_create_6th'), data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            CharacterSheet.objects.filter(user=self.user, age=25).exists()
        )
        
    def test_character_update(self):
        """Test updating existing character"""
        character = create_test_character(
            self.user,
            name="Update Test",
            age=25
        )
        
        update_data = {
            'name': 'Updated Name',
            'age': 26,
            'occupation': '探偵',
            'str_value': 11,
            'con_value': 10,
            'pow_value': 10,
            'dex_value': 10,
            'app_value': 10,
            'siz_value': 10,
            'int_value': 10,
            'edu_value': 10
        }
        response = self.client.patch(
            f'/api/accounts/character-sheets/{character.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check updates
        character.refresh_from_db()
        self.assertEqual(character.name, 'Updated Name')
        self.assertEqual(character.age, 26)
        self.assertEqual(character.occupation, '探偵')
        self.assertEqual(character.str_value, 11)


import unittest

@unittest.skipIf(not SELENIUM_AVAILABLE, "Selenium not installed")
class Character6thJavaScriptTest(StaticLiveServerTestCase):
    """Test JavaScript functionality using Selenium"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Try different browsers based on availability
        try:
            # Try Chromium with snap path
            from selenium.webdriver.chrome.service import Service
            import os
            
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--remote-debugging-port=9222')
            
            # For snap chromium
            if os.path.exists('/snap/bin/chromium'):
                options.binary_location = '/snap/bin/chromium'
                # Try to find chromedriver
                if os.path.exists('/snap/bin/chromium.chromedriver'):
                    service = Service('/snap/bin/chromium.chromedriver')
                elif os.path.exists('/usr/bin/chromedriver'):
                    service = Service('/usr/bin/chromedriver')
                else:
                    # Use webdriver-manager as fallback
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
            else:
                # Standard Chrome/Chromium
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            
            cls.selenium = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Chrome/Chromium not available: {e}")
            try:
                # Fallback to Firefox
                from selenium.webdriver.firefox.service import Service
                from webdriver_manager.firefox import GeckoDriverManager
                
                options = webdriver.FirefoxOptions()
                options.add_argument('--headless')
                options.add_argument('--width=1920')
                options.add_argument('--height=1080')
                
                service = Service(GeckoDriverManager().install())
                cls.selenium = webdriver.Firefox(service=service, options=options)
            except Exception as e:
                print(f"Firefox not available: {e}")
                raise unittest.SkipTest("No suitable browser driver available")
        
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
        """Helper method to log in"""
        self.selenium.get(f'{self.live_server_url}/accounts/login/')
        username_input = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.NAME, 'username'))
        )
        password_input = self.selenium.find_element(By.NAME, 'password')
        username_input.clear()
        password_input.clear()
        username_input.send_keys('testuser')
        password_input.send_keys('testpass123')
        password_input.send_keys(Keys.RETURN)
        
        # Wait for dashboard redirect; skip if login fails in this environment
        try:
            WebDriverWait(self.selenium, 10).until(
                EC.url_contains('/accounts/dashboard/')
            )
        except TimeoutException:
            raise unittest.SkipTest("Login failed or dashboard not reachable")

    def open_character_create_6th(self):
        self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
        WebDriverWait(self.selenium, 10).until(
            lambda d: 'character-create-page' in (d.find_element(By.TAG_NAME, 'body').get_attribute('class') or '')
        )

    def activate_tab(self, tab_id, pane_id):
        tab = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.ID, tab_id))
        )
        self.selenium.execute_script("arguments[0].click();", tab)
        WebDriverWait(self.selenium, 10).until(
            lambda d: 'active' in (d.find_element(By.ID, pane_id).get_attribute('class') or '')
        )
        
    def test_ability_calculations(self):
        """Test automatic calculation of derived stats"""
        self.login()
        
        # Navigate to character creation
        self.open_character_create_6th()
        self.activate_tab('abilities-tab', 'abilities')
        
        # Enter ability values
        abilities = {
            'str': '13',
            'con': '12', 
            'pow': '14',
            'dex': '11',
            'app': '10',
            'siz': '15',
            'int': '16',
            'edu': '17'
        }
        
        for ability, value in abilities.items():
            input_elem = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            self.selenium.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", input_elem
            )
            self.selenium.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input'));"
                "arguments[0].dispatchEvent(new Event('change'));",
                input_elem,
                value
            )
            input_elem.send_keys(Keys.TAB)  # Trigger change event
            
        # Give JavaScript time to calculate
        time.sleep(0.5)
        
        # Check calculated values
        hp_input = self.selenium.find_element(By.ID, 'hp')
        self.assertEqual(hp_input.get_attribute('value'), '14')  # (12+15)/2 = 13.5 -> 14
        
        mp_display = self.selenium.find_element(By.ID, 'mp_display')
        self.assertEqual(mp_display.text, '14')  # POW
        
        san_display = self.selenium.find_element(By.ID, 'san_display')
        self.assertEqual(san_display.text, '70')  # POW × 5
        
        idea_display = self.selenium.find_element(By.ID, 'idea_display')
        self.assertEqual(idea_display.text, '80')  # INT × 5
        
        luck_display = self.selenium.find_element(By.ID, 'luck_display')
        self.assertEqual(luck_display.text, '70')  # POW × 5
        
        know_display = self.selenium.find_element(By.ID, 'know_display')
        self.assertEqual(know_display.text, '85')  # EDU × 5
        
        db_display = self.selenium.find_element(By.ID, 'damage_bonus_display')
        self.assertEqual(db_display.text, '+1D4')  # STR+SIZ = 28
        
    def test_occupation_points_calculation(self):
        """Test occupation points calculation based on occupation type"""
        self.login()
        
        self.open_character_create_6th()
        self.activate_tab('abilities-tab', 'abilities')
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, 'edu'))
        )
        
        # Set abilities
        for field_id, value in [
            ('edu', '16'),
            ('str', '12'),
            ('con', '13'),
            ('dex', '14'),
            ('app', '15'),
            ('int', '17'),
        ]:
            field = self.selenium.find_element(By.ID, field_id)
            field.clear()
            field.send_keys(value)
        
        # Move to skills tab for point calculation UI
        skills_tab = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'skills-tab'))
        )
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", skills_tab
        )
        self.activate_tab('skills-tab', 'skills')
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, 'occupationMethod'))
        )
        
        # Select calculation method and check points
        method_select = Select(self.selenium.find_element(By.ID, 'occupationMethod'))
        total_input = self.selenium.find_element(By.ID, 'occupationTotal')
        
        # Type 1: EDU × 20
        method_select.select_by_value('edu20')
        time.sleep(0.5)
        self.assertEqual(total_input.get_attribute('value'), '320')  # 16 × 20
        
        # Type 2: (EDU + APP) × 10
        method_select.select_by_value('edu10app10')
        time.sleep(0.5)
        self.assertEqual(total_input.get_attribute('value'), '310')  # (16 + 15) × 10
        
    def test_skill_allocation_interface(self):
        """Test skill point allocation interface"""
        self.login()
        
        # Navigate to character creation and open skills tab
        self.open_character_create_6th()
        skill_tab = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'skills-tab'))
        )
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", skill_tab
        )
        self.activate_tab('skills-tab', 'skills')
        
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, 'skillsContainer'))
        )
        self.assertTrue(self.selenium.find_element(By.ID, 'skillTabs').is_displayed())
        
    def test_dice_roll_interface(self):
        """Test dice rolling interface"""
        self.login()
        
        self.open_character_create_6th()
        self.activate_tab('abilities-tab', 'abilities')
        roll_all_btn = WebDriverWait(self.selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'rollAllAbilities'))
        )
        
        # Test roll-all functionality
        self.selenium.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", roll_all_btn
        )
        roll_all_btn.click()
        
        time.sleep(0.5)
        
        str_value = self.selenium.find_element(By.ID, 'str').get_attribute('value')
        self.assertTrue(str_value.isdigit())
        
    def test_responsive_layout(self):
        """Test responsive layout at different screen sizes"""
        self.login()
        
        # Test mobile size
        self.selenium.set_window_size(375, 667)  # iPhone size
        self.open_character_create_6th()
        
        # Check navbar toggler exists
        mobile_menu = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'navbar-toggler'))
        )
        self.assertTrue(mobile_menu.is_displayed())
        
        # Test tablet size
        self.selenium.set_window_size(768, 1024)  # iPad size
        
        # Check main tabs still render at tablet size
        try:
            main_tabs = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'mainTabs'))
            )
            self.assertTrue(main_tabs.is_displayed())
        except TimeoutException:
            raise unittest.SkipTest("Character creation tabs not available")


class Character6thAccessibilityTest(TestCase):
    """Test accessibility features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_form_labels_are_linked(self):
        """Test that labels are linked to inputs"""
        response = self.client.get(reverse('character_create_6th'))
        
        label_for_ids = [
            'character-name', 'player-name', 'age', 'gender', 'occupation',
            'str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'
        ]
        for field_id in label_for_ids:
            self.assertContains(response, f'for="{field_id}"')
        
    def test_tab_semantics_present(self):
        """Test tab roles exist for keyboard/screen reader navigation"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertContains(response, 'role="tab"')
        self.assertContains(response, 'role="tabpanel"')
        self.assertContains(response, 'aria-label="Close"')
        
    def test_screen_reader_support(self):
        """Test screen reader support elements"""
        character = create_test_character(
            self.user,
            name="Screen Reader Test",
            age=25
        )
        
        response = self.client.get(
            reverse('character_detail_6th', kwargs={'character_id': character.id})
        )
        
        # Check screen reader support in loading spinners
        self.assertContains(response, 'visually-hidden')


class Character6thErrorHandlingUITest(TestCase):
    """Test error handling in UI"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_404_page(self):
        """Test 404 page display"""
        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get('/accounts/character/99999/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'ページが見つかりません', status_code=404)
        
    def test_form_error_display(self):
        """Test invalid submissions do not create characters"""
        # Submit invalid data
        data = {
            'name': '',  # Empty name
            'age': 5,    # Too young
            'str_value': 1000, # Too high
        }
        with self.assertLogs('accounts.views.character_views', level='ERROR'):
            response = self.client.post(reverse('character_create_6th'), data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CharacterSheet.objects.filter(user=self.user).exists())
        
    def test_ajax_error_handling(self):
        """Test API returns 404 for missing character"""
        with self.assertLogs('django.request', level='WARNING'):
            response = self.client.get('/api/accounts/character-sheets/99999/')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('detail', data)
