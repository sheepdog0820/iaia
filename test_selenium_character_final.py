#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
作成から登録までの完全なUIテスト（修正版）
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
    
    print("=== クトゥルフ神話TRPG 6版 キャラクター作成完全テスト ===\n")
    
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
        
        # 必須フィールドの入力（修正版）
        created_character_name = f'テスト探索者_{random.randint(1000, 9999)}'
        test_data = {
            'name': created_character_name,
            'player_name': 'テストプレイヤー',
            'age': str(random.randint(20, 40)),
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜'
        }
        
        # genderフィールドは存在しないため削除
        
        for field_id, value in test_data.items():
            try:
                field = driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(value)
                print(f"✅ {field_id}: {value}")
            except Exception as e:
                print(f"❌ {field_id} フィールドエラー: {e}")
        
        # 性別の選択（セレクトボックスの場合）
        try:
            gender_select = driver.find_element(By.ID, 'gender')
            Select(gender_select).select_by_visible_text('男性')
            print("✅ gender: 男性")
        except:
            print("⚠️ 性別フィールドは見つかりません")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブをクリック（ボタンタイプの場合）
        try:
            ability_tabs = driver.find_elements(By.XPATH, "//button[contains(text(), '能力値')]")
            if ability_tabs:
                ability_tabs[0].click()
                time.sleep(1)
                print("✅ 能力値タブに切り替え")
            else:
                print("⚠️ 能力値タブが見つかりません（既に表示されている可能性）")
        except:
            print("⚠️ 能力値タブ切り替えエラー")
        
        # 能力値の入力（修正版：IDが短縮形）
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
                print(f"✅ {ability.upper()}: {value}")
            except Exception as e:
                print(f"❌ {ability} 入力エラー: {e}")
        
        # 副次ステータスの確認
        time.sleep(1)
        print("\n副次ステータス確認:")
        try:
            # HP確認（IDが異なる可能性）
            hp_elements = driver.find_elements(By.XPATH, "//*[contains(@id, 'hp') and contains(@id, 'max')]")
            if hp_elements:
                print(f"  最大HP要素が見つかりました: {len(hp_elements)}個")
            
            # ダメージボーナス確認
            damage_bonus = driver.find_element(By.ID, 'damage-bonus')
            print(f"  ダメージボーナス: {damage_bonus.get_attribute('value')}")
            
        except Exception as e:
            print(f"⚠️ 副次ステータスの確認エラー: {e}")
        
        # 5. 保存前の準備
        print("\n=== STEP 5: 保存前の確認 ===")
        
        # 基本情報タブに戻る
        try:
            basic_tabs = driver.find_elements(By.XPATH, "//button[contains(text(), '基本情報')]")
            if basic_tabs:
                basic_tabs[0].click()
                time.sleep(1)
        except:
            pass
        
        screenshot_path = '/tmp/selenium_character_before_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"スクリーンショット保存: {screenshot_path}")
        
        # 6. キャラクターの保存
        print("\n=== STEP 6: キャラクターの保存 ===")
        
        try:
            # 保存ボタンを探す（複数の方法を試す）
            save_button = None
            
            # 方法1: type="submit"のボタン
            submit_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"]')
            for button in submit_buttons:
                if '保存' in button.text or 'Save' in button.text:
                    save_button = button
                    break
            
            # 方法2: クラス名で探す
            if not save_button:
                save_button = driver.find_element(By.CSS_SELECTOR, '.btn-primary[type="submit"]')
            
            if save_button:
                # JavaScriptでクリック（確実にクリックするため）
                driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
                time.sleep(1)
                
                print(f"保存ボタンを見つけました: '{save_button.text}'")
                driver.execute_script("arguments[0].click();", save_button)
                print("✅ 保存ボタンをクリック")
                time.sleep(5)  # 保存処理を待つ
            else:
                print("❌ 保存ボタンが見つかりません")
                
                # フォーム送信を試みる
                form = driver.find_element(By.TAG_NAME, 'form')
                driver.execute_script("arguments[0].submit();", form)
                print("✅ フォームを直接送信")
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
            
            # 詳細ページの確認
            try:
                # h1タグまたはキャラクター名を含む要素を探す
                page_headers = driver.find_elements(By.TAG_NAME, 'h1')
                for header in page_headers:
                    if created_character_name in header.text:
                        print(f"✅ 作成されたキャラクター: {header.text}")
                        break
                
                # 能力値カードの確認
                cards = driver.find_elements(By.CLASS_NAME, 'card')
                print(f"表示されているカード数: {len(cards)}")
                
            except Exception as e:
                print(f"⚠️ 詳細ページの確認エラー: {e}")
                
        else:
            print("⚠️ キャラクター作成に失敗した可能性があります")
            
            # エラーメッセージの確認
            try:
                error_messages = driver.find_elements(By.CLASS_NAME, 'alert-danger')
                if error_messages:
                    print("\n=== エラーメッセージ ===")
                    for error in error_messages:
                        print(f"  {error.text}")
                        
                # バリデーションエラーの確認
                invalid_feedback = driver.find_elements(By.CLASS_NAME, 'invalid-feedback')
                if invalid_feedback:
                    print("\n=== バリデーションエラー ===")
                    for feedback in invalid_feedback:
                        if feedback.is_displayed():
                            print(f"  {feedback.text}")
                            
            except:
                pass
        
        # 最終スクリーンショット
        screenshot_path = '/tmp/selenium_character_after_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 8. キャラクター一覧で確認
        print("\n=== STEP 8: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(2)
        
        try:
            # ページソース全体から作成したキャラクター名を検索
            page_source = driver.page_source
            if created_character_name in page_source:
                print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
                
                # キャラクターカードを探す
                character_cards = driver.find_elements(By.CLASS_NAME, 'card')
                for card in character_cards:
                    if created_character_name in card.text:
                        print("✅ キャラクターカードを確認")
                        # カード内の情報を表示
                        try:
                            card_body = card.find_element(By.CLASS_NAME, 'card-body')
                            print(f"  カード情報: {card_body.text[:100]}...")
                        except:
                            pass
                        break
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