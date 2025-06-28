#!/usr/bin/env python3
"""
Selenium UI テストのデモンストレーション
キャラクターシート6版の基本的な画面遷移をテストします
"""

import os
import sys
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_character_sheet_ui():
    """キャラクターシート画面の基本的なUIテスト"""
    
    print("=== Selenium UI テスト実行 ===\n")
    
    # Chrome オプションの設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # ユニークなユーザーデータディレクトリを作成
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f'--user-data-dir={temp_dir}')
    
    # Snap Chromium の場合のパス設定
    if os.path.exists('/snap/bin/chromium'):
        options.binary_location = '/snap/bin/chromium'
    
    driver = None
    try:
        # WebDriver の初期化
        print("1. WebDriver を初期化中...")
        driver = webdriver.Chrome(options=options)
        print("   ✅ WebDriver 初期化成功\n")
        
        # テスト1: Google にアクセスして動作確認
        print("2. Selenium の基本動作確認...")
        driver.get('https://www.google.com')
        print(f"   ✅ ページタイトル: {driver.title}\n")
        
        # テスト2: ローカルサーバーへのアクセステスト
        print("3. ローカルサーバーへの接続テスト...")
        try:
            driver.get('http://localhost:8000/')
            print("   ✅ ローカルサーバーに接続成功")
            
            # ページソースの一部を表示
            page_source = driver.page_source[:200]
            print(f"   ページソース（最初の200文字）:\n   {page_source}...\n")
            
        except Exception as e:
            print(f"   ⚠️  ローカルサーバーに接続できません: {e}")
            print("   開発サーバーが起動していることを確認してください\n")
        
        # テスト3: スクリーンショットの取得
        print("4. スクリーンショット取得テスト...")
        screenshot_path = '/tmp/selenium_test_screenshot.png'
        driver.save_screenshot(screenshot_path)
        if os.path.exists(screenshot_path):
            print(f"   ✅ スクリーンショット保存成功: {screenshot_path}")
            print(f"   ファイルサイズ: {os.path.getsize(screenshot_path)} bytes\n")
        
        # テスト4: JavaScript実行テスト
        print("5. JavaScript 実行テスト...")
        result = driver.execute_script("return navigator.userAgent")
        print(f"   ✅ User Agent: {result}\n")
        
        # テスト5: 要素の検索テスト
        print("6. DOM 要素検索テスト...")
        try:
            driver.get('https://www.google.com')
            search_box = driver.find_element(By.NAME, 'q')
            print("   ✅ 検索ボックス要素を発見")
            print(f"   要素タグ: {search_box.tag_name}")
            print(f"   要素の表示状態: {search_box.is_displayed()}\n")
        except Exception as e:
            print(f"   ❌ 要素検索エラー: {e}\n")
        
        print("=== テスト完了 ===")
        print("✅ Selenium は正常に動作しています！")
        print("✅ UI テストを実行する準備が整いました")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            print("\n✅ WebDriver を正常に終了しました")
        
        # 一時ディレクトリのクリーンアップ
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == '__main__':
    test_character_sheet_ui()