#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
技能値入力デバッグテスト
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

def run_skills_debug_test():
    """技能値入力デバッグテスト"""
    
    print("=== クトゥルフ神話TRPG 6版 技能値入力デバッグテスト ===\n")
    
    # Chrome オプションの設定（ヘッドレスを無効化してデバッグ）
    options = Options()
    # options.add_argument('--headless')  # デバッグのためコメントアウト
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
        
        # 3. ページ構造の調査
        print("\n=== STEP 3: ページ構造の調査 ===")
        
        # タブの存在確認
        tabs_info = driver.execute_script("""
            const tabs = {
                basic: document.getElementById('basic-tab'),
                abilities: document.getElementById('abilities-tab'),
                skills: document.getElementById('skills-tab'),
                equipment: document.getElementById('equipment-tab'),
                backstory: document.getElementById('backstory-tab'),
                growth: document.getElementById('growth-tab')
            };
            
            const result = {};
            for (const [key, tab] of Object.entries(tabs)) {
                result[key] = {
                    exists: !!tab,
                    text: tab?.textContent || 'N/A',
                    active: tab?.classList?.contains('active') || false
                };
            }
            return result;
        """)
        
        print("タブ情報:")
        for tab_name, info in tabs_info.items():
            print(f"  {tab_name}: 存在={info['exists']}, テキスト='{info['text']}', アクティブ={info['active']}")
        
        # 4. 基本情報と能力値を最小限入力
        print("\n=== STEP 4: 最小限の入力 ===")
        
        created_character_name = f'技能デバッグ_{random.randint(1000, 9999)}'
        
        # 基本情報
        driver.find_element(By.ID, 'name').send_keys(created_character_name)
        print(f"✅ 探索者名: {created_character_name}")
        
        # 能力値タブへ
        driver.execute_script("""
            const abilitiesTab = document.getElementById('abilities-tab');
            if (abilitiesTab) {
                abilitiesTab.click();
            }
        """)
        time.sleep(1)
        
        # 能力値入力（EDU高めで技能ポイントを多くする）
        abilities = {
            'str': '10', 'con': '10', 'pow': '10', 'dex': '10',
            'app': '10', 'siz': '10', 'int': '16', 'edu': '18'
        }
        
        for ability, value in abilities.items():
            field = driver.find_element(By.ID, ability)
            field.clear()
            field.send_keys(value)
        
        print("✅ 能力値入力完了")
        time.sleep(2)
        
        # 5. 技能タブの詳細調査
        print("\n=== STEP 5: 技能タブの詳細調査 ===")
        
        # 技能タブをクリック
        skills_tab = driver.find_element(By.ID, 'skills-tab')
        driver.execute_script("arguments[0].click();", skills_tab)
        time.sleep(2)
        
        # 技能タブの内容を調査
        skills_info = driver.execute_script("""
            const skillsPanel = document.getElementById('skills');
            const skillsTab = document.getElementById('skills-tab');
            
            // 技能要素を探す
            const skillItems = document.querySelectorAll('.skill-item-wrapper');
            const skillInputs = document.querySelectorAll('input[name^="skill_"]');
            const occupationInputs = document.querySelectorAll('.skill-occupation');
            const interestInputs = document.querySelectorAll('.skill-interest');
            
            // 技能ポイント表示を探す
            const occupationPoints = document.getElementById('occupation-points');
            const interestPoints = document.getElementById('interest-points');
            
            // hidden inputを探す
            const hiddenInputs = [];
            document.querySelectorAll('input[type="hidden"]').forEach(input => {
                if (input.name && input.name.includes('skill')) {
                    hiddenInputs.push({
                        name: input.name,
                        id: input.id,
                        value: input.value
                    });
                }
            });
            
            return {
                tabActive: skillsTab?.classList?.contains('active'),
                panelActive: skillsPanel?.classList?.contains('active'),
                panelDisplay: skillsPanel ? window.getComputedStyle(skillsPanel).display : 'none',
                skillItemsCount: skillItems.length,
                skillInputsCount: skillInputs.length,
                occupationInputsCount: occupationInputs.length,
                interestInputsCount: interestInputs.length,
                occupationPoints: occupationPoints?.textContent || 'N/A',
                interestPoints: interestPoints?.textContent || 'N/A',
                hiddenInputsCount: hiddenInputs.length,
                sampleHiddenInputs: hiddenInputs.slice(0, 5)
            };
        """)
        
        print("技能タブ情報:")
        print(f"  タブアクティブ: {skills_info['tabActive']}")
        print(f"  パネルアクティブ: {skills_info['panelActive']}")
        print(f"  パネル表示: {skills_info['panelDisplay']}")
        print(f"  技能アイテム数: {skills_info['skillItemsCount']}")
        print(f"  技能入力フィールド数: {skills_info['skillInputsCount']}")
        print(f"  職業技能入力数: {skills_info['occupationInputsCount']}")
        print(f"  趣味技能入力数: {skills_info['interestInputsCount']}")
        print(f"  職業技能ポイント: {skills_info['occupationPoints']}")
        print(f"  趣味技能ポイント: {skills_info['interestPoints']}")
        print(f"  隠しフィールド数: {skills_info['hiddenInputsCount']}")
        
        if skills_info['sampleHiddenInputs']:
            print("  サンプル隠しフィールド:")
            for hidden in skills_info['sampleHiddenInputs']:
                print(f"    - name='{hidden['name']}', id='{hidden['id']}'")
        
        # 6. 技能値入力を試みる（JavaScriptで直接）
        print("\n=== STEP 6: JavaScript経由での技能値入力 ===")
        
        # 技能値を設定
        skills_set = driver.execute_script("""
            // 技能を探して値を設定
            const skillsToSet = [
                {name: '医学', type: 'occupation', value: 60},
                {name: '応急手当', type: 'occupation', value: 50},
                {name: '目星', type: 'interest', value: 40}
            ];
            
            const results = [];
            
            // 各技能を探して値を設定
            skillsToSet.forEach(skillInfo => {
                const skillElements = document.querySelectorAll('.skill-item-wrapper');
                let found = false;
                
                for (const el of skillElements) {
                    const titleEl = el.querySelector('.skill-title');
                    if (titleEl && titleEl.textContent.trim() === skillInfo.name) {
                        // 入力フィールドを探す
                        let inputField = null;
                        if (skillInfo.type === 'occupation') {
                            inputField = el.querySelector('.skill-occupation');
                        } else {
                            inputField = el.querySelector('.skill-interest');
                        }
                        
                        if (inputField) {
                            inputField.value = skillInfo.value;
                            inputField.dispatchEvent(new Event('input', { bubbles: true }));
                            inputField.dispatchEvent(new Event('change', { bubbles: true }));
                            
                            // 合計値を更新
                            const totalField = el.querySelector('.skill-total');
                            if (totalField) {
                                const baseValue = parseInt(el.querySelector('.skill-base')?.value || 0);
                                const occValue = parseInt(el.querySelector('.skill-occupation')?.value || 0);
                                const intValue = parseInt(el.querySelector('.skill-interest')?.value || 0);
                                totalField.value = baseValue + occValue + intValue;
                            }
                            
                            results.push({
                                skill: skillInfo.name,
                                success: true,
                                inputValue: inputField.value,
                                totalValue: totalField?.value || 'N/A'
                            });
                            found = true;
                            break;
                        }
                    }
                }
                
                if (!found) {
                    results.push({
                        skill: skillInfo.name,
                        success: false,
                        error: '技能が見つかりません'
                    });
                }
            });
            
            return results;
        """)
        
        print("技能値設定結果:")
        for result in skills_set:
            if result['success']:
                print(f"  ✅ {result['skill']}: 値={result['inputValue']}, 合計={result['totalValue']}")
            else:
                print(f"  ❌ {result['skill']}: {result['error']}")
        
        # 7. hidden inputフィールドの確認と設定
        print("\n=== STEP 7: 隠しフィールドの調査と設定 ===")
        
        # 技能データをhidden inputに変換
        hidden_conversion = driver.execute_script("""
            // 現在の技能データを収集
            const skillData = [];
            document.querySelectorAll('.skill-item-wrapper').forEach((el, index) => {
                const skillName = el.querySelector('.skill-title')?.textContent?.trim() || '';
                const baseValue = el.querySelector('.skill-base')?.value || '0';
                const occValue = el.querySelector('.skill-occupation')?.value || '0';
                const intValue = el.querySelector('.skill-interest')?.value || '0';
                const bonusValue = el.querySelector('.skill-bonus')?.value || '0';
                
                if (parseInt(occValue) > 0 || parseInt(intValue) > 0) {
                    skillData.push({
                        index: index,
                        name: skillName,
                        base: baseValue,
                        occupation: occValue,
                        interest: intValue,
                        bonus: bonusValue
                    });
                }
            });
            
            // hidden inputフィールドを作成または更新
            const form = document.getElementById('character-form-6th');
            skillData.forEach(skill => {
                const skillId = `skill_${skill.index}`;
                
                // 各フィールドを作成
                ['name', 'base', 'occupation', 'interest', 'bonus'].forEach(field => {
                    const inputName = `${skillId}_${field}`;
                    let hiddenInput = form.querySelector(`input[name="${inputName}"]`);
                    
                    if (!hiddenInput) {
                        hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = inputName;
                        form.appendChild(hiddenInput);
                    }
                    
                    hiddenInput.value = skill[field];
                });
            });
            
            return {
                skillDataCount: skillData.length,
                skills: skillData
            };
        """)
        
        print(f"隠しフィールドに変換された技能数: {hidden_conversion['skillDataCount']}")
        for skill in hidden_conversion['skills']:
            print(f"  - {skill['name']}: 職業={skill['occupation']}, 趣味={skill['interest']}")
        
        # 8. フォーム送信前の最終確認
        print("\n=== STEP 8: フォーム送信前の最終確認 ===")
        
        final_check = driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            const formData = new FormData(form);
            
            const skillFields = [];
            for (let [key, value] of formData.entries()) {
                if (key.includes('skill_') && value) {
                    skillFields.push({key: key, value: value});
                }
            }
            
            return {
                totalFields: Array.from(formData.entries()).length,
                skillFields: skillFields
            };
        """)
        
        print(f"フォームフィールド総数: {final_check['totalFields']}")
        print(f"技能関連フィールド数: {len(final_check['skillFields'])}")
        if final_check['skillFields']:
            print("技能フィールドサンプル:")
            for field in final_check['skillFields'][:10]:
                print(f"  - {field['key']} = {field['value']}")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_skills_debug.png'
        driver.save_screenshot(screenshot_path)
        print(f"\nデバッグスクリーンショット: {screenshot_path}")
        
        # 9. フォーム送信
        print("\n=== STEP 9: フォーム送信 ===")
        
        driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            form.submit();
        """)
        
        time.sleep(5)
        
        # 10. 結果確認
        current_url = driver.current_url
        print(f"\n送信後のURL: {current_url}")
        
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ キャラクター作成成功")
            
            # APIで技能データを確認
            character_id = current_url.split('/character/')[-1].rstrip('/')
            driver.get(f'http://localhost:8000/api/accounts/character-sheets/{character_id}/')
            time.sleep(2)
            
            api_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # 技能データの存在確認
            skills_in_api = []
            for skill_name in ['医学', '応急手当', '目星']:
                if skill_name in api_text:
                    skills_in_api.append(skill_name)
            
            if skills_in_api:
                print(f"✅ APIレスポンスに以下の技能が含まれています: {', '.join(skills_in_api)}")
            else:
                print("❌ APIレスポンスに技能データが見つかりません")
        else:
            print("❌ キャラクター作成に失敗しました")
        
        print("\n=== デバッグテスト完了 ===")
        
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # ブラウザを閉じる前に一時停止
        input("\nEnterキーを押してブラウザを閉じます...")
        
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
        run_skills_debug_test()
    except:
        print("❌ 開発サーバーが起動していません")
        print("以下のコマンドで開発サーバーを起動してください:")
        print("python3 manage.py runserver")
        sys.exit(1)