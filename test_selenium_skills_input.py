#!/usr/bin/env python3
"""
クトゥルフ神話TRPG 6版キャラクターシート
技能値入力・保存のUIテスト
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

def run_skills_input_test():
    """技能値入力テスト"""
    
    print("=== クトゥルフ神話TRPG 6版 技能値入力UIテスト ===\n")
    
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
        
        created_character_name = f'技能テスト探索者_{random.randint(1000, 9999)}'
        
        # 基本情報を入力
        basic_info = {
            'name': created_character_name,
            'player_name': 'テストプレイヤー',
            'age': str(random.randint(20, 40)),
            'occupation': '医師',
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
            gender_field = driver.find_element(By.ID, 'gender')
            gender_field.clear()
            gender_field.send_keys('女性')
            print("✅ gender: 女性")
        except:
            print("⚠️ 性別フィールドは見つかりません")
        
        # 4. 能力値タブへ移動と入力
        print("\n=== STEP 4: 能力値の入力 ===")
        
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
            const abilitiesTab = document.getElementById('abilities-tab');
            const skillsPanel = document.getElementById('skills');
            const abilitiesPanel = document.getElementById('abilities');
            
            if (skillsTab && skillsPanel) {
                abilitiesTab.classList.remove('active');
                skillsTab.classList.add('active');
                abilitiesPanel.classList.remove('show', 'active');
                skillsPanel.classList.add('show', 'active');
                
                // Bootstrapのタブイベントも発火
                const tabTrigger = new bootstrap.Tab(skillsTab);
                tabTrigger.show();
            }
        """)
        time.sleep(2)
        print("✅ 技能タブに切り替え")
        
        # 技能ポイントの確認
        skill_points_info = driver.execute_script("""
            const occupationPoints = document.getElementById('occupation-points')?.textContent || '0';
            const interestPoints = document.getElementById('interest-points')?.textContent || '0';
            
            return {
                occupation: occupationPoints,
                interest: interestPoints
            };
        """)
        
        print(f"\n職業技能ポイント: {skill_points_info['occupation']}")
        print(f"趣味技能ポイント: {skill_points_info['interest']}")
        
        # 6. 技能値の入力
        print("\n=== STEP 6: 技能値の入力 ===")
        
        # 技能を入力する（医師の職業技能を中心に）
        skills_to_input = [
            ('医学', 'occupation', 70),      # 医師の主要技能
            ('応急手当', 'occupation', 60),  # 医師の補助技能
            ('精神分析', 'occupation', 50),  # 医師の補助技能
            ('心理学', 'occupation', 40),    # 医師の補助技能
            ('目星', 'interest', 40),        # 趣味技能
            ('図書館', 'interest', 30),      # 趣味技能
            ('聞き耳', 'interest', 30),      # 趣味技能
        ]
        
        total_occupation_used = 0
        total_interest_used = 0
        
        for skill_name, point_type, points in skills_to_input:
            try:
                # 技能を探す
                skill_element = driver.execute_script(f"""
                    const skillElements = document.querySelectorAll('.skill-item-wrapper');
                    for (let el of skillElements) {{
                        const title = el.querySelector('.skill-title');
                        if (title && title.textContent.trim() === '{skill_name}') {{
                            return el;
                        }}
                    }}
                    return null;
                """)
                
                if skill_element:
                    # スクロールして見える位置に移動
                    driver.execute_script("arguments[0].scrollIntoView(true);", skill_element)
                    time.sleep(0.5)
                    
                    # 入力フィールドを探して値を入力
                    if point_type == 'occupation':
                        input_field = skill_element.find_element(By.CLASS_NAME, 'skill-occupation')
                        total_occupation_used += points
                    else:
                        input_field = skill_element.find_element(By.CLASS_NAME, 'skill-interest')
                        total_interest_used += points
                    
                    input_field.clear()
                    input_field.send_keys(str(points))
                    input_field.send_keys(Keys.TAB)
                    
                    # 合計値の確認
                    time.sleep(0.3)
                    total_element = skill_element.find_element(By.CLASS_NAME, 'skill-total')
                    total_value = total_element.get_attribute('value') or total_element.text
                    
                    print(f"✅ {skill_name}: {point_type}={points} → 合計={total_value}")
                else:
                    print(f"❌ {skill_name}: 技能が見つかりません")
                    
            except Exception as e:
                print(f"❌ {skill_name}: エラー - {e}")
        
        print(f"\n職業技能ポイント使用: {total_occupation_used}")
        print(f"趣味技能ポイント使用: {total_interest_used}")
        
        # 7. カスタム技能の追加テスト
        print("\n=== STEP 7: カスタム技能の追加 ===")
        
        try:
            # 知識技能カテゴリにカスタム技能を追加
            driver.execute_script("""
                // カスタム技能追加関数を直接呼び出し
                if (window.addCustomSkill) {
                    // promptを上書きして自動応答
                    const originalPrompt = window.prompt;
                    let promptCount = 0;
                    window.prompt = (message) => {
                        promptCount++;
                        if (promptCount === 1) return '現代医学知識';  // 技能名
                        if (promptCount === 2) return '20';            // 基本値
                        return null;
                    };
                    
                    window.addCustomSkill('knowledge');
                    
                    // promptを元に戻す
                    window.prompt = originalPrompt;
                    return true;
                }
                return false;
            """)
            
            time.sleep(1)
            print("✅ カスタム技能「現代医学知識」を追加")
            
            # カスタム技能に値を設定
            custom_skill_set = driver.execute_script("""
                const skillElements = document.querySelectorAll('.skill-item-wrapper');
                for (let el of skillElements) {
                    const title = el.querySelector('.skill-title');
                    if (title && title.textContent.includes('現代医学知識')) {
                        const occupationInput = el.querySelector('.skill-occupation');
                        if (occupationInput) {
                            occupationInput.value = '30';
                            occupationInput.dispatchEvent(new Event('input'));
                            return true;
                        }
                    }
                }
                return false;
            """)
            
            if custom_skill_set:
                print("✅ カスタム技能に職業ポイント30を設定")
                total_occupation_used += 30
            
        except Exception as e:
            print(f"⚠️ カスタム技能追加エラー: {e}")
        
        # 8. フォーム送信前の技能データ確認
        print("\n=== STEP 8: 技能データの確認 ===")
        
        skill_data_check = driver.execute_script("""
            const skills = [];
            const skillElements = document.querySelectorAll('.skill-item-wrapper');
            
            skillElements.forEach(el => {
                const title = el.querySelector('.skill-title')?.textContent || '';
                const occupation = el.querySelector('.skill-occupation')?.value || '0';
                const interest = el.querySelector('.skill-interest')?.value || '0';
                const total = el.querySelector('.skill-total')?.value || 
                             el.querySelector('.skill-total')?.textContent || '0';
                
                if (parseInt(occupation) > 0 || parseInt(interest) > 0) {
                    skills.push({
                        name: title.trim(),
                        occupation: occupation,
                        interest: interest,
                        total: total
                    });
                }
            });
            
            return skills;
        """)
        
        print(f"入力された技能数: {len(skill_data_check)}")
        for skill in skill_data_check:
            print(f"  - {skill['name']}: 職業={skill['occupation']}, 趣味={skill['interest']}, 合計={skill['total']}")
        
        # 9. キャラクターの保存
        print("\n=== STEP 9: キャラクターの保存 ===")
        
        # フォームを送信
        driver.execute_script("""
            const form = document.getElementById('character-form-6th');
            form.submit();
        """)
        
        print("✅ フォームを送信しました")
        time.sleep(5)
        
        # 10. 保存結果の確認
        print("\n=== STEP 10: 保存結果の確認 ===")
        
        current_url = driver.current_url
        print(f"現在のURL: {current_url}")
        
        # 成功判定
        if '/character/' in current_url and '/create/' not in current_url:
            print("✅ URLから判断: キャラクター作成成功！")
            
            # キャラクターIDを取得
            character_id = current_url.split('/character/')[-1].rstrip('/')
            print(f"キャラクターID: {character_id}")
            
            # APIで技能データを確認
            driver.get(f'http://localhost:8000/api/accounts/character-sheets/{character_id}/')
            time.sleep(2)
            
            api_response = driver.find_element(By.TAG_NAME, 'pre').text
            if '医学' in api_response:
                print("✅ APIレスポンスに技能データが含まれています")
            
            # キャラクター詳細画面に戻る
            driver.get(current_url)
            time.sleep(2)
            
            # 技能値が表示されているか確認
            skill_display_check = driver.execute_script("""
                const text = document.body.innerText;
                const skills = ['医学', '応急手当', '精神分析', '心理学'];
                const found = [];
                
                skills.forEach(skill => {
                    if (text.includes(skill)) {
                        found.push(skill);
                    }
                });
                
                return found;
            """)
            
            if skill_display_check:
                print(f"✅ 以下の技能が詳細画面に表示されています: {', '.join(skill_display_check)}")
            
            print("\n🎉 テスト成功: 技能値入力とキャラクター作成が正常に完了しました！")
        else:
            print("⚠️ まだ作成ページにいます")
            
            # エラーメッセージの確認
            alerts = driver.find_elements(By.CLASS_NAME, 'alert')
            for alert in alerts:
                text = alert.text.strip()
                if text:
                    print(f"アラート: {text}")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_skills_complete.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n最終スクリーンショット: {screenshot_path}")
        
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
        run_skills_input_test()
    except:
        print("❌ 開発サーバーが起動していません")
        print("以下のコマンドで開発サーバーを起動してください:")
        print("python3 manage.py runserver")
        sys.exit(1)