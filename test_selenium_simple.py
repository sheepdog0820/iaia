#!/usr/bin/env python3
"""
最小限のSeleniumテスト - セッション競合を回避
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import uuid

print("=== 最小限のSelenium テスト ===\n")

# Chrome オプションの設定
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

# ランダムなプロファイルディレクトリを使用
unique_id = str(uuid.uuid4())
profile_dir = f'/tmp/chrome-profile-{unique_id}'
options.add_argument(f'--user-data-dir={profile_dir}')

# その他のオプション
options.add_argument('--disable-extensions')
options.add_argument('--disable-plugins')
options.add_argument('--single-process')
options.add_argument('--disable-background-timer-throttling')
options.add_argument('--disable-backgrounding-occluded-windows')
options.add_argument('--disable-renderer-backgrounding')

print(f"プロファイルディレクトリ: {profile_dir}")

try:
    # ChromeDriverの直接指定
    service = Service('/usr/bin/chromedriver')
    
    print("WebDriver を初期化中...")
    driver = webdriver.Chrome(service=service, options=options)
    
    print("✅ WebDriver 初期化成功!")
    
    # Googleにアクセス
    driver.get('https://www.google.com')
    print(f"✅ ページタイトル: {driver.title}")
    
    # ブラウザを閉じる
    driver.quit()
    print("✅ テスト完了!")
    
except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
finally:
    # クリーンアップ
    if os.path.exists(profile_dir):
        import shutil
        try:
            shutil.rmtree(profile_dir)
            print(f"✅ プロファイルディレクトリを削除: {profile_dir}")
        except:
            pass