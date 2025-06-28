#!/usr/bin/env python3
"""
作成されたキャラクターの技能データ確認
"""

import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def verify_character_skills():
    """キャラクター79の技能データを確認"""
    
    print("=== キャラクター技能データ確認 ===\n")
    
    # Chrome オプションの設定
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    
    try:
        # ChromeDriver サービス
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        
        # 開発用ログイン
        driver.get('http://localhost:8000/accounts/dev-login/')
        time.sleep(1)
        
        login_cards = driver.find_elements(By.CLASS_NAME, 'user-card')
        for card in login_cards:
            if 'investigator1' in card.text:
                card.find_element(By.CLASS_NAME, 'login-btn').click()
                break
        
        time.sleep(2)
        
        # キャラクター詳細画面へ
        driver.get('http://localhost:8000/accounts/character/79/')
        time.sleep(2)
        
        # 技能タブをクリック（もしあれば）
        try:
            skills_tab = driver.find_element(By.ID, 'skills-tab-detail')
            if skills_tab:
                driver.execute_script("arguments[0].click();", skills_tab)
                time.sleep(1)
        except:
            pass
        
        # ページ内のテキストを取得
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        
        # 技能名を検索
        skills_found = []
        skills_to_check = ['応急手当', '精神分析', '聞き耳', '医学', '心理学', '目星', '図書館']
        
        for skill in skills_to_check:
            if skill in page_text:
                skills_found.append(skill)
        
        print("=== 検出された技能 ===")
        if skills_found:
            print(f"✅ 以下の技能が保存されています:")
            for skill in skills_found:
                print(f"   - {skill}")
        else:
            print("❌ 技能が見つかりません")
        
        # APIアクセス（認証付き）
        try:
            # セッションクッキーを取得
            cookies = driver.get_cookies()
            
            # APIエンドポイントにアクセス
            driver.get('http://localhost:8000/api/accounts/character-sheets/79/')
            time.sleep(1)
            
            api_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # APIレスポンスに技能データがあるか確認
            if '"skills"' in api_text:
                print("\n✅ APIレスポンスに技能データセクションが存在します")
                
                # 技能数をカウント
                skills_count = api_text.count('"skill_name"')
                if skills_count > 0:
                    print(f"   保存されている技能数: {skills_count}")
            
        except Exception as e:
            print(f"\nAPI確認エラー: {e}")
        
        # スクリーンショット
        screenshot_path = '/tmp/selenium_skills_verify.png'
        driver.save_screenshot(screenshot_path)
        print(f"\n確認スクリーンショット: {screenshot_path}")
        
        print("\n=== 確認完了 ===")
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    # 開発サーバーが起動しているか確認
    import requests
    try:
        response = requests.get('http://localhost:8000/', timeout=2)
        print("✅ 開発サーバーが起動しています\n")
        verify_character_skills()
    except:
        print("❌ 開発サーバーが起動していません")
        sys.exit(1)