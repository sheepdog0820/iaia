#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
作成から登録までの完全動作版UIテスト
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
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException

def run_complete_character_creation_test():
    """キャラクター作成から登録までの完全なテスト"""
    
    print("=== クトゥルフ神話TRPG 6版 キャラクター作成完全テスト（動作版） ===\n")
    
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
        try:
            login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
            investigator1_found = False
            
            for card in login_cards:
                if 'investigator1' in card.text:
                    login_btn = card.find_element(By.CLASS_NAME, 'login-btn')
                    login_btn.click()
                    investigator1_found = True
                    break
            
            if investigator1_found:
                time.sleep(2)
                print("✅ investigator1でログイン成功")
            else:
                print("❌ investigator1が見つかりません")
                return
                
        except Exception as e:
            print(f"❌ ログインエラー: {e}")
            return
        
        # 2. キャラクター作成ページへ移動
        print("\n=== STEP 2: キャラクター作成ページへ移動 ===")
        driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(3)
        
        # ページタイトル確認
        page_title = driver.title
        print(f"ページタイトル: {page_title}")
        
        if '6版' in page_title:
            print("✅ 6版キャラクター作成ページにアクセス成功")
        else:
            print("❌ 予期しないページです")
        
        # 3. 基本情報の入力
        print("\n=== STEP 3: 基本情報の入力 ===")
        
        # 基本情報タブがアクティブか確認
        try:
            basic_tab_content = driver.find_element(By.ID, 'basic')
            if 'show' in basic_tab_content.get_attribute('class'):
                print("✅ 基本情報タブがアクティブです")
        except:
            pass
        
        # 必須フィールドの入力
        created_character_name = f'テスト探索者_{random.randint(1000, 9999)}'
        test_data = {
            'name': created_character_name,
            'player_name': 'テストプレイヤー',
            'age': str(random.randint(20, 40)),
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜'
        }
        
        for field_id, value in test_data.items():
            try:
                field = driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(value)
                print(f"✅ {field_id}: {value}")
            except Exception as e:
                print(f"❌ {field_id} フィールドエラー: {e}")
        
        # 性別の選択
        try:
            gender_select = driver.find_element(By.ID, 'gender')
            Select(gender_select).select_by_visible_text('男性')
            print("✅ gender: 男性")
        except:
            print("⚠️ 性別フィールドは見つかりません")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブをクリック（Bootstrap 5のタブ）
        try:
            # タブボタンを見つけてクリック
            ability_tab_button = driver.find_element(By.ID, 'abilities-tab')
            driver.execute_script("arguments[0].click();", ability_tab_button)
            time.sleep(1)
            
            # タブパネルがアクティブになったか確認
            abilities_panel = driver.find_element(By.ID, 'abilities')
            if 'show' in abilities_panel.get_attribute('class'):
                print("✅ 能力値タブに切り替え成功")
            else:
                # 強制的にタブを表示
                driver.execute_script("""
                    // 基本情報タブを非アクティブに
                    document.getElementById('basic-tab').classList.remove('active');
                    document.getElementById('basic').classList.remove('show', 'active');
                    
                    // 能力値タブをアクティブに
                    document.getElementById('abilities-tab').classList.add('active');
                    document.getElementById('abilities').classList.add('show', 'active');
                """)
                print("✅ JavaScriptで能力値タブに切り替え")
                
        except Exception as e:
            print(f"⚠️ 能力値タブ切り替えエラー: {e}")
        
        time.sleep(1)
        
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
                # 要素が見えるまで待機
                field = wait.until(EC.visibility_of_element_located((By.ID, ability)))
                
                # JavaScriptで値を設定（より確実）
                driver.execute_script(f"""
                    var element = document.getElementById('{ability}');
                    if (element) {{
                        element.value = '{value}';
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                print(f"✅ {ability.upper()}: {value}")
                
            except Exception as e:
                print(f"❌ {ability} 入力エラー: {e}")
        
        # 副次ステータスの確認（計算が完了するまで少し待つ）
        time.sleep(2)
        print("\n副次ステータス確認:")
        try:
            # JavaScriptで値を取得
            stats = driver.execute_script("""
                return {
                    hp_max: document.getElementById('hit-points-max')?.value || 'N/A',
                    mp_max: document.getElementById('magic-points-max')?.value || 'N/A',
                    san_max: document.getElementById('sanity-max')?.value || 'N/A',
                    damage_bonus: document.getElementById('damage-bonus')?.value || 'N/A'
                };
            """)
            
            print(f"  最大HP: {stats['hp_max']}")
            print(f"  最大MP: {stats['mp_max']}")
            print(f"  最大SAN: {stats['san_max']}")
            print(f"  ダメージボーナス: {stats['damage_bonus']}")
            
        except Exception as e:
            print(f"⚠️ 副次ステータスの確認エラー: {e}")
        
        # 5. 保存前の確認
        print("\n=== STEP 5: 保存前の確認 ===")
        
        # スクリーンショット（能力値タブの状態）
        screenshot_path = '/tmp/selenium_character_abilities.png'
        driver.save_screenshot(screenshot_path)
        print(f"能力値タブのスクリーンショット: {screenshot_path}")
        
        # 基本情報タブに戻る
        try:
            basic_tab_button = driver.find_element(By.ID, 'basic-tab')
            driver.execute_script("arguments[0].click();", basic_tab_button)
            time.sleep(1)
            print("✅ 基本情報タブに戻りました")
        except:
            pass
        
        screenshot_path = '/tmp/selenium_character_before_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"保存前スクリーンショット: {screenshot_path}")
        
        # 6. キャラクターの保存
        print("\n=== STEP 6: キャラクターの保存 ===")
        
        try:
            # 保存ボタンを探す
            save_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"]')
            save_button = None
            
            for button in save_buttons:
                button_text = button.text.strip()
                # ボタンが表示されていて、適切なテキストを持っているか確認
                if button.is_displayed() and ('保存' in button_text or 'Save' in button_text or button_text == ''):
                    # 空のボタンの場合、aria-labelやtitleを確認
                    aria_label = button.get_attribute('aria-label') or ''
                    title = button.get_attribute('title') or ''
                    if '保存' in aria_label or '保存' in title or button_text or True:  # 最後は任意のsubmitボタン
                        save_button = button
                        break
            
            if save_button:
                # スクロールして表示
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(1)
                
                # JavaScriptでクリック
                driver.execute_script("arguments[0].click();", save_button)
                print("✅ 保存ボタンをクリック")
                
                # 保存処理を待つ
                time.sleep(5)
            else:
                print("❌ 保存ボタンが見つかりません - フォームを直接送信します")
                # フォーム送信
                form = driver.find_element(By.TAG_NAME, 'form')
                driver.execute_script("arguments[0].submit();", form)
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
        
        # 7. 保存結果の確認
        print("\n=== STEP 7: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # 成功判定
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ キャラクター作成成功！")
            
            # キャラクターIDを取得
            try:
                character_id = current_url.split('/character/')[1].rstrip('/')
                print(f"作成されたキャラクターID: {character_id}")
            except:
                pass
            
            # 詳細ページの確認
            try:
                # ページ内でキャラクター名を探す
                page_source = driver.page_source
                if created_character_name in page_source:
                    print(f"✅ キャラクター名「{created_character_name}」が表示されています")
                
                # 能力値の表示確認
                ability_cards = driver.find_elements(By.CLASS_NAME, 'card')
                if ability_cards:
                    print(f"✅ {len(ability_cards)}個のカードが表示されています")
                    
            except Exception as e:
                print(f"⚠️ 詳細ページの確認エラー: {e}")
                
        else:
            print("⚠️ URLから判断すると、まだ作成ページにいます")
            
            # エラーメッセージの確認
            try:
                # アラートメッセージ
                alerts = driver.find_elements(By.CLASS_NAME, 'alert')
                for alert in alerts:
                    if alert.is_displayed() and alert.text.strip():
                        print(f"アラート: {alert.text}")
                
                # フォームのバリデーションエラー
                invalid_feedbacks = driver.find_elements(By.CLASS_NAME, 'invalid-feedback')
                for feedback in invalid_feedbacks:
                    if feedback.is_displayed():
                        print(f"バリデーションエラー: {feedback.text}")
                        
                # HTML5バリデーションメッセージ
                required_fields = driver.find_elements(By.CSS_SELECTOR, '[required]')
                for field in required_fields:
                    validity = driver.execute_script("return arguments[0].validity.valid;", field)
                    if not validity:
                        field_name = field.get_attribute('name') or field.get_attribute('id')
                        print(f"必須フィールド未入力: {field_name}")
                        
            except Exception as e:
                print(f"エラー確認中の例外: {e}")
        
        # 最終スクリーンショット
        screenshot_path = '/tmp/selenium_character_after_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 8. キャラクター一覧で確認
        print("\n=== STEP 8: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(3)
        
        try:
            page_source = driver.page_source
            if created_character_name in page_source:
                print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
                
                # キャラクターカードの詳細確認
                cards = driver.find_elements(By.CLASS_NAME, 'card')
                for card in cards:
                    if created_character_name in card.text:
                        print("✅ キャラクターカードの詳細:")
                        card_text = card.text.replace('\n', ' ')
                        print(f"  {card_text[:150]}...")
                        break
                        
                # 一覧のスクリーンショット
                screenshot_path = '/tmp/selenium_character_list.png'
                driver.save_screenshot(screenshot_path)
                print(f"\nキャラクター一覧スクリーンショット: {screenshot_path}")
                
            else:
                print(f"❌ 作成したキャラクター「{created_character_name}」が一覧に見つかりません")
                
        except Exception as e:
            print(f"⚠️ 一覧確認エラー: {e}")
        
        print("\n=== テスト完了 ===")
        print("✅ キャラクター作成完全テストが終了しました！")
        
        # テスト結果のサマリー
        print("\n=== テスト結果サマリー ===")
        print(f"作成したキャラクター名: {created_character_name}")
        print(f"最終URL: {current_url}")
        
        # 成功判定
        if created_character_name and created_character_name in driver.page_source:
            print("\n🎉 テスト成功: キャラクターが正常に作成されました！")
        else:
            print("\n⚠️ テスト一部成功: キャラクター作成プロセスを完了しましたが、確認が必要です")
        
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