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
        self.assertContains(response, 'キャラクター作成（6版）')
        self.assertContains(response, '<form', count=1)
        
        # Check all ability fields
        abilities = ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU']
        for ability in abilities:
            self.assertContains(response, f'id="{ability.lower()}"')
            
        # Check derived stats display
        self.assertContains(response, 'id="hp_display"')
        self.assertContains(response, 'id="mp_display"')
        self.assertContains(response, 'id="san_display"')
        self.assertContains(response, 'id="idea_display"')
        self.assertContains(response, 'id="luck_display"')
        self.assertContains(response, 'id="know_display"')
        
        # Check occupation dropdown
        self.assertContains(response, '<select name="occupation"')
        self.assertContains(response, '医師')
        self.assertContains(response, '私立探偵')
        
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
        
        # Add some skills
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="医学",
            base_value=5,
            occupation_points=70
        )
        
        response = self.client.get(
            reverse('character_detail', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check character info display
        self.assertContains(response, 'Detail Test')
        self.assertContains(response, '30歳')
        self.assertContains(response, '医師')
        
        # Check ability values
        self.assertContains(response, 'STR: 13')
        self.assertContains(response, 'HP: 14')  # (12+15)/2 = 13.5 -> 14
        
        # Check skills display
        self.assertContains(response, '医学')
        self.assertContains(response, '75')  # 5 + 70
        
        # Check action buttons
        self.assertContains(response, '編集')
        self.assertContains(response, 'バージョン作成')
        self.assertContains(response, 'CCFOLIA出力')
        
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
        self.assertContains(response, 'value="10"', count=8)  # All abilities
        
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
        
        # Try to access (should get 404)
        response = self.client.get(
            reverse('character_detail', kwargs={'character_id': character.id})
        )
        self.assertEqual(response.status_code, 404)
        
        # Try to edit (should get 404)
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
            'gender': 'male',
            'occupation': '医師',
            'birthplace': '東京',
            'residence': '横浜',
            'str': 13,
            'con': 12,
            'pow': 14,
            'dex': 11,
            'app': 10,
            'siz': 15,
            'int': 16,
            'edu': 17
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
            'str': 0,  # Invalid: too low
            'con': 10,
            'pow': 10,
            'dex': 10,
            'app': 10,
            'siz': 10,
            'int': 10,
            'edu': 1000  # Invalid: too high
        }
        
        response = self.client.post(reverse('character_create_6th'), data)
        
        # Should not redirect (form has errors)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')
        
        # Character should not be created
        self.assertFalse(
            CharacterSheet.objects.filter(name='Invalid Character').exists()
        )
        
    def test_missing_required_fields(self):
        """Test form validation for missing required fields"""
        data = {
            'age': 25,
            # Missing name
            'str': 10,
            'con': 10,
            'pow': 10,
            'dex': 10,
            'app': 10,
            'siz': 10,
            'int': 10,
            'edu': 10
        }
        
        response = self.client.post(reverse('character_create_6th'), data)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'このフィールドは必須です')
        
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
            'str': 11,
            'con': 10,
            'pow': 10,
            'dex': 10,
            'app': 10,
            'siz': 10,
            'int': 10,
            'edu': 10
        }
        
        response = self.client.post(
            reverse('character_edit', kwargs={'character_id': character.id}),
            update_data
        )
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
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
        username_input = self.selenium.find_element(By.NAME, 'username')
        password_input = self.selenium.find_element(By.NAME, 'password')
        username_input.send_keys('testuser')
        password_input.send_keys('testpass123')
        password_input.send_keys(Keys.RETURN)
        
        # Wait for redirect
        WebDriverWait(self.selenium, 10).until(
            EC.url_changes(f'{self.live_server_url}/accounts/login/')
        )
        
    def test_ability_calculations(self):
        """Test automatic calculation of derived stats"""
        self.login()
        
        # Navigate to character creation
        self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
        
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
            input_elem = self.selenium.find_element(By.ID, ability)
            input_elem.clear()
            input_elem.send_keys(value)
            input_elem.send_keys(Keys.TAB)  # Trigger change event
            
        # Give JavaScript time to calculate
        time.sleep(0.5)
        
        # Check calculated values
        hp_display = self.selenium.find_element(By.ID, 'hp_display')
        self.assertEqual(hp_display.text, '14')  # (12+15)/2 = 13.5 -> 14
        
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
        
        self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
        
        # Set abilities
        self.selenium.find_element(By.ID, 'edu').send_keys('16')
        self.selenium.find_element(By.ID, 'str').send_keys('12')
        self.selenium.find_element(By.ID, 'con').send_keys('13')
        self.selenium.find_element(By.ID, 'dex').send_keys('14')
        self.selenium.find_element(By.ID, 'app').send_keys('15')
        self.selenium.find_element(By.ID, 'int').send_keys('17')
        
        # Select occupation and check points
        occupation_select = Select(self.selenium.find_element(By.NAME, 'occupation'))
        
        # Type 1: EDU × 20
        occupation_select.select_by_visible_text('医師')
        time.sleep(0.5)
        points_display = self.selenium.find_element(By.ID, 'occupation_points_display')
        self.assertEqual(points_display.text, '320')  # 16 × 20
        
        # Type 2: (EDU + APP) × 10  
        occupation_select.select_by_visible_text('エンターテイナー')
        time.sleep(0.5)
        self.assertEqual(points_display.text, '310')  # (16 + 15) × 10
        
        # Type 5: (EDU or DEX) × 20
        occupation_select.select_by_visible_text('スポーツ選手')
        time.sleep(0.5)
        self.assertEqual(points_display.text, '320')  # max(16, 14) × 20
        
    def test_skill_allocation_interface(self):
        """Test skill point allocation interface"""
        # Create character first
        character = create_test_character(
            self.user,
            name="Skill Test",
            age=25,
            edu_value=16,
            occupation="医師"
        )
        
        self.login()
        
        # Navigate to character detail
        self.selenium.get(
            f'{self.live_server_url}/accounts/character/{character.id}/'
        )
        
        # Click skill allocation button
        skill_btn = self.selenium.find_element(By.ID, 'allocate_skills_btn')
        skill_btn.click()
        
        # Wait for modal/section to appear
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, 'skill_allocation_section'))
        )
        
        # Check available points display
        occ_points = self.selenium.find_element(By.ID, 'occupation_points_available')
        self.assertEqual(occ_points.text, '320')  # EDU:16 × 20
        
        hobby_points = self.selenium.find_element(By.ID, 'hobby_points_available')
        self.assertEqual(hobby_points.text, '100')  # INT:10 × 10
        
        # Allocate points to a skill
        skill_select = Select(self.selenium.find_element(By.ID, 'skill_name'))
        skill_select.select_by_visible_text('医学')
        
        occ_input = self.selenium.find_element(By.ID, 'occupation_points_input')
        occ_input.send_keys('70')
        
        # Submit allocation
        submit_btn = self.selenium.find_element(By.ID, 'allocate_skill_btn')
        submit_btn.click()
        
        # Wait for update
        time.sleep(1)
        
        # Check points were deducted
        updated_occ_points = self.selenium.find_element(By.ID, 'occupation_points_available')
        self.assertEqual(updated_occ_points.text, '250')  # 320 - 70
        
    def test_dice_roll_interface(self):
        """Test dice rolling interface"""
        character = create_test_character(
            self.user,
            name="Dice Test",
            age=25,
            str_value=13
        )
        
        # Add a skill
        CharacterSkill.objects.create(
            character_sheet=character,
            skill_name="医学",
            base_value=5,
            occupation_points=70
        )
        
        self.login()
        
        self.selenium.get(
            f'{self.live_server_url}/accounts/character/{character.id}/'
        )
        
        # Test ability roll
        str_roll_btn = self.selenium.find_element(By.ID, 'roll_str_btn')
        str_roll_btn.click()
        
        time.sleep(0.5)
        
        # Check roll result appears
        roll_result = self.selenium.find_element(By.ID, 'roll_result')
        self.assertIn('STR', roll_result.text)
        self.assertIn('1D100', roll_result.text)
        
        # Test skill roll
        skill_roll_btn = self.selenium.find_element(By.CSS_SELECTOR, '[data-skill="医学"]')
        skill_roll_btn.click()
        
        time.sleep(0.5)
        
        # Check skill roll result
        self.assertIn('医学', roll_result.text)
        self.assertIn('75', roll_result.text)  # Skill value
        
    def test_responsive_layout(self):
        """Test responsive layout at different screen sizes"""
        self.login()
        
        # Test mobile size
        self.selenium.set_window_size(375, 667)  # iPhone size
        self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
        
        # Check mobile menu is visible
        mobile_menu = self.selenium.find_element(By.CLASS_NAME, 'mobile-menu-toggle')
        self.assertTrue(mobile_menu.is_displayed())
        
        # Test tablet size
        self.selenium.set_window_size(768, 1024)  # iPad size
        
        # Check layout adjustments
        form_container = self.selenium.find_element(By.CLASS_NAME, 'character-form')
        self.assertIn('tablet-layout', form_container.get_attribute('class'))
        
        # Test desktop size
        self.selenium.set_window_size(1920, 1080)
        
        # Check full layout
        sidebar = self.selenium.find_element(By.CLASS_NAME, 'character-sidebar')
        self.assertTrue(sidebar.is_displayed())


