#!/usr/bin/env python3
"""
Selenium UIテスト - キャラクターシート6版
開発用ログインとキャラクター一覧表示のテスト
"""

import os
import sys
import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
import django
django.setup()


class CharacterSheetUITest(unittest.TestCase):
    """キャラクターシート6版のUIテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        cls.base_url = "http://localhost:8000"
        
    def setUp(self):
        """各テストメソッドの前に実行"""
        # Chrome オプション設定
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--window-size=1920,1080')
        
        # ChromeDriver サービス
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """各テストメソッドの後に実行"""
        if self.driver:
            self.driver.quit()
    
    def test_01_dev_login(self):
        """開発用ログインページからログイン"""
        print("\n=== テスト1: 開発用ログイン ===")
        
        # 開発用ログインページにアクセス
        self.driver.get(f"{self.base_url}/accounts/dev-login/")
        
        # ページが完全に読み込まれるのを待つ
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "user-card"))
        )
        
        print(f"ページタイトル: {self.driver.title}")
        
        # investigator1でログイン
        try:
            # investigator1を含むユーザーカードを探す
            user_cards = self.driver.find_elements(By.CLASS_NAME, "user-card")
            login_button = None
            
            for card in user_cards:
                # カード内のユーザー名要素を確認
                username_elements = card.find_elements(By.CLASS_NAME, "username")
                if username_elements and "investigator1" in username_elements[0].text:
                    # このカード内のログインボタンを探す
                    login_button = card.find_element(By.CLASS_NAME, "login-btn")
                    print(f"investigator1のカードを発見: {username_elements[0].text}")
                    break
            
            self.assertIsNotNone(login_button, "investigator1のログインボタンが見つかりません")
            
            # ログインボタンをクリック
            print("ログインボタンをクリック")
            login_button.click()
            
            # ページ遷移を待つ
            WebDriverWait(self.driver, 10).until(
                lambda driver: "/dev-login/" not in driver.current_url
            )
            
            # ログイン成功確認
            current_url = self.driver.current_url
            print(f"ログイン後のURL: {current_url}")
            self.assertNotIn("/dev-login/", current_url)
            print("✓ ログイン成功")
            
        except TimeoutException:
            self.fail("ページの読み込みがタイムアウトしました")
        except Exception as e:
            print(f"エラー: {e}")
            self.driver.save_screenshot("login_error.png")
            raise
    
    def test_02_character_list_access(self):
        """ログイン後のキャラクター一覧アクセス"""
        print("\n=== テスト2: キャラクター一覧アクセス ===")
        
        # まずログイン
        self._dev_login("investigator1")
        
        # キャラクター一覧ページにアクセス
        self.driver.get(f"{self.base_url}/accounts/character/list/")
        
        # 現在のURLを確認
        print(f"現在のURL: {self.driver.current_url}")
        
        # ページが読み込まれるのを待つ
        try:
            # ページタイトルまたは本文のいずれかが存在することを確認
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.find_elements(By.TAG_NAME, "h1") or 
                              driver.find_elements(By.CLASS_NAME, "container")
            )
            
            # ページ要素の確認
            page_content = self.driver.page_source
            
            # ページタイトル確認（h1, h2, h3のいずれか）
            heading_found = False
            for tag in ['h1', 'h2', 'h3']:
                try:
                    heading = self.driver.find_element(By.TAG_NAME, tag)
                    print(f"ページ見出し({tag}): {heading.text}")
                    heading_found = True
                    break
                except:
                    continue
            
            if not heading_found:
                print("見出し要素が見つかりません")
            
            # ページタイトル（ブラウザ）
            print(f"ブラウザタイトル: {self.driver.title}")
            
            # キャラクター作成ボタンの確認（複数のパターンを試す）
            create_button_texts = ["キャラクター作成", "新規作成", "Create", "作成"]
            create_buttons = []
            for text in create_button_texts:
                buttons = self.driver.find_elements(By.PARTIAL_LINK_TEXT, text)
                create_buttons.extend(buttons)
            
            if create_buttons:
                print(f"✓ 作成ボタンを{len(create_buttons)}個発見")
            
            # キャラクターカードまたはテーブルの確認
            character_elements = (
                self.driver.find_elements(By.CLASS_NAME, "character-card") or
                self.driver.find_elements(By.CLASS_NAME, "card") or
                self.driver.find_elements(By.TAG_NAME, "table")
            )
            
            if character_elements:
                print(f"✓ キャラクター要素を{len(character_elements)}個発見")
            else:
                print("   キャラクター要素は存在しません（キャラクター未作成の可能性）")
            
            # ページにキャラクター関連のテキストがあるか確認
            if "キャラクター" in page_content or "character" in page_content.lower():
                print("✓ キャラクター関連のコンテンツを確認")
            
            print("✓ キャラクター一覧ページアクセス成功")
            
        except TimeoutException:
            self.fail("キャラクター一覧ページの読み込みがタイムアウトしました")
        except Exception as e:
            print(f"エラー: {e}")
            self.driver.save_screenshot("character_list_error.png")
            raise
    
    def test_03_character_create_page(self):
        """6版キャラクター作成ページアクセス"""
        print("\n=== テスト3: 6版キャラクター作成ページ ===")
        
        # まずログイン
        self._dev_login("investigator1")
        
        # 6版キャラクター作成ページに直接アクセス
        self.driver.get(f"{self.base_url}/accounts/character/create/6th/")
        
        try:
            # ページが読み込まれるのを待つ
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # ページ要素の確認
            print("ページ要素の確認:")
            
            # 基本情報フィールド
            basic_fields = ['name', 'age', 'sex', 'occupation', 'birthplace']
            for field_name in basic_fields:
                try:
                    field = self.driver.find_element(By.NAME, field_name)
                    print(f"  ✓ {field_name}フィールド: 存在")
                except:
                    print(f"  ✗ {field_name}フィールド: 見つかりません")
            
            # 能力値フィールド
            ability_fields = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
            found_abilities = 0
            for ability in ability_fields:
                try:
                    field = self.driver.find_element(By.NAME, ability)
                    found_abilities += 1
                except:
                    pass
            print(f"  ✓ 能力値フィールド: {found_abilities}/{len(ability_fields)}個発見")
            
            # 送信ボタン
            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
            if submit_buttons:
                print(f"  ✓ 送信ボタン: {len(submit_buttons)}個発見")
            
            print("✓ 6版キャラクター作成ページアクセス成功")
            
        except TimeoutException:
            self.fail("キャラクター作成ページの読み込みがタイムアウトしました")
        except Exception as e:
            print(f"エラー: {e}")
            self.driver.save_screenshot("character_create_error.png")
            raise
    
    def _dev_login(self, username):
        """開発用ログインのヘルパーメソッド"""
        self.driver.get(f"{self.base_url}/accounts/dev-login/")
        
        # ページが読み込まれるのを待つ
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "user-card"))
        )
        
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


if __name__ == '__main__':
    # テスト実行
    print("=" * 70)
    print("Selenium UIテスト - キャラクターシート6版")
    print("=" * 70)
    
    # サーバーが起動しているか確認
    import requests
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print("✅ 開発サーバーが起動しています\n")
    except:
        print("❌ エラー: 開発サーバーが起動していません")
        print("別のターミナルで以下を実行してください:")
        print("python3 manage.py runserver")
        sys.exit(1)
    
    # テスト実行
    unittest.main(verbosity=2)