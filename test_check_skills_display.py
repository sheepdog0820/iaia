#!/usr/bin/env python3
"""
技能タブの表示状態を確認
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def check_skills_display():
    """技能タブの表示状態を確認"""
    
    print("=== 技能タブ表示状態確認 ===\n")
    
    # Chrome オプションの設定（ヘッドレスモードOFF）
    options = Options()
    # options.add_argument('--headless')  # デバッグのためコメントアウト
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    
    try:
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        
        # ログイン
        driver.get('http://localhost:8000/accounts/dev-login/')
        time.sleep(1)
        
        login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
        for card in login_cards:
            if 'investigator1' in card.text:
                card.find_element(By.CLASS_NAME, 'login-btn').click()
                break
        
        time.sleep(2)
        
        # キャラクター作成ページへ
        driver.get('http://localhost:8000/accounts/character/create/6th/')
        time.sleep(3)
        
        # 技能タブをクリック
        skills_tab = driver.find_element(By.ID, 'skills-tab')
        driver.execute_script("arguments[0].click();", skills_tab)
        time.sleep(2)
        
        # 技能要素の表示状態を調査
        display_info = driver.execute_script("""
            const skillsPanel = document.getElementById('skills');
            const skillItems = document.querySelectorAll('.skill-item-wrapper');
            const skillContainer = document.getElementById('all-skills-container');
            
            // 各要素の表示状態を確認
            const results = {
                panelDisplay: skillsPanel ? window.getComputedStyle(skillsPanel).display : 'N/A',
                panelVisibility: skillsPanel ? window.getComputedStyle(skillsPanel).visibility : 'N/A',
                containerDisplay: skillContainer ? window.getComputedStyle(skillContainer).display : 'N/A',
                skillItemsCount: skillItems.length,
                visibleSkillItems: 0,
                hiddenSkillItems: 0,
                sampleSkills: []
            };
            
            // 各技能アイテムの表示状態を確認
            skillItems.forEach((item, index) => {
                const style = window.getComputedStyle(item);
                const isVisible = style.display !== 'none' && style.visibility !== 'hidden';
                
                if (isVisible) {
                    results.visibleSkillItems++;
                } else {
                    results.hiddenSkillItems++;
                }
                
                // 最初の5つの詳細情報を取得
                if (index < 5) {
                    const title = item.querySelector('.skill-title');
                    results.sampleSkills.push({
                        name: title?.textContent?.trim() || 'N/A',
                        display: style.display,
                        visibility: style.visibility,
                        height: item.offsetHeight,
                        hasInputs: !!item.querySelector('input')
                    });
                }
            });
            
            // 技能ポイント表示の確認
            const occupationPoints = document.getElementById('occupation-points');
            const interestPoints = document.getElementById('interest-points');
            
            results.pointsDisplay = {
                occupation: occupationPoints ? window.getComputedStyle(occupationPoints).display : 'N/A',
                interest: interestPoints ? window.getComputedStyle(interestPoints).display : 'N/A'
            };
            
            return results;
        """)
        
        print("技能パネル表示状態:")
        print(f"  パネル display: {display_info['panelDisplay']}")
        print(f"  パネル visibility: {display_info['panelVisibility']}")
        print(f"  コンテナ display: {display_info['containerDisplay']}")
        print(f"\n技能アイテム:")
        print(f"  総数: {display_info['skillItemsCount']}")
        print(f"  表示: {display_info['visibleSkillItems']}")
        print(f"  非表示: {display_info['hiddenSkillItems']}")
        
        print(f"\n技能ポイント表示:")
        print(f"  職業: {display_info['pointsDisplay']['occupation']}")
        print(f"  趣味: {display_info['pointsDisplay']['interest']}")
        
        if display_info['sampleSkills']:
            print(f"\nサンプル技能:")
            for skill in display_info['sampleSkills']:
                print(f"  - {skill['name']}: display={skill['display']}, height={skill['height']}, inputs={skill['hasInputs']}")
        
        # スクリーンショット
        screenshot_path = '/tmp/skills_display_check.png'
        driver.save_screenshot(screenshot_path)
        print(f"\nスクリーンショット: {screenshot_path}")
        
        # ブラウザを開いたままにする
        input("\nEnterキーを押してブラウザを閉じます...")
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    check_skills_display()