#!/usr/bin/env python3
"""
タブ切り替えの動作確認テスト
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import sys

def test_tab_switching():
    # Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # Initialize driver
    driver = None
    try:
        # Try different driver paths
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            # Try with explicit path
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ WebDriver initialized successfully")
        
        # Navigate to character creation page
        driver.get("http://localhost:8000/accounts/character/create/6th/")
        print("✅ Navigated to character creation page")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Test all tabs
        tabs = [
            {"id": "basic-tab", "content_id": "basic", "name": "基本情報"},
            {"id": "abilities-tab", "content_id": "abilities", "name": "能力値"},
            {"id": "skills-tab", "content_id": "skills", "name": "技能"},
            {"id": "profile-tab", "content_id": "profile", "name": "プロフィール"},
            {"id": "equipment-tab", "content_id": "equipment", "name": "装備品"},
            {"id": "ccfolia-tab", "content_id": "ccfolia", "name": "CCFOLIA連携"}
        ]
        
        print("\n=== タブ切り替えテスト開始 ===")
        
        for tab in tabs:
            print(f"\n📍 {tab['name']}タブのテスト:")
            
            try:
                # Find and click tab
                tab_element = driver.find_element(By.ID, tab['id'])
                print(f"  ✅ タブボタン発見: {tab['id']}")
                
                # Check if tab is clickable
                if tab_element.is_enabled():
                    print(f"  ✅ タブボタンは有効")
                else:
                    print(f"  ❌ タブボタンが無効")
                
                # Click the tab
                driver.execute_script("arguments[0].click();", tab_element)
                print(f"  ✅ タブをクリック")
                
                # Wait a bit for transition
                time.sleep(0.5)
                
                # Check if content is visible
                content_element = driver.find_element(By.ID, tab['content_id'])
                
                # Check if tab pane has 'show' and 'active' classes
                content_classes = content_element.get_attribute('class')
                print(f"  📋 コンテンツのクラス: {content_classes}")
                
                if 'show' in content_classes and 'active' in content_classes:
                    print(f"  ✅ コンテンツが表示されている")
                else:
                    print(f"  ❌ コンテンツが表示されていない")
                
                # Check if content is actually visible
                if content_element.is_displayed():
                    print(f"  ✅ コンテンツは実際に表示されている")
                else:
                    print(f"  ❌ コンテンツは実際には表示されていない")
                
                # Check tab button active state
                tab_classes = tab_element.get_attribute('class')
                if 'active' in tab_classes:
                    print(f"  ✅ タブボタンがアクティブ")
                else:
                    print(f"  ❌ タブボタンがアクティブではない")
                
                # Special checks for skills tab
                if tab['id'] == 'skills-tab':
                    # Check if skill items are visible
                    skill_items = driver.find_elements(By.CLASS_NAME, 'skill-item-wrapper')
                    print(f"  📊 技能アイテム数: {len(skill_items)}")
                    
                    if skill_items:
                        visible_count = sum(1 for item in skill_items if item.is_displayed())
                        print(f"  📊 表示されている技能数: {visible_count}")
                    
            except Exception as e:
                print(f"  ❌ エラー: {str(e)}")
        
        # Additional diagnostics
        print("\n=== 追加診断 ===")
        
        # Check for JavaScript errors
        logs = driver.get_log('browser')
        if logs:
            print("\n⚠️  ブラウザコンソールエラー:")
            for log in logs:
                if log['level'] == 'SEVERE':
                    print(f"  - {log['message']}")
        else:
            print("✅ JavaScriptエラーなし")
        
        # Check Bootstrap version
        bootstrap_version = driver.execute_script(
            "return typeof bootstrap !== 'undefined' ? bootstrap.VERSION : 'not found'"
        )
        print(f"\n📦 Bootstrap version: {bootstrap_version}")
        
        # Check if jQuery is loaded (if needed)
        jquery_loaded = driver.execute_script(
            "return typeof jQuery !== 'undefined'"
        )
        print(f"📦 jQuery loaded: {jquery_loaded}")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {str(e)}")
        return False
    
    finally:
        if driver:
            driver.quit()
            print("\n✅ WebDriver closed")
    
    return True

if __name__ == "__main__":
    print("🧪 タブ切り替えUIテスト")
    print("=" * 50)
    
    success = test_tab_switching()
    
    if success:
        print("\n✅ テスト完了")
        sys.exit(0)
    else:
        print("\n❌ テスト失敗")
        sys.exit(1)