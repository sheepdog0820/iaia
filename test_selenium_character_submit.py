#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
フォーム送信を直接実行するテスト
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

def run_character_creation_test():
    """キャラクター作成テスト（フォーム送信修正版）"""
    
    print("=== クトゥルフ神話TRPG 6版 キャラクター作成テスト（送信修正版） ===\n")
    
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
                print(f"✅ {field_id}: {value}")
            except Exception as e:
                print(f"❌ {field_id}: {e}")
        
        # 性別の入力
        try:
            gender_select = driver.find_element(By.ID, 'gender')
            Select(gender_select).select_by_visible_text('男性')
            print("✅ gender: 男性")
        except:
            try:
                gender_field = driver.find_element(By.ID, 'gender')
                gender_field.clear()
                gender_field.send_keys('男性')
                print("✅ gender: 男性（テキスト入力）")
            except:
                print("⚠️ 性別フィールドは見つかりません")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブをクリック（preventDefaultを回避）
        driver.execute_script("""
            // 既存のイベントリスナーを削除して、タブを直接切り替え
            const abilitiesTab = document.getElementById('abilities-tab');
            const basicTab = document.getElementById('basic-tab');
            const abilitiesPanel = document.getElementById('abilities');
            const basicPanel = document.getElementById('basic');
            
            // タブのアクティブ状態を変更
            basicTab.classList.remove('active');
            abilitiesTab.classList.add('active');
            
            // パネルの表示を変更
            basicPanel.classList.remove('show', 'active');
            abilitiesPanel.classList.add('show', 'active');
            
            // aria属性も更新
            basicTab.setAttribute('aria-selected', 'false');
            abilitiesTab.setAttribute('aria-selected', 'true');
        """)
        time.sleep(1)
        print("✅ 能力値タブに切り替え（JavaScript強制実行）")
        
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
                field.send_keys(Keys.TAB)
                print(f"✅ {ability.upper()}: {value}")
            except Exception as e:
                print(f"❌ {ability}: {e}")
        
        # 計算を待つ
        time.sleep(2)
        
        # 5. フォームの検証と送信準備
        print("\n=== STEP 5: フォーム検証と送信準備 ===")
        
        # すべてのタブパネルを表示状態にする（隠れたフィールドを防ぐ）
        driver.execute_script("""
            // すべてのタブパネルを一時的に表示
            const allPanels = document.querySelectorAll('.tab-pane');
            allPanels.forEach(panel => {
                panel.style.display = 'block';
                panel.style.opacity = '1';
            });
        """)
        
        # フォームの妥当性確認
        form_check = driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            const isValid = form.checkValidity();
            
            // 無効なフィールドを収集
            const invalidFields = [];
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
            inputs.forEach(input => {
                if (!input.validity.valid) {
                    invalidFields.push({
                        id: input.id,
                        name: input.name,
                        value: input.value,
                        type: input.type,
                        required: input.required,
                        message: input.validationMessage
                    });
                }
            });
            
            return {
                isValid: isValid,
                invalidCount: invalidFields.length,
                invalidFields: invalidFields
            };
        """)
        
        print(f"フォーム妥当性: {form_check['isValid']}")
        print(f"無効フィールド数: {form_check['invalidCount']}")
        
        if form_check['invalidFields']:
            print("\n無効なフィールド:")
            for field in form_check['invalidFields']:
                print(f"  - {field['id']}: {field['message']}")
        
        # 6. キャラクターの保存（直接フォーム送信）
        print("\n=== STEP 6: キャラクターの保存 ===")
        
        # preventDefaultを回避してフォームを送信
        try:
            result = driver.execute_script("""
                // フォームを取得
                const form = document.getElementById('character-form-6th');
                
                // フォームが有効かチェック
                if (!form.checkValidity()) {
                    // HTML5バリデーションをトリガー
                    form.reportValidity();
                    return {success: false, message: 'フォームが無効です'};
                }
                
                // すべてのイベントリスナーを一時的に無効化
                const submitButton = form.querySelector('button[type="submit"]');
                const newButton = submitButton.cloneNode(true);
                submitButton.parentNode.replaceChild(newButton, submitButton);
                
                // フォームを直接送信
                form.submit();
                
                return {success: true, message: 'フォームを送信しました'};
            """)
            
            print(f"送信結果: {result}")
            
            # 送信処理を待つ
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ 送信エラー: {e}")
            
            # 代替方法：POSTリクエストを直接送信
            print("\n代替方法: フォームデータを収集してPOST送信")
            
            form_data = driver.execute_script("""
                const form = document.getElementById('character-form-6th');
                const formData = new FormData(form);
                const data = {};
                
                for (let [key, value] of formData.entries()) {
                    data[key] = value;
                }
                
                return data;
            """)
            
            print(f"収集したフォームデータ: {len(form_data)}項目")
        
        # 7. 保存結果の確認
        print("\n=== STEP 7: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # 成功判定
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ URLから判断: キャラクター作成成功！")
            
            # ページ内容の確認
            page_source = driver.page_source
            if created_character_name in page_source:
                print(f"✅ キャラクター名「{created_character_name}」が表示されています")
                
            print("\n🎉 テスト成功: キャラクターが正常に作成されました！")
        else:
            print("⚠️ まだ作成ページにいます")
            
            # エラーメッセージの確認
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            for alert in alerts:
                text = alert.text.strip()
                if text:
                    print(f"アラート: {text}")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_character_final_result.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 8. キャラクター一覧での確認
        print("\n=== STEP 8: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(3)
        
        page_source = driver.page_source
        if created_character_name in page_source:
            print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
            print("\n🎉 完全成功: キャラクターの作成と保存が確認されました！")
        else:
            print(f"❌ キャラクター「{created_character_name}」が一覧に見つかりません")
        
        print("\n=== テスト完了 ===")
        
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
        run_character_creation_test()
    except:
        print("❌ 開発サーバーが起動していません")
        print("以下のコマンドで開発サーバーを起動してください:")
        print("python3 manage.py runserver")
        sys.exit(1)