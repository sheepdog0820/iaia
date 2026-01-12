"""
カスタム技能機能の最終E2Eテスト
"""
import os
import time
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

User = get_user_model()


@override_settings(DEBUG=True)
class CustomSkillE2EFinalTest(StaticLiveServerTestCase):
    """カスタム技能追加機能の最終E2Eテスト"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Chromeオプション設定
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            cls.selenium = webdriver.Chrome(options=chrome_options)
            cls.selenium.implicitly_wait(10)
        except Exception as e:
            print(f"Chrome WebDriver初期化エラー: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'selenium'):
            cls.selenium.quit()
        super().tearDownClass()
    
    def setUp(self):
        """テストユーザーの作成"""
        # 開発用ログインで使用するユーザーを作成
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.keeper1 = User.objects.create_user(
            username='keeper1',
            email='keeper1@example.com',
            password='keeper123'
        )
    
    def test_custom_skill_add_and_remove(self):
        """カスタム技能の追加と削除のE2Eテスト"""
        # Seleniumログインはdev-login UIに依存しない（POST形式変更に追従するため）
        client = Client()
        logged_in = client.login(username='admin', password='admin123')
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
        self.selenium.get(f"{self.live_server_url}/accounts/dashboard/")
        
        # 3. キャラクター作成画面に移動
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        WebDriverWait(self.selenium, 20).until(
            EC.presence_of_element_located((By.ID, "character-name"))
        )
        
        # 4. 基本情報を入力
        try:
            # キャラクター名
            name_input = self.selenium.find_element(By.ID, "character-name")
            name_input.send_keys("カスタム技能テスト探索者")
            
            # 年齢
            age_input = self.selenium.find_element(By.ID, "age")
            age_input.send_keys("30")
            
            # 能力値を入力（能力値タブへ移動してから）
            abilities_tab = WebDriverWait(self.selenium, 20).until(
                EC.element_to_be_clickable((By.ID, "abilities-tab"))
            )
            self.selenium.execute_script("arguments[0].click();", abilities_tab)
            WebDriverWait(self.selenium, 20).until(
                EC.visibility_of_element_located((By.ID, "abilities"))
            )
            abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            for ability in abilities:
                element = WebDriverWait(self.selenium, 20).until(
                    EC.element_to_be_clickable((By.ID, ability))
                )
                element.clear()
                element.send_keys("12")
            
            print("基本情報を入力しました")
        except Exception as e:
            print(f"基本情報入力エラー: {e}")
            self.selenium.save_screenshot("/tmp/selenium_debug/basic_info_error.png")
            raise
        
        # 5. 技能タブに移動
        try:
            skills_tab = self.selenium.find_element(By.ID, "skills-tab")
            self.selenium.execute_script("arguments[0].click();", skills_tab)
            WebDriverWait(self.selenium, 20).until(
                EC.visibility_of_element_located((By.ID, "skills"))
            )
            print("技能タブに移動しました")
        except Exception as e:
            print(f"技能タブエラー: {e}")
            self.selenium.save_screenshot("/tmp/selenium_debug/skills_tab_error.png")
            raise
        
        # 6. カスタム技能追加ボタンを探す
        try:
            self.selenium.execute_script("arguments[0].click();", self.selenium.find_element(By.ID, "combat-tab"))

            add_button = WebDriverWait(self.selenium, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#combat button[data-custom-skill-category='combat']"))
            )
            self.selenium.execute_script("arguments[0].click();", add_button)

            custom_skills = WebDriverWait(self.selenium, 20).until(
                lambda driver: driver.find_elements(By.CSS_SELECTOR, "#combat .custom-skill")
            )
            print(f"追加されたカスタム技能の数: {len(custom_skills)}")
            
            # スクリーンショットを保存
            self.selenium.save_screenshot("/tmp/selenium_debug/custom_skill_added.png")
            
            # カスタム技能が存在することを確認
            self.assertGreater(len(custom_skills), 0, "カスタム技能が追加されていません")
            
            # 7. カスタム技能名を変更
            if custom_skills:
                name_input = custom_skills[0].find_element(By.CSS_SELECTOR, ".custom-skill-name")
                name_input.clear()
                name_input.send_keys("カスタム格闘術")
                print("カスタム技能名を変更しました")
                
                # 8. カスタム技能を削除
                delete_button = custom_skills[0].find_element(By.CSS_SELECTOR, ".btn-outline-danger")
                delete_button.click()
                time.sleep(1)
                print("カスタム技能を削除しました")
                
                # 削除後の確認
                remaining_skills = self.selenium.find_elements(By.CSS_SELECTOR, ".custom-skill")
                print(f"削除後のカスタム技能の数: {len(remaining_skills)}")
                
                # スクリーンショットを保存
                self.selenium.save_screenshot("/tmp/selenium_debug/custom_skill_deleted.png")
            
        except Exception as e:
            print(f"カスタム技能操作エラー: {e}")
            self.selenium.save_screenshot("/tmp/selenium_debug/custom_skill_error.png")
            raise
        
        print("\nE2Eテスト完了")
        print("スクリーンショットは /tmp/selenium_debug/ に保存されました")
