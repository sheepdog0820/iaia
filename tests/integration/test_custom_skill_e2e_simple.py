"""
カスタム技能機能の簡易E2Eテスト（デバッグ付き）
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
from django.contrib.sessions.models import Session

User = get_user_model()


@override_settings(DEBUG=True)
class CustomSkillE2EDebugTest(StaticLiveServerTestCase):
    """カスタム技能追加機能の簡易E2Eテスト（デバッグ版）"""
    
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
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # adminユーザーも作成（開発用ログインで使用）
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
    
    def test_debug_page_access(self):
        """ページアクセスのデバッグテスト"""
        # 1. ホームページにアクセス
        print(f"\n1. ホームページにアクセス: {self.live_server_url}")
        self.selenium.get(self.live_server_url)
        time.sleep(2)
        
        print(f"ページタイトル: {self.selenium.title}")
        print(f"現在のURL: {self.selenium.current_url}")
        
        # スクリーンショットを保存（デバッグ用）
        screenshot_dir = "/tmp/selenium_debug"
        os.makedirs(screenshot_dir, exist_ok=True)
        self.selenium.save_screenshot(f"{screenshot_dir}/1_homepage.png")
        
        # 2. 開発用ログインページにアクセス
        print(f"\n2. 開発用ログインページにアクセス")
        dev_login_url = f"{self.live_server_url}/accounts/dev-login/"
        self.selenium.get(dev_login_url)
        time.sleep(2)
        
        print(f"ページタイトル: {self.selenium.title}")
        print(f"現在のURL: {self.selenium.current_url}")
        self.selenium.save_screenshot(f"{screenshot_dir}/2_dev_login.png")
        
        # ページソースの一部を出力
        page_source = self.selenium.page_source
        if "開発用クイックログイン" in page_source:
            print("開発用ログインページが表示されています")
        else:
            print("開発用ログインページが見つかりません")
            print(f"ページソースの最初の500文字: {page_source[:500]}")
        
        # 3. adminユーザーでログイン
        try:
            # ユーザー選択
            user_select = self.selenium.find_element(By.NAME, "username")
            user_select.send_keys("admin")
            
            # ログインボタンをクリック
            login_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            time.sleep(2)
            print(f"\n3. ログイン後のURL: {self.selenium.current_url}")
            self.selenium.save_screenshot(f"{screenshot_dir}/3_after_login.png")
        except Exception as e:
            print(f"ログインエラー: {e}")
            self.selenium.save_screenshot(f"{screenshot_dir}/3_login_error.png")
        
        # 4. キャラクター作成画面にアクセス
        print(f"\n4. キャラクター作成画面にアクセス")
        create_url = f"{self.live_server_url}/accounts/character/create/6th/"
        self.selenium.get(create_url)
        time.sleep(3)
        
        print(f"ページタイトル: {self.selenium.title}")
        print(f"現在のURL: {self.selenium.current_url}")
        self.selenium.save_screenshot(f"{screenshot_dir}/4_character_create.png")
        
        # ページ内の要素を確認
        try:
            # キャラクター名入力欄を探す
            char_name = self.selenium.find_element(By.ID, "character-name")
            print("キャラクター名入力欄: 見つかりました")
        except:
            print("キャラクター名入力欄: 見つかりません")
            
        try:
            # 技能タブを探す
            skills_tab = self.selenium.find_element(By.ID, "skills-tab")
            print("技能タブ: 見つかりました")
        except:
            print("技能タブ: 見つかりません")
        
        # JavaScriptエラーをチェック
        logs = self.selenium.get_log('browser')
        if logs:
            print("\nブラウザコンソールログ:")
            for log in logs:
                print(f"  {log['level']}: {log['message']}")
        
        print(f"\nスクリーンショットは {screenshot_dir} に保存されました")
    
    def test_custom_skill_functionality(self):
        """カスタム技能機能の簡易テスト"""
        # 開発用ログインを使用
        self.selenium.get(f"{self.live_server_url}/accounts/dev-login/")
        time.sleep(1)
        
        try:
            # adminでログイン
            user_select = self.selenium.find_element(By.NAME, "username")
            user_select.send_keys("admin")
            login_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            time.sleep(2)
        except:
            print("ログインをスキップ")
        
        # キャラクター作成画面に直接アクセス
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        time.sleep(3)
        
        # 基本情報を入力
        try:
            self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者")
            self.selenium.find_element(By.ID, "age").send_keys("25")
            
            # 能力値を入力
            abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            for ability in abilities:
                element = self.selenium.find_element(By.ID, ability)
                element.clear()
                element.send_keys("10")
            
            # 技能タブをクリック
            self.selenium.find_element(By.ID, "skills-tab").click()
            time.sleep(2)
            
            # JavaScriptが読み込まれているか確認
            result = self.selenium.execute_script("return typeof addCustomSkill")
            print(f"addCustomSkill関数の型: {result}")
            
            # カスタム技能追加ボタンが存在するか確認
            buttons = self.selenium.find_elements(By.XPATH, "//button[contains(text(), 'カスタム技能を追加')]")
            print(f"カスタム技能追加ボタンの数: {len(buttons)}")
            
            if buttons:
                # 最初のボタンをクリック
                buttons[0].click()
                time.sleep(1)
                
                # カスタム技能が追加されたか確認
                custom_skills = self.selenium.find_elements(By.CSS_SELECTOR, ".custom-skill")
                print(f"カスタム技能の数: {len(custom_skills)}")
                
                self.assertGreater(len(custom_skills), 0, "カスタム技能が追加されていません")
                
                # スクリーンショットを保存
                screenshot_dir = "/tmp/selenium_debug"
                os.makedirs(screenshot_dir, exist_ok=True)
                self.selenium.save_screenshot(f"{screenshot_dir}/custom_skill_added.png")
                print(f"スクリーンショット保存: {screenshot_dir}/custom_skill_added.png")
                
        except Exception as e:
            print(f"エラー発生: {e}")
            screenshot_dir = "/tmp/selenium_debug"
            os.makedirs(screenshot_dir, exist_ok=True)
            self.selenium.save_screenshot(f"{screenshot_dir}/error.png")
            raise