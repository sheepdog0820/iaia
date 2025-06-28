#!/usr/bin/env python3
"""
必須フィールドチェックスクリプト
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
import django
django.setup()

def check_required_fields():
    """必須フィールドの確認"""
    # Chrome オプション設定
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # ChromeDriver
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # 開発用ログイン
        print("1. 開発用ログイン")
        driver.get("http://localhost:8000/accounts/dev-login/")
        time.sleep(2)
        
        # investigator1でログイン
        user_cards = driver.find_elements(By.CLASS_NAME, "user-card")
        for card in user_cards:
            if "investigator1" in card.text:
                login_button = card.find_element(By.CLASS_NAME, "login-btn")
                login_button.click()
                break
        
        time.sleep(2)
        
        # キャラクター作成ページへ
        print("\n2. キャラクター作成ページへ移動")
        driver.get("http://localhost:8000/accounts/character/create/6th/")
        time.sleep(2)
        
        # 必須フィールドを確認
        print("\n3. 必須フィールドの確認")
        print("=" * 60)
        
        # required属性を持つフィールドを探す
        required_fields = driver.find_elements(By.CSS_SELECTOR, "[required]")
        print(f"\nrequired属性を持つフィールド: {len(required_fields)}個")
        for field in required_fields:
            field_name = field.get_attribute("name")
            field_id = field.get_attribute("id")
            field_type = field.get_attribute("type")
            print(f"  - name={field_name}, id={field_id}, type={field_type}")
        
        # .requiredクラスを持つラベルを探す
        required_labels = driver.find_elements(By.CSS_SELECTOR, ".required")
        print(f"\n.requiredクラスを持つラベル: {len(required_labels)}個")
        for label in required_labels:
            print(f"  - {label.text}")
        
        # 最小限のデータで送信を試みる
        print("\n4. 最小限のデータで送信テスト")
        print("=" * 60)
        
        # 名前だけ入力
        name_field = driver.find_element(By.NAME, "name")
        name_field.send_keys("テストキャラクター")
        
        # 送信ボタンをクリック
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", submit_button)
        
        # エラーメッセージを待つ
        time.sleep(2)
        
        # バリデーションエラーの確認
        print("\n5. バリデーションエラーの確認")
        
        # ブラウザのHTML5バリデーションメッセージ
        invalid_fields = driver.find_elements(By.CSS_SELECTOR, ":invalid")
        print(f"\n無効なフィールド: {len(invalid_fields)}個")
        for field in invalid_fields:
            field_name = field.get_attribute("name")
            validation_msg = field.get_attribute("validationMessage")
            if field_name:
                print(f"  - {field_name}: {validation_msg}")
        
        # カスタムエラーメッセージ
        error_messages = driver.find_elements(By.CLASS_NAME, "error-message")
        if error_messages:
            print("\nカスタムエラーメッセージ:")
            for msg in error_messages:
                if msg.is_displayed():
                    print(f"  - {msg.text}")
        
        # フォームのアクション確認
        form = driver.find_element(By.TAG_NAME, "form")
        print(f"\nフォームのアクション: {form.get_attribute('action')}")
        print(f"フォームのメソッド: {form.get_attribute('method')}")
        
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == '__main__':
    print("必須フィールドチェックスクリプト")
    print("=" * 60)
    check_required_fields()