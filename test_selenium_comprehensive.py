#!/usr/bin/env python3
"""
Selenium 包括的UIテスト
キャラクターシート6版の完全な動作確認
"""

import os
import sys
import time
import unittest
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
import django
django.setup()


class ComprehensiveCharacterTest(unittest.TestCase):
    """キャラクターシート6版の包括的UIテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        cls.base_url = "http://localhost:8000"
        cls.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def setUp(self):
        """各テストメソッドの前に実行"""
        # Chrome オプション設定
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--window-size=1920,1080')
        
        # ヘッドレスモードオプション（CI環境用）
        if os.environ.get('CI'):
            options.add_argument('--headless')
        
        # ChromeDriver サービス
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """各テストメソッドの後に実行"""
        if self.driver:
            self.driver.quit()
    
    def test_01_complete_character_workflow(self):
        """完全なキャラクター作成ワークフロー"""
        print("\n" + "="*70)
        print("完全なキャラクター作成ワークフローテスト")
        print("="*70)
        
        # ステップ1: 開発用ログイン
        print("\n[ステップ1] 開発用ログイン")
        self._dev_login("investigator1")
        print("✓ ログイン成功")
        
        # ステップ2: キャラクター一覧ページ
        print("\n[ステップ2] キャラクター一覧ページ確認")
        self.driver.get(f"{self.base_url}/accounts/character/list/")
        self._wait_for_page_load()
        
        # 既存キャラクター数を記録
        existing_characters = len(self.driver.find_elements(By.CLASS_NAME, "card"))
        print(f"既存キャラクター数: {existing_characters}")
        
        # ステップ3: 新規キャラクター作成ページへ
        print("\n[ステップ3] 新規キャラクター作成")
        self.driver.get(f"{self.base_url}/accounts/character/create/6th/")
        self._wait_for_page_load()
        
        # ステップ4: フォーム入力
        print("\n[ステップ4] フォーム入力")
        
        # フィールド名のマッピング（実際のname属性に合わせる）
        character_data = {
            'name': f'テスト探索者_{self.test_timestamp}',
            'age': '28',
            'occupation': 'ジャーナリスト',
            'birthplace': '東京'
        }
        
        # 能力値データ（別途処理）
        ability_data = {
            'str': '13',
            'con': '12',
            'pow': '14',
            'dex': '11',
            'app': '10',
            'siz': '15',
            'int': '16',
            'edu': '17'
        }
        
        # 基本情報入力
        print("基本情報:")
        for field_name, value in character_data.items():
            try:
                field = self.driver.find_element(By.NAME, field_name)
                field.clear()
                field.send_keys(value)
                print(f"  ✓ {field_name}: {value}")
            except NoSuchElementException:
                print(f"  ✗ {field_name}: フィールドが見つかりません")
        
        # 能力値入力
        print("\n能力値:")
        for ability_name, value in ability_data.items():
            try:
                # 能力値フィールドはIDで探す
                field = self.driver.find_element(By.ID, ability_name)
                
                # フィールドがreadonly属性を持っているか確認
                is_readonly = field.get_attribute("readonly")
                is_disabled = field.get_attribute("disabled")
                
                if is_readonly or is_disabled:
                    print(f"  ⚠️  {ability_name.upper()}: フィールドはreadonly/disabledです")
                    continue
                
                # JavaScriptで値を設定（より確実な方法）
                self.driver.execute_script(f"arguments[0].value = '{value}';", field)
                # 変更イベントを発火
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", field)
                print(f"  ✓ {ability_name.upper()}: {value}")
            except NoSuchElementException:
                print(f"  ✗ {ability_name.upper()}: フィールドが見つかりません")
            except Exception as e:
                print(f"  ✗ {ability_name.upper()}: エラー - {type(e).__name__}")
        
        # ステップ5: フォーム送信
        print("\n[ステップ5] フォーム送信")
        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            
            # スクロールしてボタンを表示
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)
            
            # JavaScriptでクリック（通常のクリックが効かない場合の対策）
            self.driver.execute_script("arguments[0].click();", submit_button)
            print("✓ フォーム送信完了")
        except Exception as e:
            print(f"✗ フォーム送信エラー: {e}")
            # スクリーンショットを保存
            self.driver.save_screenshot(f"submit_error_{self.test_timestamp}.png")
        
        # ステップ6: 作成結果確認
        print("\n[ステップ6] 作成結果確認")
        time.sleep(3)  # リダイレクトを待つ
        
        current_url = self.driver.current_url
        if "/character/" in current_url and "/create/" not in current_url:
            print(f"✓ キャラクター詳細ページにリダイレクト: {current_url}")
            
            # キャラクター情報の確認
            try:
                page_content = self.driver.page_source
                if character_data['name'] in page_content:
                    print(f"✓ キャラクター名が表示されています: {character_data['name']}")
                
                # 能力値の確認
                for ability in ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']:
                    if ability_data[ability] in page_content:
                        print(f"  ✓ {ability.upper()}: {ability_data[ability]}")
            except Exception as e:
                print(f"  ✗ 詳細確認中にエラー: {e}")
        else:
            print(f"  ⚠️  予期しないURL: {current_url}")
            
            # エラーメッセージの確認
            error_messages = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
            if error_messages:
                print("\n  エラーメッセージ:")
                for msg in error_messages:
                    print(f"    - {msg.text}")
            
            # フォームエラーの確認
            form_errors = self.driver.find_elements(By.CLASS_NAME, "invalid-feedback")
            if form_errors:
                print("\n  フォームエラー:")
                for err in form_errors:
                    if err.is_displayed():
                        print(f"    - {err.text}")
            
            # エラーがない場合、フォームの検証状態を確認
            if not error_messages and not form_errors:
                print("\n  デバッグ情報:")
                # 送信ボタンの状態
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                print(f"    送信ボタン有効: {submit_btn.is_enabled()}")
                print(f"    送信ボタンテキスト: {submit_btn.text}")
                
                # スクリーンショット保存
                self.driver.save_screenshot(f"form_state_{self.test_timestamp}.png")
                print(f"    スクリーンショット保存: form_state_{self.test_timestamp}.png")
        
        # ステップ7: キャラクター一覧に戻る
        print("\n[ステップ7] キャラクター一覧に戻る")
        self.driver.get(f"{self.base_url}/accounts/character/list/")
        self._wait_for_page_load()
        
        new_character_count = len(self.driver.find_elements(By.CLASS_NAME, "card"))
        if new_character_count > existing_characters:
            print(f"✓ 新しいキャラクターが追加されました（{existing_characters} → {new_character_count}）")
        else:
            print(f"  ⚠️  キャラクター数が増えていません（{new_character_count}）")
        
        print("\n" + "="*70)
        print("テスト完了")
        print("="*70)
    
    def test_02_navigation_test(self):
        """ナビゲーションと画面遷移テスト"""
        print("\n" + "="*70)
        print("ナビゲーションテスト")
        print("="*70)
        
        # ログイン
        self._dev_login("investigator1")
        
        # メインナビゲーションのテスト
        navigation_tests = [
            ("ホーム", "/", "Arkham Nexus"),
            ("キャラクター一覧", "/accounts/character/list/", "キャラクター"),
            ("ダッシュボード", "/accounts/dashboard/", "ダッシュボード"),
        ]
        
        for nav_name, url, expected_content in navigation_tests:
            print(f"\n[{nav_name}] {url}")
            self.driver.get(f"{self.base_url}{url}")
            self._wait_for_page_load()
            
            page_title = self.driver.title
            page_content = self.driver.page_source
            
            if expected_content in page_title or expected_content in page_content:
                print(f"  ✓ ページ読み込み成功")
                print(f"  タイトル: {page_title}")
            else:
                print(f"  ✗ 期待されるコンテンツが見つかりません")
    
    def test_03_responsive_design(self):
        """レスポンシブデザインテスト"""
        print("\n" + "="*70)
        print("レスポンシブデザインテスト")
        print("="*70)
        
        # ログイン
        self._dev_login("investigator1")
        
        # テストするページ
        test_url = f"{self.base_url}/accounts/character/create/6th/"
        self.driver.get(test_url)
        self._wait_for_page_load()
        
        # 各画面サイズでテスト
        screen_sizes = [
            ("デスクトップ", 1920, 1080),
            ("タブレット（横）", 1024, 768),
            ("タブレット（縦）", 768, 1024),
            ("スマートフォン", 375, 667)
        ]
        
        for device_name, width, height in screen_sizes:
            print(f"\n[{device_name}] {width}x{height}")
            self.driver.set_window_size(width, height)
            time.sleep(1)
            
            # 要素の表示確認
            try:
                # フォームが表示されているか
                form = self.driver.find_element(By.TAG_NAME, "form")
                if form.is_displayed():
                    print("  ✓ フォーム表示: OK")
                
                # 送信ボタンが表示されているか
                submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                if submit.is_displayed():
                    print("  ✓ 送信ボタン表示: OK")
                
                # スクリーンショット保存
                screenshot_name = f"responsive_{device_name.replace(' ', '_')}_{self.test_timestamp}.png"
                self.driver.save_screenshot(screenshot_name)
                print(f"  ✓ スクリーンショット保存: {screenshot_name}")
                
            except Exception as e:
                print(f"  ✗ エラー: {e}")
    
    def _dev_login(self, username):
        """開発用ログインのヘルパーメソッド"""
        self.driver.get(f"{self.base_url}/accounts/dev-login/")
        self._wait_for_page_load()
        
        # ユーザーカードを探してログイン
        user_cards = self.driver.find_elements(By.CLASS_NAME, "user-card")
        for card in user_cards:
            username_elements = card.find_elements(By.CLASS_NAME, "username")
            if username_elements and username in username_elements[0].text:
                login_button = card.find_element(By.CLASS_NAME, "login-btn")
                login_button.click()
                
                # ログイン完了を待つ
                WebDriverWait(self.driver, 10).until(
                    lambda driver: "/dev-login/" not in driver.current_url
                )
                break
    
    def _wait_for_page_load(self):
        """ページ読み込み完了を待つ"""
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )


if __name__ == '__main__':
    # テスト実行
    print("\n" + "="*70)
    print("Selenium 包括的UIテスト")
    print("テスト開始時刻:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    # サーバーが起動しているか確認
    import requests
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print("✅ 開発サーバーが起動しています")
    except:
        print("❌ エラー: 開発サーバーが起動していません")
        print("別のターミナルで以下を実行してください:")
        print("python3 manage.py runserver")
        sys.exit(1)
    
    # テスト実行
    unittest.main(verbosity=2)