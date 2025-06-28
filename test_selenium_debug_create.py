#!/usr/bin/env python3
"""
キャラクター作成ページのデバッグスクリプト
"""

import os
import sys
import time
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_character_create_page():
    """キャラクター作成ページの構造を調査"""
    
    print("=== キャラクター作成ページデバッグ ===\n")
    
    # Chrome オプションの設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # ユニークなプロファイルディレクトリ
    unique_id = str(uuid.uuid4())
    profile_dir = f'/tmp/chrome-profile-{unique_id}'
    options.add_argument(f'--user-data-dir={profile_dir}')
    
    driver = None
    try:
        # ChromeDriver サービス
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)
        print("✅ WebDriver 初期化成功\n")
        
        # 1. 開発用ログインページへアクセス
        print("=== ログイン ===")
        driver.get('http://localhost:8000/accounts/dev-login/')
        time.sleep(2)
        
        # investigator1でログイン
        try:
            login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
            for card in login_cards:
                if 'investigator1' in card.text:
                    login_btn = card.find_element(By.CLASS_NAME, 'login-btn')
                    login_btn.click()
                    break
            
            time.sleep(2)
            print("✅ ログイン成功")
        except Exception as e:
            print(f"❌ ログインエラー: {e}")
        
        # 2. キャラクター作成ページへ移動
        print("\n=== キャラクター作成ページへ移動 ===")
        driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(3)
        
        # ページ情報
        print(f"\n現在のURL: {driver.current_url}")
        print(f"ページタイトル: {driver.title}")
        
        # ページソースの一部を確認
        page_source = driver.page_source
        print(f"\nページソース長: {len(page_source)} 文字")
        
        # エラーメッセージの確認
        try:
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            if alerts:
                print("\n=== アラートメッセージ ===")
                for alert in alerts:
                    print(f"- {alert.text}")
        except:
            pass
        
        # フォーム要素の確認
        print("\n=== フォーム要素の確認 ===")
        
        # formタグの確認
        forms = driver.find_elements(By.TAG_NAME, 'form')
        print(f"フォーム数: {len(forms)}")
        
        # input要素の確認
        inputs = driver.find_elements(By.TAG_NAME, 'input')
        print(f"\ninput要素数: {len(inputs)}")
        
        # 最初の10個のinput要素を表示
        print("\n最初の10個のinput要素:")
        for i, input_elem in enumerate(inputs[:10]):
            try:
                input_id = input_elem.get_attribute('id')
                input_name = input_elem.get_attribute('name')
                input_type = input_elem.get_attribute('type')
                print(f"  {i+1}. id='{input_id}', name='{input_name}', type='{input_type}'")
            except:
                pass
        
        # タブの確認
        print("\n=== タブ構造の確認 ===")
        nav_tabs = driver.find_elements(By.CSS_SELECTOR, '.nav-tabs .nav-link')
        print(f"タブ数: {len(nav_tabs)}")
        for tab in nav_tabs:
            print(f"  - {tab.text}")
        
        # ボタンの確認
        print("\n=== ボタンの確認 ===")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        print(f"ボタン数: {len(buttons)}")
        for button in buttons:
            button_text = button.text
            button_type = button.get_attribute('type')
            if button_text:
                print(f"  - '{button_text}' (type={button_type})")
        
        # JavaScriptエラーの確認
        print("\n=== JavaScriptエラーの確認 ===")
        logs = driver.get_log('browser')
        if logs:
            for log in logs:
                if log['level'] == 'SEVERE':
                    print(f"  ERROR: {log['message']}")
        else:
            print("  JavaScriptエラーなし")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_debug_create_page.png'
        driver.save_screenshot(screenshot_path)
        print(f"\nスクリーンショット保存: {screenshot_path}")
        
        # ページソースを保存
        with open('/tmp/selenium_page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("ページソース保存: /tmp/selenium_page_source.html")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            print("\n✅ WebDriver を正常に終了しました")
        
        # クリーンアップ
        if os.path.exists(profile_dir):
            import shutil
            try:
                shutil.rmtree(profile_dir)
            except:
                pass

if __name__ == '__main__':
    # 開発サーバーが起動しているか確認
    import requests
    try:
        response = requests.get('http://localhost:8000/', timeout=2)
        print("✅ 開発サーバーが起動しています\n")
        debug_character_create_page()
    except:
        print("❌ 開発サーバーが起動していません")
        sys.exit(1)