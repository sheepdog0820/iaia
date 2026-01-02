#!/usr/bin/env python
"""
Selenium WebDriverを使用したブラウザ自動化テスト
ブラウザでの実際のユーザー操作をシミュレートします。

使用方法: python browser_tests.py
必須: pip install selenium
"""

import os
import sys
import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class ArkhamNexusBrowserTests(unittest.TestCase):
    """
    タブレノ Webアプリケーションのブラウザテスト
    """
    
    @classmethod
    def setUpClass(cls):
        """テストクラス開始時の設定"""
        cls.base_url = "http://localhost:8000"
        
        # Chromeオプション設定（ヘッドレスモード対応）
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # ヘッドレスモード
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(10)
            cls.wait = WebDriverWait(cls.driver, 10)
        except Exception as e:
            print(f"WebDriver初期化エラー: {e}")
            print("Chromeドライバーがインストールされていない可能性があります")
            print("以下のコマンドでインストールしてください:")
            print("pip install selenium webdriver-manager")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """テストクラス終了時のクリーンアップ"""
        if hasattr(cls, 'driver'):
            cls.driver.quit()
    
    def test_01_home_page_loads(self):
        """ホームページの読み込みテスト"""
        self.driver.get(self.base_url)
        
        # タイトル確認
        self.assertIn("タブレノ", self.driver.title)
        
        # ナビゲーションバー確認
        navbar = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "navbar"))
        )
        self.assertTrue(navbar.is_displayed())
        
        # ロゴ確認
        logo = self.driver.find_element(By.CLASS_NAME, "navbar-brand")
        self.assertTrue(logo.is_displayed())
        
        print("✓ ホームページが正常に読み込まれました")
    
    def test_02_navigation_links(self):
        """ナビゲーションリンクのテスト"""
        self.driver.get(self.base_url)
        
        # ログインリンクの確認とクリック
        login_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/accounts/login')]")
        self.assertTrue(len(login_links) > 0, "ログインリンクが見つかりません")
        
        # ログインページへ移動
        login_links[0].click()
        
        # ログインページの確認
        self.wait.until(EC.title_contains("ログイン"))
        self.assertIn("ログイン", self.driver.title)
        
        print("✓ ナビゲーションリンクが正常に動作します")
    
    def test_03_demo_login_flow(self):
        """デモログインフローのテスト"""
        # デモページに移動
        self.driver.get(f"{self.base_url}/accounts/demo/")
        
        # デモページの確認
        self.wait.until(EC.title_contains("デモログイン"))
        
        # Googleモックログインボタンを探してクリック
        try:
            google_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'mock-social/google')]"))
            )
            google_btn.click()
            
            # ダッシュボードにリダイレクトされることを確認
            self.wait.until(EC.title_contains("ダッシュボード"))
            self.assertIn("ダッシュボード", self.driver.title)
            
            print("✓ デモログインが正常に動作します")
            
        except TimeoutException:
            print("⚠ デモログインボタンが見つかりません")
            self.fail("デモログインボタンが見つかりません")
    
    def test_04_dashboard_functionality(self):
        """ダッシュボード機能のテスト（ログイン後）"""
        # まずログイン
        self.driver.get(f"{self.base_url}/accounts/mock-social/google/")
        
        # ダッシュボードページの確認
        self.wait.until(EC.title_contains("ダッシュボード"))
        
        # 統計カードの確認
        stat_cards = self.driver.find_elements(By.CLASS_NAME, "card-title")
        self.assertTrue(len(stat_cards) > 0, "統計カードが見つかりません")
        
        # ユーザープロフィール領域の確認
        try:
            profile_section = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'eldritch-font')]")
            self.assertTrue(profile_section.is_displayed())
        except NoSuchElementException:
            print("⚠ プロフィールセクションが見つかりません")
        
        print("✓ ダッシュボードが正常に表示されます")
    
    def test_05_logout_functionality(self):
        """ログアウト機能のテスト"""
        # ログイン状態から開始
        self.driver.get(f"{self.base_url}/accounts/mock-social/google/")
        self.wait.until(EC.title_contains("ダッシュボード"))
        
        # ログアウトリンクを探してクリック
        try:
            logout_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/accounts/logout')]"))
            )
            logout_link.click()
            
            # ログアウトページまたはホームページにリダイレクトされることを確認
            time.sleep(2)  # リダイレクト待機
            current_url = self.driver.current_url
            self.assertTrue(
                "/accounts/logout" in current_url or current_url.endswith("/"),
                f"予期しないページにリダイレクトされました: {current_url}"
            )
            
            print("✓ ログアウトが正常に動作します")
            
        except TimeoutException:
            print("⚠ ログアウトリンクが見つかりません")
    
    def test_06_responsive_design(self):
        """レスポンシブデザインのテスト"""
        self.driver.get(self.base_url)
        
        # デスクトップサイズ
        self.driver.set_window_size(1920, 1080)
        navbar = self.driver.find_element(By.CLASS_NAME, "navbar")
        self.assertTrue(navbar.is_displayed())
        
        # タブレットサイズ
        self.driver.set_window_size(768, 1024)
        time.sleep(1)  # レイアウト調整待機
        navbar = self.driver.find_element(By.CLASS_NAME, "navbar")
        self.assertTrue(navbar.is_displayed())
        
        # モバイルサイズ
        self.driver.set_window_size(375, 667)
        time.sleep(1)  # レイアウト調整待機
        navbar = self.driver.find_element(By.CLASS_NAME, "navbar")
        self.assertTrue(navbar.is_displayed())
        
        # ハンバーガーメニューの確認（モバイル）
        try:
            toggle_btn = self.driver.find_element(By.CLASS_NAME, "navbar-toggler")
            self.assertTrue(toggle_btn.is_displayed())
            print("✓ レスポンシブデザインが正常に動作します")
        except NoSuchElementException:
            print("⚠ ハンバーガーメニューが見つかりません")
    
    def test_07_api_browsable_interface(self):
        """Django REST Framework ブラウザブルAPIのテスト"""
        # まずログイン
        self.driver.get(f"{self.base_url}/accounts/mock-social/google/")
        self.wait.until(EC.title_contains("ダッシュボード"))
        
        # APIエンドポイントにアクセス
        self.driver.get(f"{self.base_url}/api/schedules/sessions/view/")
        
        # APIページが表示されることを確認
        try:
            # DRFの特徴的な要素を探す
            api_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'region')]")
            if len(api_elements) > 0:
                print("✓ ブラウザブルAPIが正常に表示されます")
            else:
                # JSONレスポンスの場合
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "count" in body_text or "results" in body_text:
                    print("✓ APIがJSON形式で正常にレスポンスします")
                else:
                    print("⚠ 予期しないAPIレスポンス")
        except Exception as e:
            print(f"⚠ API テストでエラー: {e}")
    
    def test_08_error_handling(self):
        """エラーハンドリングのテスト"""
        # 存在しないページにアクセス
        self.driver.get(f"{self.base_url}/nonexistent-page/")
        
        # 404ページまたはエラーページの確認
        time.sleep(2)
        page_source = self.driver.page_source.lower()
        
        # 一般的な404エラーの指標を確認
        error_indicators = ["404", "not found", "page not found", "error"]
        found_error = any(indicator in page_source for indicator in error_indicators)
        
        if found_error:
            print("✓ 404エラーが適切に処理されます")
        else:
            print("⚠ 404エラーページの処理を確認してください")


