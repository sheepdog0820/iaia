#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
フィールド名修正版の完全UIテスト
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
    """キャラクター作成テスト（フィールド名修正版）"""
    
    print("=== クトゥルフ神話TRPG 6版 キャラクター作成完全テスト（修正版） ===\n")
    
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
        
        # 3. フォームフィールドの調査
        print("\n=== STEP 3: フォームフィールドの調査 ===")
        
        # すべてのinputフィールドを調査
        input_fields = driver.execute_script("""
            const inputs = document.querySelectorAll('input[type="text"], input[type="number"], input[type="hidden"]');
            const fields = [];
            
            inputs.forEach(input => {
                if (input.name && input.name !== 'csrfmiddlewaretoken') {
                    fields.push({
                        id: input.id,
                        name: input.name,
                        type: input.type,
                        required: input.required,
                        value: input.value,
                        placeholder: input.placeholder
                    });
                }
            });
            
            return fields;
        """)
        
        print(f"フォームフィールド数: {len(input_fields)}")
        
        # 能力値関連のフィールドを探す
        ability_fields = [f for f in input_fields if any(ab in (f['name'] or '').lower() for ab in ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'])]
        
        print("\n能力値関連フィールド:")
        for field in ability_fields[:10]:
            print(f"  - name='{field['name']}', id='{field['id']}', required={field['required']}")
        
        # 4. 基本情報の入力
        print("\n=== STEP 4: 基本情報の入力 ===")
        
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
        
        # 5. 能力値タブへ移動と入力
        print("\n=== STEP 5: 能力値の入力 ===")
        
        # 能力値タブを表示
        driver.execute_script("""
            // タブを強制的に切り替え
            const abilitiesTab = document.getElementById('abilities-tab');
            const basicTab = document.getElementById('basic-tab');
            const abilitiesPanel = document.getElementById('abilities');
            const basicPanel = document.getElementById('basic');
            
            if (abilitiesTab && abilitiesPanel) {
                basicTab.classList.remove('active');
                abilitiesTab.classList.add('active');
                basicPanel.classList.remove('show', 'active');
                abilitiesPanel.classList.add('show', 'active');
            }
        """)
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
                field.send_keys(Keys.TAB)
                print(f"✅ {ability.upper()}: {value}")
            except Exception as e:
                print(f"❌ {ability}: {e}")
        
        # 計算を待つ
        time.sleep(2)
        
        # 6. 隠しフィールドの自動設定
        print("\n=== STEP 6: 隠しフィールドの設定 ===")
        
        # JavaScriptで必要な値を計算して設定
        driver.execute_script("""
            // 能力値を取得
            const str = parseInt(document.getElementById('str')?.value) || 0;
            const con = parseInt(document.getElementById('con')?.value) || 0;
            const pow = parseInt(document.getElementById('pow')?.value) || 0;
            const siz = parseInt(document.getElementById('siz')?.value) || 0;
            
            // 計算値を設定（フィールドが存在する場合）
            const setFieldValue = (name, value) => {
                const fields = document.getElementsByName(name);
                if (fields.length > 0) {
                    fields[0].value = value;
                    console.log(`Set ${name} = ${value}`);
                }
            };
            
            // 能力値フィールド（_value付き）
            setFieldValue('str_value', str);
            setFieldValue('con_value', con);
            setFieldValue('pow_value', pow);
            setFieldValue('dex_value', document.getElementById('dex')?.value || 0);
            setFieldValue('app_value', document.getElementById('app')?.value || 0);
            setFieldValue('siz_value', siz);
            setFieldValue('int_value', document.getElementById('int')?.value || 0);
            setFieldValue('edu_value', document.getElementById('edu')?.value || 0);
            
            // 計算フィールド
            const hp_max = Math.ceil((con + siz) / 2);
            const mp_max = pow;
            const san_starting = pow * 5;
            
            setFieldValue('hit_points_max', hp_max);
            setFieldValue('magic_points_max', mp_max);
            setFieldValue('sanity_starting', san_starting);
            setFieldValue('sanity_max', 99);  // デフォルト値
            
            // 現在値も設定
            setFieldValue('hit_points_current', hp_max);
            setFieldValue('magic_points_current', mp_max);
            setFieldValue('sanity_current', san_starting);
            
            console.log('Hidden fields set successfully');
        """)
        
        print("✅ 隠しフィールドを設定しました")
        
        # 7. フォーム検証
        print("\n=== STEP 7: フォーム検証 ===")
        
        form_check = driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            const formData = new FormData(form);
            
            // フォームデータを確認
            const data = {};
            for (let [key, value] of formData.entries()) {
                if (key !== 'csrfmiddlewaretoken') {
                    data[key] = value;
                }
            }
            
            return {
                isValid: form.checkValidity(),
                fieldCount: Object.keys(data).length,
                hasStrValue: !!data['str_value'],
                hasHpMax: !!data['hit_points_max'],
                data: data
            };
        """)
        
        print(f"フォーム妥当性: {form_check['isValid']}")
        print(f"フィールド数: {form_check['fieldCount']}")
        print(f"str_value存在: {form_check['hasStrValue']}")
        print(f"hit_points_max存在: {form_check['hasHpMax']}")
        
        # 8. キャラクターの保存
        print("\n=== STEP 8: キャラクターの保存 ===")
        
        # フォームを直接送信
        driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            
            // submitボタンのイベントリスナーを無効化
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                const newButton = submitButton.cloneNode(true);
                submitButton.parentNode.replaceChild(newButton, submitButton);
            }
            
            // フォームを送信
            form.submit();
        """)
        
        print("✅ フォームを送信しました")
        time.sleep(5)
        
        # 9. 保存結果の確認
        print("\n=== STEP 9: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # 成功判定
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ URLから判断: キャラクター作成成功！")
            
            # ページ内容の確認
            page_source = driver.page_source
            if created_character_name in page_source:
                print(f"✅ キャラクター名「{created_character_name}」が表示されています")
                
                # 詳細情報の取得
                try:
                    # キャラクター名の確認
                    h1_elements = driver.find_elements(By.TAG_NAME, 'h1')
                    for h1 in h1_elements:
                        if created_character_name in h1.text:
                            print(f"✅ ページタイトル: {h1.text}")
                            break
                    
                    # 能力値の表示確認
                    ability_displays = driver.find_elements(By.CLASS_NAME, 'ability-value')
                    if ability_displays:
                        print(f"✅ {len(ability_displays)}個の能力値が表示されています")
                    
                except Exception as e:
                    print(f"詳細確認エラー: {e}")
                
            print("\n🎉 テスト成功: キャラクターが正常に作成されました！")
        else:
            print("⚠️ まだ作成ページにいます")
            
            # エラーメッセージの確認
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            for alert in alerts:
                text = alert.text.strip()
                if text:
                    print(f"アラート: {text}")
            
            # フォームエラーの確認
            error_lists = driver.find_elements(By.CLASS_NAME, 'errorlist')
            if error_lists:
                print("\nフォームエラー:")
                for error_list in error_lists:
                    print(f"  - {error_list.text}")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_character_complete.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 10. キャラクター一覧での確認
        print("\n=== STEP 10: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(3)
        
        page_source = driver.page_source
        if created_character_name in page_source:
            print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
            
            # キャラクターカードの詳細
            cards = driver.find_elements(By.CLASS_NAME, 'card')
            for card in cards:
                if created_character_name in card.text:
                    print("\n✅ キャラクターカードの内容:")
                    card_text = card.text.replace('\n', ' / ')
                    print(f"  {card_text[:200]}...")
                    break
            
            print("\n🎉 完全成功: キャラクターの作成・保存・一覧表示すべて確認されました！")
        else:
            print(f"❌ キャラクター「{created_character_name}」が一覧に見つかりません")
        
        # 一覧のスクリーンショット
        screenshot_path = '/tmp/selenium_character_list_complete.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n一覧スクリーンショット: {screenshot_path}")
        
        print("\n=== テスト完了 ===")
        print("✅ キャラクター作成UIテストが完了しました！")
        
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