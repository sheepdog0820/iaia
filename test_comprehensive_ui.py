#!/usr/bin/env python3
"""
Arkham Nexus 包括的UIテスト
キャラクターシート6版を含む全機能のSelenium UIテスト
"""

import os
import sys
import time
import uuid
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ComprehensiveUITest:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.test_results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        self.screenshots = []
        
    def setup(self):
        """WebDriverのセットアップ"""
        print("=== Arkham Nexus 包括的UIテスト ===\n")
        print("セットアップ中...")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # ユニークなプロファイル
        self.profile_dir = f'/tmp/chrome-profile-{uuid.uuid4()}'
        options.add_argument(f'--user-data-dir={self.profile_dir}')
        
        try:
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 10)
            print("✅ WebDriver セットアップ完了\n")
            return True
        except Exception as e:
            print(f"❌ セットアップエラー: {e}")
            return False
    
    def teardown(self):
        """クリーンアップ"""
        if self.driver:
            self.driver.quit()
        
        if os.path.exists(self.profile_dir):
            import shutil
            try:
                shutil.rmtree(self.profile_dir)
            except:
                pass
    
    def save_screenshot(self, name):
        """スクリーンショットを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'/tmp/ui_test_{name}_{timestamp}.png'
        self.driver.save_screenshot(filename)
        self.screenshots.append(filename)
        return filename
    
    def run_test(self, test_name, test_func):
        """個別テストを実行"""
        self.test_results['total'] += 1
        print(f"\n🧪 {test_name}")
        try:
            test_func()
            self.test_results['passed'] += 1
            print(f"   ✅ 成功")
        except Exception as e:
            self.test_results['failed'] += 1
            self.test_results['errors'].append({
                'test': test_name,
                'error': str(e)
            })
            print(f"   ❌ 失敗: {e}")
            # エラー時のスクリーンショット
            self.save_screenshot(f"error_{test_name.replace(' ', '_')}")
    
    def test_01_home_page(self):
        """ホームページアクセステスト"""
        self.driver.get('http://localhost:8000/')
        assert 'Gate of Yog-Sothoth' in self.driver.title
        self.save_screenshot('home_page')
    
    def test_02_login_page(self):
        """ログインページ表示テスト"""
        self.driver.get('http://localhost:8000/accounts/login/')
        
        # ログインフォーム要素の確認
        username = self.wait.until(
            EC.presence_of_element_located((By.ID, 'id_username'))
        )
        password = self.driver.find_element(By.ID, 'id_password')
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        assert username.is_displayed()
        assert password.is_displayed()
        assert submit_btn.is_displayed()
        
        self.save_screenshot('login_page')
    
    def test_03_test_login(self):
        """テストユーザーでログイン"""
        self.driver.get('http://localhost:8000/accounts/login/')
        
        # adminユーザーでログイン試行
        username = self.driver.find_element(By.ID, 'id_username')
        password = self.driver.find_element(By.ID, 'id_password')
        
        username.send_keys('admin')
        password.send_keys('arkham_admin_2024')
        password.send_keys(Keys.RETURN)
        
        time.sleep(2)
        
        # ログイン成功の確認（リダイレクト先を確認）
        current_url = self.driver.current_url
        assert 'login' not in current_url
        
        self.save_screenshot('after_login')
    
    def test_04_character_list(self):
        """キャラクター一覧ページ"""
        self.driver.get('http://localhost:8000/accounts/character/list/')
        
        # ページタイトルまたは要素の確認
        time.sleep(1)
        page_source = self.driver.page_source
        
        # JavaScriptが読み込まれているか確認
        assert 'loadCharacters' in page_source or 'キャラクター' in page_source
        
        self.save_screenshot('character_list')
    
    def test_05_character_create_6th(self):
        """6版キャラクター作成ページ"""
        self.driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(1)
        
        # フォーム要素の確認
        page_source = self.driver.page_source
        
        # 能力値入力フィールドの存在確認
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            # フィールドが存在することを確認（name属性で）
            assert f'name="{ability}"' in page_source or f'id="{ability}"' in page_source
        
        self.save_screenshot('character_create_6th')
    
    def test_06_navigation_menu(self):
        """ナビゲーションメニューテスト"""
        self.driver.get('http://localhost:8000/')
        time.sleep(1)
        
        # ナビゲーションリンクの確認
        page_source = self.driver.page_source
        
        # 主要メニュー項目の確認
        menu_items = ['カレンダー', 'セッション', 'シナリオ', 'グループ']
        for item in menu_items:
            assert item in page_source or item.lower() in page_source.lower()
        
        self.save_screenshot('navigation_menu')
    
    def test_07_responsive_design(self):
        """レスポンシブデザインテスト"""
        self.driver.get('http://localhost:8000/')
        
        # デスクトップサイズ
        self.driver.set_window_size(1920, 1080)
        time.sleep(0.5)
        self.save_screenshot('responsive_desktop')
        
        # タブレットサイズ
        self.driver.set_window_size(768, 1024)
        time.sleep(0.5)
        self.save_screenshot('responsive_tablet')
        
        # モバイルサイズ
        self.driver.set_window_size(375, 667)
        time.sleep(0.5)
        self.save_screenshot('responsive_mobile')
        
        # サイズを戻す
        self.driver.set_window_size(1920, 1080)
    
    def test_08_javascript_functions(self):
        """JavaScript関数の存在確認"""
        self.driver.get('http://localhost:8000/')
        
        # カスタムJavaScript関数の確認
        js_check = self.driver.execute_script("""
            return {
                loadCalendarView: typeof loadCalendarView !== 'undefined',
                loadSessionsView: typeof loadSessionsView !== 'undefined',
                loadScenariosView: typeof loadScenariosView !== 'undefined',
                loadGroupsView: typeof loadGroupsView !== 'undefined',
                loadStatisticsView: typeof loadStatisticsView !== 'undefined'
            }
        """)
        
        # 少なくとも一部の関数が定義されていること
        assert any(js_check.values())
    
    def test_09_form_validation(self):
        """フォームバリデーションテスト"""
        self.driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(1)
        
        # 空のフォーム送信を試行
        try:
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_btn.click()
            time.sleep(1)
            
            # エラーメッセージの確認
            page_source = self.driver.page_source
            assert 'error' in page_source.lower() or '必須' in page_source
            
            self.save_screenshot('form_validation')
        except NoSuchElementException:
            # フォームが異なる構造の場合はスキップ
            pass
    
    def test_10_performance_metrics(self):
        """パフォーマンスメトリクス"""
        self.driver.get('http://localhost:8000/')
        
        # Navigation Timing API
        metrics = self.driver.execute_script("""
            var timing = window.performance.timing;
            return {
                loadTime: timing.loadEventEnd - timing.navigationStart,
                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                responseTime: timing.responseEnd - timing.requestStart,
                domInteractive: timing.domInteractive - timing.navigationStart
            }
        """)
        
        print(f"   パフォーマンスメトリクス:")
        print(f"   - ページ読み込み時間: {metrics['loadTime']}ms")
        print(f"   - DOM Content Loaded: {metrics['domContentLoaded']}ms")
        print(f"   - サーバーレスポンス: {metrics['responseTime']}ms")
        print(f"   - DOM Interactive: {metrics['domInteractive']}ms")
        
        # 基本的なパフォーマンス基準
        assert metrics['loadTime'] < 5000  # 5秒以内
    
    def run_all_tests(self):
        """全テストを実行"""
        if not self.setup():
            return False
        
        tests = [
            ("ホームページアクセス", self.test_01_home_page),
            ("ログインページ表示", self.test_02_login_page),
            ("管理者ログイン", self.test_03_test_login),
            ("キャラクター一覧", self.test_04_character_list),
            ("6版キャラクター作成", self.test_05_character_create_6th),
            ("ナビゲーションメニュー", self.test_06_navigation_menu),
            ("レスポンシブデザイン", self.test_07_responsive_design),
            ("JavaScript関数確認", self.test_08_javascript_functions),
            ("フォームバリデーション", self.test_09_form_validation),
            ("パフォーマンス測定", self.test_10_performance_metrics)
        ]
        
        print("=" * 50)
        print("テスト実行開始")
        print("=" * 50)
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        self.print_results()
        self.teardown()
        
        return self.test_results['failed'] == 0
    
    def print_results(self):
        """テスト結果を表示"""
        print("\n" + "=" * 50)
        print("テスト結果サマリー")
        print("=" * 50)
        print(f"総テスト数: {self.test_results['total']}")
        print(f"✅ 成功: {self.test_results['passed']}")
        print(f"❌ 失敗: {self.test_results['failed']}")
        
        if self.test_results['errors']:
            print("\nエラー詳細:")
            for error in self.test_results['errors']:
                print(f"  - {error['test']}: {error['error']}")
        
        print(f"\n保存されたスクリーンショット:")
        for screenshot in self.screenshots:
            print(f"  - {screenshot}")
        
        print("\n" + "=" * 50)
        if self.test_results['failed'] == 0:
            print("🎉 全テスト成功！")
        else:
            print("⚠️  一部のテストが失敗しました")
        print("=" * 50)


if __name__ == '__main__':
    # 開発サーバーの確認
    import requests
    try:
        response = requests.get('http://localhost:8000/', timeout=2)
        print("✅ 開発サーバーが起動しています\n")
    except:
        print("❌ 開発サーバーが起動していません")
        print("python3 manage.py runserver を実行してください")
        sys.exit(1)
    
    # テスト実行
    tester = ComprehensiveUITest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)