#!/usr/bin/env python3
"""
Selenium デバッグ用スクリプト
フォームフィールドの確認
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

def debug_form_fields():
    """フォームフィールドのデバッグ"""
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
        
        # フォームフィールドを調査
        print("\n3. フォームフィールドの調査")
        print("=" * 60)
        
        # input要素を全て取得
        print("\n[INPUT要素]")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for idx, input_elem in enumerate(inputs):
            input_type = input_elem.get_attribute("type")
            input_name = input_elem.get_attribute("name")
            input_id = input_elem.get_attribute("id")
            if input_name:  # name属性がある場合のみ表示
                print(f"{idx}: type={input_type}, name={input_name}, id={input_id}")
        
        # textarea要素
        print("\n[TEXTAREA要素]")
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        for idx, textarea in enumerate(textareas):
            textarea_name = textarea.get_attribute("name")
            textarea_id = textarea.get_attribute("id")
            print(f"{idx}: name={textarea_name}, id={textarea_id}")
        
        # select要素
        print("\n[SELECT要素]")
        selects = driver.find_elements(By.TAG_NAME, "select")
        for idx, select in enumerate(selects):
            select_name = select.get_attribute("name")
            select_id = select.get_attribute("id")
            print(f"{idx}: name={select_name}, id={select_id}")
        
        # 特定のフィールドを探す
        print("\n[特定フィールドの存在確認]")
        test_fields = [
            "character_name", "name", "player_name",
            "age", "occupation", "birthplace",
            "str", "con", "pow", "dex", "app", "siz", "int", "edu"
        ]
        
        for field_name in test_fields:
            try:
                # NAMEで探す
                by_name = driver.find_elements(By.NAME, field_name)
                if by_name:
                    print(f"✓ name='{field_name}' → {len(by_name)}個見つかりました")
                
                # IDで探す
                by_id = driver.find_elements(By.ID, field_name)
                if by_id:
                    print(f"✓ id='{field_name}' → {len(by_id)}個見つかりました")
            except:
                pass
        
        # フォームの構造確認
        print("\n[フォーム構造]")
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"フォーム数: {len(forms)}")
        
        if forms:
            form = forms[0]
            print(f"フォームaction: {form.get_attribute('action')}")
            print(f"フォームmethod: {form.get_attribute('method')}")
        
        # ボタン確認
        print("\n[送信ボタン]")
        submit_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        print(f"送信ボタン数: {len(submit_buttons)}")
        for idx, btn in enumerate(submit_buttons):
            print(f"{idx}: text='{btn.text}', class='{btn.get_attribute('class')}'")
        
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == '__main__':
    print("Seleniumデバッグスクリプト")
    print("=" * 60)
    debug_form_fields()