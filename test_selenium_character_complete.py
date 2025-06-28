#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
作成から登録までの完全なUIテスト
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
        time.sleep(2)
        
        # ページタイトル確認
        try:
            page_title = driver.find_element(By.TAG_NAME, 'h1').text
            print(f"ページタイトル: {page_title}")
            
            if '6版' in page_title:
                print("✅ 6版キャラクター作成ページにアクセス成功")
            else:
                print("❌ 予期しないページです")
                return
        except:
            print("❌ ページタイトルが取得できません")
        
        # 3. 基本情報の入力
        print("\n=== STEP 3: 基本情報の入力 ===")
        
        # 必須フィールドの入力
        test_data = {
            'name': f'テスト探索者_{random.randint(1000, 9999)}',
            'age': str(random.randint(20, 40)),
            'gender': '男性',
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜',
            'player_name': 'テストプレイヤー'
        }
        
        for field_id, value in test_data.items():
            try:
                field = driver.find_element(By.ID, f'id_{field_id}')
                field.clear()
                field.send_keys(value)
                print(f"✅ {field_id}: {value}")
            except Exception as e:
                print(f"❌ {field_id} フィールドエラー: {e}")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブをクリック
        try:
            ability_tab = driver.find_element(By.LINK_TEXT, '能力値')
            ability_tab.click()
            time.sleep(1)
            print("✅ 能力値タブに切り替え")
        except:
            print("⚠️ 能力値タブが見つかりません（既に表示されている可能性）")
        
        # 能力値の入力（標準的な値）
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
                field = driver.find_element(By.ID, f'id_{ability}')
                field.clear()
                field.send_keys(value)
                print(f"✅ {ability.upper()}: {value}")
            except Exception as e:
                print(f"❌ {ability} 入力エラー: {e}")
        
        # 副次ステータスの確認
        time.sleep(1)
        print("\n副次ステータス確認:")
        try:
            # HP確認
            hp_max = driver.find_element(By.ID, 'hp_max')
            print(f"  最大HP: {hp_max.text}")
            
            # MP確認
            mp_max = driver.find_element(By.ID, 'mp_max')
            print(f"  最大MP: {mp_max.text}")
            
            # SAN確認
            san_max = driver.find_element(By.ID, 'san_max')
            print(f"  最大SAN: {san_max.text}")
            
            # ダメージボーナス確認
            damage_bonus = driver.find_element(By.ID, 'damage_bonus')
            print(f"  ダメージボーナス: {damage_bonus.text}")
        except Exception as e:
            print(f"⚠️ 副次ステータスの確認エラー: {e}")
        
        # 5. 技能タブへ移動
        print("\n=== STEP 5: 技能ポイントの割り振り ===")
        
        try:
            skill_tab = driver.find_element(By.LINK_TEXT, '技能')
            skill_tab.click()
            time.sleep(1)
            print("✅ 技能タブに切り替え")
        except:
            print("⚠️ 技能タブが見つかりません")
        
        # 職業技能ポイントの確認
        try:
            occupation_points = driver.find_element(By.ID, 'occupation_points_display')
            interest_points = driver.find_element(By.ID, 'interest_points_display')
            print(f"職業技能ポイント: {occupation_points.text}")
            print(f"趣味技能ポイント: {interest_points.text}")
        except:
            print("⚠️ 技能ポイント表示が見つかりません")
        
        # いくつかの技能にポイントを割り振る
        skills_to_allocate = [
            ('図書館', '70', 'occupation'),
            ('目星', '60', 'occupation'),
            ('聞き耳', '50', 'occupation'),
            ('心理学', '40', 'interest'),
            ('回避', '30', 'interest')
        ]
        
        for skill_data in skills_to_allocate:
            if len(skill_data) == 3:
                skill_name, points, point_type = skill_data
            else:
                skill_name, points, point_type = skill_data[0], skill_data[1], 'occupation'
                
            try:
                # 技能の入力フィールドを探す
                skill_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="number"]')
                for skill_input in skill_inputs:
                    parent_row = skill_input.find_element(By.XPATH, './ancestor::tr')
                    if skill_name in parent_row.text:
                        # 職業/趣味ポイントの選択
                        if point_type == 'occupation':
                            input_field = parent_row.find_element(By.CSS_SELECTOR, 'input[name*="occupation"]')
                        else:
                            input_field = parent_row.find_element(By.CSS_SELECTOR, 'input[name*="interest"]')
                        
                        input_field.clear()
                        input_field.send_keys(points)
                        print(f"✅ {skill_name}: {points}ポイント（{point_type}）")
                        break
            except Exception as e:
                print(f"⚠️ {skill_name} の入力エラー: {e}")
        
        # 6. プロフィールタブ
        print("\n=== STEP 6: プロフィール情報の入力 ===")
        
        try:
            profile_tab = driver.find_element(By.LINK_TEXT, 'プロフィール')
            profile_tab.click()
            time.sleep(1)
            print("✅ プロフィールタブに切り替え")
            
            # キャラクターメモ
            character_memo = driver.find_element(By.ID, 'id_character_memo')
            character_memo.send_keys('このキャラクターはSeleniumテストで作成されました。\n'
                                   '東京で生まれ、横浜で私立探偵をしています。')
            print("✅ キャラクターメモ入力")
            
            # 公開設定
            try:
                is_public = driver.find_element(By.ID, 'id_is_public')
                if not is_public.is_selected():
                    is_public.click()
                    print("✅ 公開設定: ON")
            except:
                print("⚠️ 公開設定チェックボックスが見つかりません")
                
        except Exception as e:
            print(f"⚠️ プロフィールタブエラー: {e}")
        
        # 7. 保存前のスクリーンショット
        print("\n=== STEP 7: 保存前の確認 ===")
        
        # 基本情報タブに戻る
        try:
            basic_tab = driver.find_element(By.LINK_TEXT, '基本情報')
            basic_tab.click()
            time.sleep(1)
        except:
            pass
        
        screenshot_path = '/tmp/selenium_character_before_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"スクリーンショット保存: {screenshot_path}")
        
        # 8. キャラクターの保存
        print("\n=== STEP 8: キャラクターの保存 ===")
        
        try:
            # 保存ボタンを探す
            save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            # JavaScriptでクリック（確実にクリックするため）
            driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", save_button)
            
            print("✅ 保存ボタンをクリック")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 保存ボタンクリックエラー: {e}")
            
            # 代替方法：フォーム送信
            try:
                form = driver.find_element(By.TAG_NAME, 'form')
                driver.execute_script("arguments[0].submit();", form)
                print("✅ フォームを直接送信")
                time.sleep(3)
            except:
                print("❌ フォーム送信も失敗")
        
        # 9. 保存結果の確認
        print("\n=== STEP 9: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # 成功判定
        if '/accounts/character/' in current_url and '/create/' not in current_url:
            print("✅ キャラクター作成成功！")
            
            # 詳細ページの確認
            try:
                character_name = driver.find_element(By.TAG_NAME, 'h1').text
                print(f"作成されたキャラクター: {character_name}")
                
                # 詳細情報の確認
                detail_cards = driver.find_elements(By.CLASS_NAME, 'card')
                for card in detail_cards[:3]:  # 最初の3つのカードのみ
                    try:
                        card_title = card.find_element(By.CLASS_NAME, 'card-header').text
                        print(f"  {card_title} カード確認 ✅")
                    except:
                        pass
                        
            except Exception as e:
                print(f"⚠️ 詳細ページの確認エラー: {e}")
                
        else:
            print("❌ キャラクター作成に失敗した可能性があります")
            
            # エラーメッセージの確認
            try:
                error_messages = driver.find_elements(By.CLASS_NAME, 'alert-danger')
                for error in error_messages:
                    print(f"エラー: {error.text}")
            except:
                pass
        
        # 最終スクリーンショット
        screenshot_path = '/tmp/selenium_character_after_save.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 10. キャラクター一覧で確認
        print("\n=== STEP 10: キャラクター一覧での確認 ===")
        
        driver.get('http://localhost:8000/accounts/character/list/')
        time.sleep(2)
        
        try:
            # 作成したキャラクターを探す
            character_cards = driver.find_elements(By.CLASS_NAME, 'character-card')
            found = False
            
            for card in character_cards:
                if test_data['name'] in card.text:
                    print(f"✅ キャラクター「{test_data['name']}」が一覧に表示されています")
                    found = True
                    break
                    
            if not found:
                print("❌ 作成したキャラクターが一覧に見つかりません")
                
        except Exception as e:
            print(f"⚠️ 一覧確認エラー: {e}")
        
        print("\n=== テスト完了 ===")
        print("✅ キャラクター作成完全テストが終了しました！")
        
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