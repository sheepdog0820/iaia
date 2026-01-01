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

        def open_main_tab(self, tab_id, pane_id):
            tab = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, tab_id))
            )
            self.selenium.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", tab
            )
            self.selenium.execute_script(
                """
                const tab = arguments[0];
                const paneId = arguments[1];
                if (window.bootstrap && bootstrap.Tab) {
                    bootstrap.Tab.getOrCreateInstance(tab).show();
                } else {
                    tab.classList.add('active');
                    tab.setAttribute('aria-selected', 'true');
                    const pane = document.getElementById(paneId);
                    if (pane) {
                        pane.classList.add('show', 'active');
                        pane.style.display = 'block';
                        pane.style.opacity = '1';
                        pane.style.visibility = 'visible';
                    }
                }
                """,
                tab,
                pane_id,
            )
            try:
                WebDriverWait(self.selenium, 10).until(
                    EC.visibility_of_element_located((By.ID, pane_id))
                )
            except TimeoutException:
                pass
            
        def login(self):
            """Helper method to log in via Selenium"""
            client = Client()
            logged_in = client.login(
                username=self.user.username,
                password='testpass123'
            )
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
            self.selenium.get(f'{self.live_server_url}/')
            
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

            self.open_main_tab('abilities-tab', 'abilities')
            WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, 'dex'))
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
            self.open_main_tab('abilities-tab', 'abilities')
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
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'edu'))
            )
            self.selenium.execute_script(
                """
                const edu = document.getElementById('edu');
                if (edu) {
                    edu.value = '16';
                    edu.dispatchEvent(new Event('input', { bubbles: true }));
                    edu.dispatchEvent(new Event('change', { bubbles: true }));
                }
                """
            )
            
            time.sleep(0.5)
            
            # Open skills tab and allocate points to any occupation skill
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.occupation-skill'))
            )
            self.selenium.execute_script(
                """
                const skillInputs = Array.from(document.querySelectorAll('.occupation-skill'));
                const target = skillInputs.find((el) => el.offsetParent !== null) || skillInputs[0];
                if (target) {
                    target.value = '50';
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                    target.dispatchEvent(new Event('change', { bubbles: true }));
                    target.dispatchEvent(new Event('blur', { bubbles: true }));
                }
                """
            )
                    
            time.sleep(0.5)
            
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during skill allocation: {errors}")
            
        def test_custom_base_value_editing_no_errors(self):
            """Test that editing custom base values doesn't cause JavaScript errors"""
            self.login()
            self.selenium.get(f'{self.live_server_url}/accounts/character/create/6th/')

            self.open_main_tab('skills-tab', 'skills')
            WebDriverWait(self.selenium, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '[id^="base_"]'))
            )
            
            # Try to edit a base value
            base_inputs = self.selenium.find_elements(By.CSS_SELECTOR, '[id^="base_"]')
            visible_base_inputs = [base_input for base_input in base_inputs if base_input.is_displayed()]
            if visible_base_inputs:
                visible_base_inputs[0].clear()
                visible_base_inputs[0].send_keys('10')
                visible_base_inputs[0].send_keys(Keys.TAB)
                    
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
            self.open_main_tab('abilities-tab', 'abilities')
            roll_btn = self.selenium.find_element(By.ID, 'rollAllAbilities')
            roll_btn.click()
            
            time.sleep(1)
            
            # Try to submit (will be blocked by validation)
            submit_btn = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
            )
            self.selenium.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", submit_btn
            )
            self.selenium.execute_script("arguments[0].click();", submit_btn)
            
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
            self.open_main_tab('skills-tab', 'skills')
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'skillTabs'))
            )
            
            # Click through all tabs
            tab_ids = ['combat-tab', 'exploration-tab', 'action-tab', 'social-tab',
                       'knowledge-tab', 'all-tab', 'recommended-tab', 'allocated-tab']
            
            for tab_id in tab_ids:
                self.selenium.execute_script(
                    """
                    const tabId = arguments[0];
                    const tab = document.getElementById(tabId);
                    if (!tab) {
                        return;
                    }
                    if (window.bootstrap && bootstrap.Tab) {
                        bootstrap.Tab.getOrCreateInstance(tab).show();
                    } else {
                        tab.classList.add('active');
                        tab.setAttribute('aria-selected', 'true');
                        const target = tab.getAttribute('data-bs-target');
                        if (target) {
                            const pane = document.querySelector(target);
                            if (pane) {
                                pane.classList.add('show', 'active');
                                pane.style.display = 'block';
                                pane.style.opacity = '1';
                                pane.style.visibility = 'visible';
                            }
                        }
                    }
                    """,
                    tab_id,
                )
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
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.ID, 'occupationTemplateBtn'))
            )
            self.selenium.execute_script(
                """
                const modalEl = document.getElementById('occupationTemplateModal');
                if (!modalEl) {
                    return;
                }
                if (window.bootstrap && bootstrap.Modal) {
                    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                    modal.show();
                    modal.hide();
                } else {
                    modalEl.classList.add('show');
                    modalEl.style.display = 'block';
                    modalEl.style.visibility = 'visible';
                    modalEl.style.opacity = '1';
                    modalEl.removeAttribute('aria-hidden');
                    modalEl.classList.remove('show');
                    modalEl.style.display = 'none';
                    modalEl.setAttribute('aria-hidden', 'true');
                }
                """
            )
            
            time.sleep(0.5)
                    
            # Check for JavaScript errors
            errors = self.get_browser_errors()
            self.assertEqual(len(errors), 0, 
                f"JavaScript errors found during template selection: {errors}")
