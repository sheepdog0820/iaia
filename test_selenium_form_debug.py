#!/usr/bin/env python3
"""
フォーム値の確認デバッグスクリプト
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

def debug_form_values():
    """フォームの値を確認"""
    
    print("=== フォーム値確認デバッグ ===\n")
    
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
        
        # 1. ログイン
        driver.get('http://localhost:8000/accounts/dev-login/')
        time.sleep(2)
        
        login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
        for card in login_cards:
            if 'investigator1' in card.text:
                login_btn = card.find_element(By.CLASS_NAME, 'login-btn')
                login_btn.click()
                break
        
        time.sleep(2)
        print("✅ ログイン完了\n")
        
        # 2. キャラクター作成ページ
        driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(3)
        
        # 3. 基本情報を入力（通常の方法）
        print("=== 基本情報入力（通常の方法） ===")
        
        test_data = {
            'name': 'テスト太郎',
            'age': '25',
            'occupation': '探偵'
        }
        
        for field_id, value in test_data.items():
            try:
                field = driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(value)
                
                # 入力後の値を確認
                actual_value = field.get_attribute('value')
                validity = driver.execute_script("return arguments[0].validity.valid;", field)
                print(f"{field_id}: 入力値='{value}', 実際の値='{actual_value}', 有効={validity}")
            except Exception as e:
                print(f"{field_id}: エラー - {e}")
        
        # 4. 能力値タブに切り替え
        print("\n=== 能力値タブへ切り替え ===")
        
        ability_tab = driver.find_element(By.ID, 'abilities-tab')
        driver.execute_script("arguments[0].click();", ability_tab)
        time.sleep(1)
        
        # 5. 能力値を入力（JavaScriptで）
        print("\n=== 能力値入力（JavaScript） ===")
        
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        
        for ability in abilities:
            try:
                # JavaScriptで値を設定
                result = driver.execute_script(f"""
                    var element = document.getElementById('{ability}');
                    if (element) {{
                        element.value = '10';
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        return {{
                            value: element.value,
                            valid: element.validity.valid,
                            required: element.hasAttribute('required'),
                            disabled: element.disabled,
                            readonly: element.readOnly,
                            type: element.type,
                            validationMessage: element.validationMessage
                        }};
                    }}
                    return null;
                """)
                
                if result:
                    print(f"{ability}: {result}")
                else:
                    print(f"{ability}: 要素が見つかりません")
                    
            except Exception as e:
                print(f"{ability}: エラー - {e}")
        
        # 6. フォーム全体の状態を確認
        print("\n=== フォーム全体の検証状態 ===")
        
        form_state = driver.execute_script("""
            var form = document.querySelector('form');
            var requiredFields = form.querySelectorAll('[required]');
            var invalidFields = [];
            var validFields = [];
            
            requiredFields.forEach(function(field) {
                var info = {
                    id: field.id,
                    name: field.name,
                    value: field.value,
                    valid: field.validity.valid,
                    message: field.validationMessage
                };
                
                if (field.validity.valid) {
                    validFields.push(info);
                } else {
                    invalidFields.push(info);
                }
            });
            
            return {
                formValid: form.checkValidity(),
                totalRequired: requiredFields.length,
                validCount: validFields.length,
                invalidCount: invalidFields.length,
                invalidFields: invalidFields,
                validFields: validFields
            };
        """)
        
        print(f"フォーム全体の妥当性: {form_state['formValid']}")
        print(f"必須フィールド総数: {form_state['totalRequired']}")
        print(f"有効なフィールド数: {form_state['validCount']}")
        print(f"無効なフィールド数: {form_state['invalidCount']}")
        
        if form_state['invalidFields']:
            print("\n無効なフィールド:")
            for field in form_state['invalidFields']:
                print(f"  - {field['id'] or field['name']}: '{field['value']}' ({field['message']})")
        
        # 7. 保存ボタンの確認
        print("\n=== 保存ボタンの確認 ===")
        
        save_buttons = driver.execute_script("""
            var buttons = document.querySelectorAll('button[type="submit"]');
            var buttonInfo = [];
            
            buttons.forEach(function(btn, index) {
                buttonInfo.push({
                    index: index,
                    text: btn.textContent.trim(),
                    visible: btn.offsetParent !== null,
                    disabled: btn.disabled,
                    classes: btn.className
                });
            });
            
            return buttonInfo;
        """)
        
        print(f"保存ボタン数: {len(save_buttons)}")
        for btn in save_buttons:
            print(f"  ボタン{btn['index']}: '{btn['text']}' (表示={btn['visible']}, 無効={btn['disabled']})")
        
        # 8. スクリーンショット
        screenshot_path = '/tmp/selenium_form_debug.png'
        driver.save_screenshot(screenshot_path)
        print(f"\nスクリーンショット: {screenshot_path}")
        
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
        debug_form_values()
    except:
        print("❌ 開発サーバーが起動していません")
        sys.exit(1)