class Character6thAccessibilityTest(TestCase):
    """Test accessibility features"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_aria_labels(self):
        """Test ARIA labels are present"""
        response = self.client.get(reverse('character_create_6th'))
        
        # Check form has proper ARIA labels
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'aria-describedby')
        self.assertContains(response, 'role="form"')
        
        # Check important elements have labels
        self.assertContains(response, 'aria-label="キャラクター名"')
        self.assertContains(response, 'aria-label="STR値"')
        
    def test_keyboard_navigation(self):
        """Test keyboard navigation support"""
        response = self.client.get(reverse('character_create_6th'))
        
        # Check tabindex attributes
        self.assertContains(response, 'tabindex')
        
        # Check focus indicators in CSS
        self.assertContains(response, 'focus:outline')
        
    def test_color_contrast(self):
        """Test color contrast meets WCAG standards"""
        response = self.client.get(reverse('character_create_6th'))
        
        # Check CSS includes high contrast colors
        self.assertContains(response, 'color-contrast-high')
        
    def test_screen_reader_support(self):
        """Test screen reader support elements"""
        character = create_test_character(
            self.user,
            name="Screen Reader Test",
            age=25
        )
        
        response = self.client.get(
            reverse('character_detail', kwargs={'character_id': character.id})
        )
        
        # Check screen reader only text
        self.assertContains(response, 'sr-only')
        self.assertContains(response, 'aria-live')
        
        # Check table headers
        self.assertContains(response, 'scope="col"')
        self.assertContains(response, 'scope="row"')


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
        response = self.client.get('/accounts/character/99999/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'ページが見つかりません', status_code=404)
        
    def test_form_error_display(self):
        """Test form errors are displayed properly"""
        # Submit invalid data
        data = {
            'name': '',  # Empty name
            'age': 5,    # Too young
            'str': 1000, # Too high
        }
        
        response = self.client.post(reverse('character_create_6th'), data)
        
        # Check error messages
        self.assertContains(response, 'alert-danger')
        self.assertContains(response, 'このフィールドは必須です')
        self.assertContains(response, '10以上200以下の値を入力してください')
        self.assertContains(response, '1以上999以下の値を入力してください')
        
    def test_ajax_error_handling(self):
        """Test AJAX error handling"""
        # Make invalid AJAX request
        response = self.client.post(
            '/api/characters/99999/allocate_skill_points/',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)


