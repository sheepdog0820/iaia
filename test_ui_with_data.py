#!/usr/bin/env python3
"""
テストデータ付きUIテスト
事前にテストユーザーとデータを作成してからUIテストを実行
"""

import os
import sys
import django
import time
import uuid
from datetime import datetime

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.character_models import CharacterSheet, CharacterSkill
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

User = get_user_model()

class UITestWithData:
    def __init__(self):
        self.driver = None
        self.test_user = None
        self.test_character = None
        
    def setup_test_data(self):
        """テストデータの作成"""
        print("テストデータ作成中...")
        
        # テストユーザー作成
        username = f'uitest_{uuid.uuid4().hex[:8]}'
        self.test_user = User.objects.create_user(
            username=username,
            password='testpass123',
            email=f'{username}@test.com',
            nickname='UIテストユーザー'
        )
        
        # テストキャラクター作成
        self.test_character = CharacterSheet.objects.create(
            user=self.test_user,
            name='UIテスト探索者',
            age=25,
            edition='6th',
            gender='男性',
            occupation='探偵',
            birthplace='東京',
            residence='横浜',
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
        
        # テストスキル追加
        CharacterSkill.objects.create(
            character_sheet=self.test_character,
            skill_name='目星',
            base_value=25,
            occupation_points=20,
            hobby_points=10,
            current_value=55
        )
        
        print(f"✅ テストユーザー作成: {username}")
        print(f"✅ テストキャラクター作成: {self.test_character.name}")
        
    def setup_driver(self):
        """WebDriverのセットアップ"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        profile_dir = f'/tmp/chrome-profile-{uuid.uuid4()}'
        options.add_argument(f'--user-data-dir={profile_dir}')
        
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def cleanup(self):
        """クリーンアップ"""
        if self.driver:
            self.driver.quit()
        
        if self.test_character:
            self.test_character.delete()
        
        if self.test_user:
            self.test_user.delete()
    
    def save_screenshot(self, name):
        """スクリーンショット保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'/tmp/ui_data_test_{name}_{timestamp}.png'
        self.driver.save_screenshot(filename)
        print(f"   📸 スクリーンショット: {filename}")
        return filename
    
    def run_tests(self):
        """UIテスト実行"""
        print("\n=== データ付きUIテスト実行 ===\n")
        
        # 1. ホームページとリダイレクト
        print("1. ホームページアクセス")
        self.driver.get('http://localhost:8000/')
        time.sleep(1)
        print(f"   現在のURL: {self.driver.current_url}")
        print(f"   タイトル: {self.driver.title}")
        self.save_screenshot('home_redirect')
        
        # 2. ログインページの構造確認
        print("\n2. ログインページ構造確認")
        page_source = self.driver.page_source
        
        # フォーム要素を探す
        form_found = False
        for selector in ['username', 'id_username', 'login', 'user']:
            elements = self.driver.find_elements(By.CSS_SELECTOR, f'input[name*="{selector}"]')
            if elements:
                print(f"   ✅ 入力フィールド発見: {elements[0].get_attribute('name')}")
                form_found = True
                break
        
        if not form_found:
            print("   ❌ ログインフォームが見つかりません")
            print("   ページに含まれるinput要素:")
            inputs = self.driver.find_elements(By.TAG_NAME, 'input')
            for inp in inputs[:5]:  # 最初の5個まで
                print(f"     - name: {inp.get_attribute('name')}, type: {inp.get_attribute('type')}")
        
        # 3. Django管理画面でのログインテスト
        print("\n3. Django管理画面ログインテスト")
        self.driver.get('http://localhost:8000/admin/')
        time.sleep(1)
        
        try:
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            
            username_field.send_keys('admin')
            password_field.send_keys('arkham_admin_2024')
            
            login_btn = self.driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
            login_btn.click()
            
            time.sleep(2)
            print(f"   ✅ 管理画面ログイン成功")
            print(f"   現在のURL: {self.driver.current_url}")
            self.save_screenshot('admin_logged_in')
            
        except Exception as e:
            print(f"   ❌ 管理画面ログイン失敗: {e}")
        
        # 4. 管理画面からキャラクター確認
        print("\n4. 管理画面でキャラクター確認")
        self.driver.get('http://localhost:8000/admin/accounts/charactersheet/')
        time.sleep(1)
        
        page_source = self.driver.page_source
        if self.test_character.name in page_source:
            print(f"   ✅ テストキャラクター確認: {self.test_character.name}")
        else:
            print("   ❌ テストキャラクターが表示されていません")
        
        self.save_screenshot('admin_character_list')
        
        # 5. APIエンドポイントテスト
        print("\n5. APIエンドポイントテスト（ブラウザ経由）")
        
        # セッションCookieを保持したままAPIアクセス
        self.driver.get('http://localhost:8000/accounts/character-sheets/')
        time.sleep(1)
        
        page_content = self.driver.find_element(By.TAG_NAME, 'body').text
        print(f"   APIレスポンス（最初の200文字）:")
        print(f"   {page_content[:200]}...")
        
        # 6. ログアウトしてフロントエンドテスト
        print("\n6. フロントエンドページテスト")
        self.driver.get('http://localhost:8000/admin/logout/')
        time.sleep(1)
        
        # キャラクター一覧（未ログイン）
        self.driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(1)
        print(f"   キャラクター一覧URL: {self.driver.current_url}")
        
        # 7. カスタムログインページ検索
        print("\n7. カスタムログインページ検索")
        login_urls = [
            '/accounts/login/',
            '/login/',
            '/auth/login/',
            '/user/login/'
        ]
        
        for url in login_urls:
            try:
                self.driver.get(f'http://localhost:8000{url}')
                time.sleep(0.5)
                if 'login' in self.driver.current_url.lower():
                    print(f"   ✅ ログインページ発見: {self.driver.current_url}")
                    self.save_screenshot(f'login_page_{url.replace("/", "_")}')
                    break
            except:
                continue
        
        # 8. JavaScriptコンソールログ確認
        print("\n8. JavaScriptコンソールエラー確認")
        logs = self.driver.get_log('browser')
        if logs:
            print("   コンソールログ:")
            for log in logs[:5]:
                print(f"   - {log['level']}: {log['message'][:100]}")
        else:
            print("   ✅ コンソールエラーなし")
        
        print("\n=== テスト完了 ===")
        

def main():
    # サーバー確認
    import requests
    try:
        requests.get('http://localhost:8000/', timeout=2)
    except:
        print("❌ 開発サーバーが起動していません")
        return
    
    tester = UITestWithData()
    
    try:
        tester.setup_test_data()
        tester.setup_driver()
        tester.run_tests()
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.cleanup()
        print("\n✅ クリーンアップ完了")


if __name__ == '__main__':
    main()