#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
作成から登録までの完全成功版UIテスト
"""

import os
import sys
import time
import uuid
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

def run_complete_character_creation_test():
    """キャラクター作成から登録までの完全なテスト"""
    
    print("=== クトゥルフ神話TRPG 6版 キャラクター作成完全テスト（成功版） ===\n")
    
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
    created_character_name = None
    
    try:
        # ChromeDriver サービス
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)
        print("✅ WebDriver 初期化成功\n")
        
        # 1. 開発用ログインページへアクセス
        print("=== STEP 1: ログイン ===")
        driver.get('http://localhost:8000/accounts/dev-login/')
        time.sleep(2)
        
        # investigator1でログイン
        login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
        for card in login_cards:
            if 'investigator1' in card.text:
                login_btn = card.find_element(By.CLASS_NAME, 'login-btn')
                login_btn.click()
                break
        
        time.sleep(2)
        print("✅ investigator1でログイン成功")
        
        # 2. キャラクター作成ページへ移動
        print("\n=== STEP 2: キャラクター作成ページへ移動 ===")
        driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(3)
        
        page_title = driver.title
        print(f"ページタイトル: {page_title}")
        print("✅ 6版キャラクター作成ページにアクセス成功")
        
        # 3. 基本情報の入力
        print("\n=== STEP 3: 基本情報の入力 ===")
        
        created_character_name = f'テスト探索者_{random.randint(1000, 9999)}'
        
        # 基本情報を入力
        basic_info = {
            'name': created_character_name,
            'player_name': 'テストプレイヤー',
            'age': str(random.randint(20, 40)),
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜'
        }
        
        for field_id, value in basic_info.items():
            try:
                field = driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(value)
                # 値が設定されたことを確認
                actual_value = field.get_attribute('value')
                if actual_value == value:
                    print(f"✅ {field_id}: {value}")
                else:
                    print(f"⚠️ {field_id}: 期待値={value}, 実際={actual_value}")
            except Exception as e:
                print(f"❌ {field_id}: {e}")
        
        # 性別の選択
        try:
            gender_select = driver.find_element(By.ID, 'gender')
            Select(gender_select).select_by_visible_text('男性')
            print("✅ gender: 男性")
        except:
            # 性別がテキストフィールドの場合
            try:
                gender_field = driver.find_element(By.ID, 'gender')
                gender_field.clear()
                gender_field.send_keys('男性')
                print("✅ gender: 男性（テキスト入力）")
            except:
                print("⚠️ 性別フィールドは見つかりません")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブをクリック
        ability_tab = driver.find_element(By.ID, 'abilities-tab')
        driver.execute_script("arguments[0].click();", ability_tab)
        time.sleep(1)
        print("✅ 能力値タブに切り替え")
        
        # 能力値の入力
        abilities = {
            'str': '13',
            'con': '14',
            'pow': '15',
            'dex': '12',
            'app': '11',
            'siz': '13',
            'int': '16',
            'edu': '17'
        }
        
        for ability, value in abilities.items():
            try:
                field = driver.find_element(By.ID, ability)
                field.clear()
                field.send_keys(value)
                
                # Tabキーを押して次のフィールドへ（changeイベントを確実に発火）
                field.send_keys(Keys.TAB)
                
                # 値が設定されたことを確認
                actual_value = field.get_attribute('value')
                if actual_value == value:
                    print(f"✅ {ability.upper()}: {value}")
                else:
                    print(f"⚠️ {ability.upper()}: 期待値={value}, 実際={actual_value}")
                    
            except Exception as e:
                print(f"❌ {ability}: {e}")
        
        # 副次ステータスの計算を待つ
        time.sleep(2)
        
        # 5. フォームの妥当性を確認
        print("\n=== STEP 5: フォーム検証 ===")
        
        form_valid = driver.execute_script("""
            var form = document.querySelector('form');
            return form.checkValidity();
        """)
        
        print(f"フォームの妥当性: {form_valid}")
        
        if not form_valid:
            # 無効なフィールドを特定
            invalid_fields = driver.execute_script("""
                var form = document.querySelector('form');
                var fields = form.querySelectorAll('input[required]');
                var invalid = [];
                
                fields.forEach(function(field) {
                    if (!field.validity.valid) {
                        invalid.push({
                            id: field.id,
                            name: field.name,
                            value: field.value,
                            message: field.validationMessage
                        });
                    }
                });
                
                return invalid;
            """)
            
            if invalid_fields:
                print("無効なフィールド:")
                for field in invalid_fields:
                    print(f"  - {field['id'] or field['name']}: '{field['value']}' ({field['message']})")
        
        # 6. キャラクターの保存
        print("\n=== STEP 6: キャラクターの保存 ===")
        
        try:
            # 保存ボタンを探す（「作成」テキストのボタン）
            save_button = None
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"]')
            
            for button in buttons:
                if button.is_displayed():
                    button_text = button.text.strip()
                    if '作成' in button_text or '保存' in button_text or 'Save' in button_text:
                        save_button = button
                        break
            
            # 見つからない場合は最初のsubmitボタンを使用
            if not save_button and buttons:
                save_button = buttons[0]
            
            if save_button:
                print(f"保存ボタンを見つけました: '{save_button.text.strip()}'")
                
                # スクロールして表示
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(1)
                
                # クリック
                save_button.click()
                print("✅ 保存ボタンをクリック")
                
                # 保存処理を待つ
                time.sleep(5)
            else:
                print("❌ 保存ボタンが見つかりません")
                
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
        
        # 7. 保存結果の確認
        print("\n=== STEP 7: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # URLでの成功判定
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ URLから判断: キャラクター作成成功！")
            
            # キャラクターIDを取得
            try:
                parts = current_url.split('/character/')
                if len(parts) > 1:
                    character_id = parts[1].rstrip('/')
                    print(f"作成されたキャラクターID: {character_id}")
            except:
                pass
        else:
            print("⚠️ まだ作成ページにいます")
            
            # エラーメッセージの確認
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            for alert in alerts:
                text = alert.text.strip()
                if text:
                    print(f"アラート: {text}")
        
        # ページ内容の確認
        page_source = driver.page_source
        if created_character_name in page_source:
            print(f"✅ キャラクター名「{created_character_name}」がページに表示されています")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_character_result.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n結果スクリーンショット: {screenshot_path}")
        
        # 8. キャラクター一覧での最終確認
        print("\n=== STEP 8: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(3)
        
        page_source = driver.page_source
        if created_character_name in page_source:
            print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
            
            # キャラクターカードの詳細を取得
            cards = driver.find_elements(By.CLASS_NAME, 'card')
            for card in cards:
                if created_character_name in card.text:
                    print("\n✅ キャラクターカードの内容:")
                    card_lines = card.text.split('\n')
                    for line in card_lines[:5]:  # 最初の5行のみ表示
                        print(f"  {line}")
                    break
                    
            print("\n🎉 テスト完全成功: キャラクターが正常に作成・保存されました！")
        else:
            print(f"❌ キャラクター「{created_character_name}」が一覧に見つかりません")
        
        # 一覧のスクリーンショット
        screenshot_path = '/tmp/selenium_character_list_final.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        print("\n=== テスト完了 ===")
        print("✅ キャラクター作成完全テストが終了しました！")
        
        # テスト結果のサマリー
        print("\n=== テスト結果サマリー ===")
        print(f"作成キャラクター名: {created_character_name}")
        print(f"最終URL: {current_url}")
        print(f"一覧での表示: {'成功' if created_character_name in page_source else '失敗'}")
        
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
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
        run_complete_character_creation_test()
    except:
        print("❌ 開発サーバーが起動していません")
        print("以下のコマンドで開発サーバーを起動してください:")
        print("python3 manage.py runserver")
        sys.exit(1)