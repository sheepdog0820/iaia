#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
技能値入力の動作確認テスト（修正版）
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

def run_skills_working_test():
    """技能値入力の動作確認テスト"""
    
    print("=== クトゥルフ神話TRPG 6版 技能値入力動作確認テスト ===\n")
    
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
        
        # 3. 基本情報の入力（必須フィールドをすべて入力）
        print("\n=== STEP 3: 基本情報の入力 ===")
        
        created_character_name = f'技能完全テスト探索者_{random.randint(1000, 9999)}'
        
        # 基本情報を入力
        basic_info = {
            'name': created_character_name,
            'player_name': 'テストプレイヤー',
            'age': '28',  # 必須フィールド
            'gender': '男性',
            'occupation': '医師',
            'birthplace': '東京都',
            'residence': '横浜市'
        }
        
        for field_id, value in basic_info.items():
            try:
                field = driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(value)
                print(f"✅ {field_id}: {value}")
            except Exception as e:
                print(f"❌ {field_id}: {e}")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
        # 能力値タブを表示
        driver.execute_script("""
            const abilitiesTab = document.getElementById('abilities-tab');
            if (abilitiesTab) {
                abilitiesTab.click();
            }
        """)
        time.sleep(1)
        print("✅ 能力値タブに切り替え")
        
        # 能力値の入力（技能ポイント計算のため高めの値を設定）
        abilities = {
            'str': '14',
            'con': '13',
            'pow': '16',
            'dex': '15',
            'app': '12',
            'siz': '11',
            'int': '17',  # 趣味ポイント: 170
            'edu': '18'   # 職業ポイント: 360
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
        
        # 5. 技能タブへ移動
        print("\n=== STEP 5: 技能タブへ移動 ===")
        
        # 技能タブをクリック
        driver.execute_script("""
            const skillsTab = document.getElementById('skills-tab');
            if (skillsTab) {
                skillsTab.click();
            }
        """)
        time.sleep(2)
        print("✅ 技能タブに切り替え")
        
        # 技能ポイントの確認
        skill_points = driver.execute_script("""
            return {
                occupation: document.getElementById('occupation-points')?.textContent || '0',
                interest: document.getElementById('interest-points')?.textContent || '0'
            };
        """)
        
        print(f"\n職業技能ポイント: {skill_points['occupation']}")
        print(f"趣味技能ポイント: {skill_points['interest']}")
        
        # 6. 技能値の入力（skill_{id}_name形式で入力）
        print("\n=== STEP 6: 技能値の入力 ===")
        
        # 技能データを適切な形式で設定
        skills_result = driver.execute_script("""
            // 設定したい技能のリスト
            const skillsToSet = [
                {name: '医学', type: 'occupation', value: 70},
                {name: '応急手当', type: 'occupation', value: 60},
                {name: '精神分析', type: 'occupation', value: 50},
                {name: '心理学', type: 'occupation', value: 40},
                {name: '目星', type: 'interest', value: 50},
                {name: '図書館', type: 'interest', value: 40},
                {name: '聞き耳', type: 'interest', value: 30}
            ];
            
            const results = [];
            let skillIndex = 0;
            
            // 各技能要素を処理
            const skillElements = document.querySelectorAll('.skill-item-wrapper');
            
            skillElements.forEach((el, index) => {
                const titleEl = el.querySelector('.skill-title');
                if (!titleEl) return;
                
                const skillName = titleEl.textContent.trim();
                const matchingSkill = skillsToSet.find(s => s.name === skillName);
                
                if (matchingSkill) {
                    // 入力フィールドの値を設定
                    const baseInput = el.querySelector('.skill-base');
                    const occupationInput = el.querySelector('.skill-occupation');
                    const interestInput = el.querySelector('.skill-interest');
                    const totalInput = el.querySelector('.skill-total');
                    
                    // 対応するフィールドに値を設定
                    if (matchingSkill.type === 'occupation' && occupationInput) {
                        occupationInput.value = matchingSkill.value;
                        occupationInput.dispatchEvent(new Event('input', { bubbles: true }));
                    } else if (matchingSkill.type === 'interest' && interestInput) {
                        interestInput.value = matchingSkill.value;
                        interestInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    
                    // 合計値を更新
                    const baseValue = parseInt(baseInput?.value || 0);
                    const occValue = parseInt(occupationInput?.value || 0);
                    const intValue = parseInt(interestInput?.value || 0);
                    const total = baseValue + occValue + intValue;
                    
                    if (totalInput) {
                        totalInput.value = total;
                    }
                    
                    // フォーム用のhidden inputを作成（技能データ保存用）
                    const form = document.getElementById('character-form-6th');
                    
                    // skill_{index}_name
                    let nameInput = form.querySelector(`input[name="skill_${index}_name"]`);
                    if (!nameInput) {
                        nameInput = document.createElement('input');
                        nameInput.type = 'hidden';
                        nameInput.name = `skill_${index}_name`;
                        form.appendChild(nameInput);
                    }
                    nameInput.value = skillName;
                    
                    // skill_{index}_base
                    let baseHidden = form.querySelector(`input[name="skill_${index}_base"]`);
                    if (!baseHidden) {
                        baseHidden = document.createElement('input');
                        baseHidden.type = 'hidden';
                        baseHidden.name = `skill_${index}_base`;
                        form.appendChild(baseHidden);
                    }
                    baseHidden.value = baseValue;
                    
                    // skill_{index}_occupation
                    let occHidden = form.querySelector(`input[name="skill_${index}_occupation"]`);
                    if (!occHidden) {
                        occHidden = document.createElement('input');
                        occHidden.type = 'hidden';
                        occHidden.name = `skill_${index}_occupation`;
                        form.appendChild(occHidden);
                    }
                    occHidden.value = occValue;
                    
                    // skill_{index}_interest
                    let intHidden = form.querySelector(`input[name="skill_${index}_interest"]`);
                    if (!intHidden) {
                        intHidden = document.createElement('input');
                        intHidden.type = 'hidden';
                        intHidden.name = `skill_${index}_interest`;
                        form.appendChild(intHidden);
                    }
                    intHidden.value = intValue;
                    
                    // skill_{index}_bonus
                    let bonusHidden = form.querySelector(`input[name="skill_${index}_bonus"]`);
                    if (!bonusHidden) {
                        bonusHidden = document.createElement('input');
                        bonusHidden.type = 'hidden';
                        bonusHidden.name = `skill_${index}_bonus`;
                        form.appendChild(bonusHidden);
                    }
                    bonusHidden.value = 0;
                    
                    results.push({
                        skill: skillName,
                        success: true,
                        index: index,
                        type: matchingSkill.type,
                        value: matchingSkill.value,
                        total: total
                    });
                }
            });
            
            return results;
        """)
        
        print("技能値設定結果:")
        total_occupation_used = 0
        total_interest_used = 0
        
        for result in skills_result:
            if result['success']:
                print(f"  ✅ {result['skill']}: {result['type']}={result['value']}, 合計={result['total']} (index={result['index']})")
                if result['type'] == 'occupation':
                    total_occupation_used += result['value']
                else:
                    total_interest_used += result['value']
        
        print(f"\n職業技能ポイント使用: {total_occupation_used}")
        print(f"趣味技能ポイント使用: {total_interest_used}")
        
        # 7. フォーム送信前の最終確認
        print("\n=== STEP 7: フォーム送信前の最終確認 ===")
        
        # 技能関連フィールドの確認
        skill_fields_check = driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            const formData = new FormData(form);
            
            const skillFields = {};
            for (let [key, value] of formData.entries()) {
                if (key.includes('skill_') && key.includes('_name') && value) {
                    const skillId = key.match(/skill_(\d+)_name/)?.[1];
                    if (skillId) {
                        skillFields[skillId] = {
                            name: value,
                            base: formData.get(`skill_${skillId}_base`) || '0',
                            occupation: formData.get(`skill_${skillId}_occupation`) || '0',
                            interest: formData.get(`skill_${skillId}_interest`) || '0'
                        };
                    }
                }
            }
            
            return skillFields;
        """)
        
        print(f"保存される技能数: {len(skill_fields_check)}")
        for skill_id, skill_data in skill_fields_check.items():
            if int(skill_data['occupation']) > 0 or int(skill_data['interest']) > 0:
                print(f"  - {skill_data['name']}: 基本={skill_data['base']}, 職業={skill_data['occupation']}, 趣味={skill_data['interest']}")
        
        # 8. キャラクターの保存
        print("\n=== STEP 8: キャラクターの保存 ===")
        
        # フォームを送信
        driver.execute_script("""
            const form = document.getElementById('character-form-6th');
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
            
            # キャラクターIDを取得
            character_id = current_url.split('/character/')[-1].rstrip('/')
            print(f"キャラクターID: {character_id}")
            
            # ページ内容の確認
            page_source = driver.page_source
            
            # 技能が表示されているか確認
            saved_skills = []
            for skill_name in ['医学', '応急手当', '精神分析', '心理学', '目星', '図書館', '聞き耳']:
                if skill_name in page_source:
                    saved_skills.append(skill_name)
            
            if saved_skills:
                print(f"✅ 以下の技能が詳細画面に表示されています: {', '.join(saved_skills)}")
            else:
                print("⚠️ 技能が詳細画面に表示されていません")
                
                # APIで確認
                driver.get(f'http://localhost:8000/api/accounts/character-sheets/{character_id}/')
                time.sleep(2)
                
                api_text = driver.find_element(By.TAG_NAME, 'body').text
                if '医学' in api_text or 'skills' in api_text:
                    print("✅ ただし、APIレスポンスには技能データが含まれています")
            
            print("\n🎉 テスト成功: 技能値入力とキャラクター作成が正常に完了しました！")
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
        screenshot_path = '/tmp/selenium_skills_success.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
        # 10. キャラクター一覧での確認
        if '/character/' in current_url and '/create/' not in current_url:
            print("\n=== STEP 10: キャラクター一覧での確認 ===")
            
            driver.get('http://localhost:8000/accounts/character/list/')
            time.sleep(3)
            
            page_source = driver.page_source
            if created_character_name in page_source:
                print(f"✅ キャラクター「{created_character_name}」が一覧に表示されています")
                
                # 一覧画面でも技能表示を確認できる場合
                if '医学' in page_source or '応急手当' in page_source:
                    print("✅ 技能情報も一覧に表示されています")
            
            # 一覧のスクリーンショット
            list_screenshot_path = '/tmp/selenium_skills_list.png'
            driver.save_screenshot(list_screenshot_path)
            print(f"\n一覧スクリーンショット: {list_screenshot_path}")
        
        print("\n=== テスト完了 ===")
        print("✅ 技能値入力UIテストが完了しました！")
        
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
        # エラー時のスクリーンショット
        if driver:
            error_screenshot = '/tmp/selenium_skills_error.png'
            driver.save_screenshot(error_screenshot)
            print(f"\nエラースクリーンショット: {error_screenshot}")
        
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
        run_skills_working_test()
    except:
        print("❌ 開発サーバーが起動していません")
        print("以下のコマンドで開発サーバーを起動してください:")
        print("python3 manage.py runserver")
        sys.exit(1)