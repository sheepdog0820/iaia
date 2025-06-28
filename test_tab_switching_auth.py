#!/usr/bin/env python3
"""
タブ切り替えの動作確認テスト（認証付き）
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import sys

def test_tab_switching_with_auth():
    # Chrome options
    chrome_options = Options()
    # ヘッドレスモードを無効化してデバッグ
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
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
        
        # First, login
        print("\n=== ログイン処理 ===")
        driver.get("http://localhost:8000/accounts/login/")
        time.sleep(2)
        
        # Check if we need to login
        if "login" in driver.current_url:
            # Fill login form
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            
            username_field.send_keys("admin")
            password_field.send_keys("arkham_admin_2024")
            
            # Submit form
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            print("✅ Logged in successfully")
            time.sleep(2)
        
        # Navigate to character creation page
        driver.get("http://localhost:8000/accounts/character/create/6th/")
        print("✅ Navigated to character creation page")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        time.sleep(3)  # Give extra time for JavaScript to load
        
        # Take screenshot for debugging
        driver.save_screenshot("tab_test_screenshot.png")
        print("📸 Screenshot saved as tab_test_screenshot.png")
        
        # Check page content
        page_source = driver.page_source
        print(f"\n📄 Page title: {driver.title}")
        print(f"📄 Current URL: {driver.current_url}")
        
        # Check if tabs exist in the page
        tabs_exist = "characterTabs" in page_source
        print(f"📄 Tabs container exists: {tabs_exist}")
        
        # Try to find tabs with different methods
        print("\n=== タブ要素の検索 ===")
        
        # Method 1: By ID
        try:
            tabs_by_id = driver.find_elements(By.CSS_SELECTOR, "[id$='-tab']")
            print(f"✅ ID検索で見つかったタブ数: {len(tabs_by_id)}")
            for tab in tabs_by_id:
                print(f"  - {tab.get_attribute('id')}: {tab.text}")
        except:
            print("❌ ID検索で失敗")
        
        # Method 2: By class
        try:
            tabs_by_class = driver.find_elements(By.CSS_SELECTOR, ".nav-link[data-bs-toggle='tab']")
            print(f"✅ Class検索で見つかったタブ数: {len(tabs_by_class)}")
        except:
            print("❌ Class検索で失敗")
        
        # Test tab switching if tabs are found
        if tabs_by_id:
            print("\n=== タブ切り替えテスト ===")
            
            for tab in tabs_by_id[:6]:  # Test first 6 tabs
                tab_id = tab.get_attribute('id')
                tab_text = tab.text
                
                print(f"\n📍 {tab_text}タブのテスト:")
                
                try:
                    # Click the tab
                    driver.execute_script("arguments[0].scrollIntoView(true);", tab)
                    driver.execute_script("arguments[0].click();", tab)
                    print(f"  ✅ タブをクリック: {tab_id}")
                    
                    time.sleep(1)
                    
                    # Check active state
                    tab_classes = tab.get_attribute('class')
                    if 'active' in tab_classes:
                        print(f"  ✅ タブがアクティブ")
                    else:
                        print(f"  ❌ タブがアクティブではない")
                    
                    # Find corresponding content
                    target = tab.get_attribute('data-bs-target')
                    if target:
                        content_id = target.replace('#', '')
                        try:
                            content = driver.find_element(By.ID, content_id)
                            content_classes = content.get_attribute('class')
                            
                            if 'show' in content_classes and 'active' in content_classes:
                                print(f"  ✅ コンテンツが表示されている: {content_id}")
                            else:
                                print(f"  ❌ コンテンツが表示されていない: {content_id}")
                                print(f"     Classes: {content_classes}")
                        except:
                            print(f"  ❌ コンテンツが見つからない: {content_id}")
                    
                except Exception as e:
                    print(f"  ❌ エラー: {str(e)}")
        
        # Check for JavaScript errors
        print("\n=== JavaScript診断 ===")
        logs = driver.get_log('browser')
        if logs:
            print("⚠️  ブラウザコンソールログ:")
            for log in logs:
                if log['level'] in ['WARNING', 'SEVERE']:
                    print(f"  [{log['level']}] {log['message']}")
        else:
            print("✅ コンソールエラーなし")
        
        # Check Bootstrap
        bootstrap_loaded = driver.execute_script(
            "return typeof bootstrap !== 'undefined'"
        )
        print(f"📦 Bootstrap loaded: {bootstrap_loaded}")
        
        if bootstrap_loaded:
            bootstrap_version = driver.execute_script(
                "return bootstrap.VERSION || 'unknown'"
            )
            print(f"📦 Bootstrap version: {bootstrap_version}")
            
            # Check Tab functionality
            tab_js_check = driver.execute_script(
                "return typeof bootstrap.Tab !== 'undefined'"
            )
            print(f"📦 Bootstrap Tab plugin loaded: {tab_js_check}")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            # Wait before closing
            input("\n⏸️  Press Enter to close browser...")
            driver.quit()
            print("✅ WebDriver closed")
    
    return True

if __name__ == "__main__":
    print("🧪 タブ切り替えUIテスト（認証付き）")
    print("=" * 50)
    
    success = test_tab_switching_with_auth()
    
    if success:
        print("\n✅ テスト完了")
        sys.exit(0)
    else:
        print("\n❌ テスト失敗")
        sys.exit(1)