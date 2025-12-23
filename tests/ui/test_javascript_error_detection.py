"""
JavaScript Error Detection Tests for Character Creation

Tests that detect JavaScript errors in the browser console during UI interactions.
This helps catch runtime errors that might not be visible during normal testing.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import time
import unittest

# Optional imports for Selenium tests
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

User = get_user_model()


if SELENIUM_AVAILABLE:
    class JavaScriptErrorDetectionTest(StaticLiveServerTestCase):
        """Test suite for detecting JavaScript errors in character creation"""
        
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            
            # Chrome options for headless testing with console log capture
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            # Enable logging
            options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
            
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
            # Use dev login for testing
            self.selenium.get(f'{self.live_server_url}/accounts/dev-login/')
            
            try:
                login_btn = WebDriverWait(self.selenium, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'form button.login-btn:not([disabled])'))
                )
                login_btn.click()
            except TimeoutException:
                raise unittest.SkipTest("Dev login not available for Selenium tests")
                
            # Wait for redirect or character list page
            try:
                WebDriverWait(self.selenium, 5).until(
                    EC.url_contains('/accounts/')
                )
            except TimeoutException:
                pass
            
        def get_browser_errors(self):
            """Extract JavaScript errors from browser console"""
            errors = []
            for entry in self.selenium.get_log('browser'):
                if entry['level'] == 'SEVERE':
                    # Filter out expected warnings
                    if 'favicon.ico' not in entry['message'] and \
                       'Failed to load resource' not in entry['message']:
                        errors.append(entry)
            return errors
            
        def test_page_load_no_errors(self):
            """Test that character creation page loads without JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for page to fully load
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character-name'))
            )
            
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found on page load: {errors}")
            
        def test_ability_score_changes_no_errors(self):
            """Test that changing ability scores doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for page to load
            dex_field = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'dex'))
            )
            
            # Change various ability scores
            ability_fields = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            for ability in ability_fields:
                field = self.selenium.find_element(By.ID, ability)
                field.clear()
                field.send_keys('15')
                field.send_keys(Keys.TAB)
                time.sleep(0.1)
                
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found when changing abilities: {errors}")
            
        def test_dice_rolling_no_errors(self):
            """Test that dice rolling doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait and click roll all button
            roll_all_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'rollAllAbilities'))
            )
            roll_all_btn.click()
            
            time.sleep(1)
            
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during dice rolling: {errors}")
            
        def test_skill_allocation_no_errors(self):
            """Test that skill point allocation doesn't cause JavaScript errors"""
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
            
            # Open skills tab and allocate points to any occupation skill
            self.selenium.find_element(By.ID, 'skills-tab').click()
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#combatSkills .occupation-skill'))
            )
            skill_inputs = self.selenium.find_elements(By.CSS_SELECTOR, '.occupation-skill')
            if skill_inputs:
                skill_inputs[0].clear()
                skill_inputs[0].send_keys('50')
                skill_inputs[0].send_keys(Keys.TAB)
                    
            time.sleep(0.5)
            
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during skill allocation: {errors}")
            
        def test_custom_base_value_editing_no_errors(self):
            """Test that editing custom base values doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for skills to load
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'combatSkills'))
            )
            
            # Try to edit a base value
            base_inputs = self.selenium.find_elements(By.CSS_SELECTOR, '[id^="base_"]')
            if base_inputs:
                base_inputs[0].clear()
                base_inputs[0].send_keys('10')
                base_inputs[0].send_keys(Keys.TAB)
                    
            time.sleep(0.5)
            
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during base value editing: {errors}")
            
        def test_form_submission_no_errors(self):
            """Test that form submission doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Fill minimum required fields
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'character-name'))
            )
            
            self.selenium.find_element(By.ID, 'character-name').send_keys('Error Test Character')
            
            # Roll abilities
            roll_btn = self.selenium.find_element(By.ID, 'rollAllAbilities')
            roll_btn.click()
            
            time.sleep(1)
            
            # Try to submit (will be blocked by validation)
            submit_btn = self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_btn.click()
            
            # Accept any alert
            try:
                alert = WebDriverWait(self.selenium, 3).until(EC.alert_is_present())
                alert.accept()
            except TimeoutException:
                pass
                
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during form submission: {errors}")
            
        def test_tab_navigation_no_errors(self):
            """Test that navigating between skill tabs doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Wait for skills section
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'skillTabs'))
            )
            
            # Click through all tabs
            tab_ids = ['combat-tab', 'exploration-tab', 'action-tab', 'social-tab',
                       'knowledge-tab', 'all-tab', 'allocated-tab']
            
            for tab_id in tab_ids:
                tab = self.selenium.find_element(By.ID, tab_id)
                tab.click()
                time.sleep(0.2)
                    
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during tab navigation: {errors}")
            
        def test_occupation_template_selection_no_errors(self):
            """Test that occupation template selection doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')
            
            # Open and close occupation template modal
            open_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'occupationTemplateBtn'))
            )
            open_btn.click()
            
            WebDriverWait(self.selenium, 10).until(
                EC.visibility_of_element_located((By.ID, 'occupationTemplateModal'))
            )
            close_btn = self.selenium.find_element(By.CSS_SELECTOR, '#occupationTemplateModal .btn-close')
            close_btn.click()
            
            time.sleep(0.5)
                    
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during template selection: {errors}")