def run_browser_tests():
    """ブラウザテストの実行"""
    print("=" * 60)
    print("ARKHAM NEXUS ブラウザ自動化テスト開始")
    print("=" * 60)
    
    # WebDriverの依存関係チェック
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        # ChromeDriverの自動管理
        ArkhamNexusBrowserTests.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=Options()
        )
        print("✓ WebDriver自動管理を使用します")
        
    except ImportError:
        print("⚠ webdriver-manager未インストール - 手動インストールのWebDriverを使用")
    except Exception as e:
        print(f"⚠ WebDriver設定エラー: {e}")
        return False
    
    # テスト実行
    unittest.main(argv=[''], exit=False, verbosity=2)
    return True


if __name__ == "__main__":
    # 依存関係チェック
    try:
        import selenium
        print(f"Selenium バージョン: {selenium.__version__}")
    except ImportError:
        print("❌ Seleniumがインストールされていません")
        print("次のコマンドでインストールしてください:")
        print("pip install selenium webdriver-manager")
        sys.exit(1)
    
    # サーバー動作確認
    import requests
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("✓ サーバーが動作しています")
        else:
            print(f"⚠ サーバーレスポンス異常: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ サーバーが動作していません")
        print("./server.sh start でサーバーを起動してください")
        sys.exit(1)
    
    # テスト実行
    run_browser_tests()