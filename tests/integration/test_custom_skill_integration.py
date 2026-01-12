"""
カスタム技能機能の統合テスト
"""
import json
import time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

User = get_user_model()


class CustomSkillIntegrationTest(StaticLiveServerTestCase):
    """カスタム技能追加機能のSeleniumテスト"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Chromeオプション設定
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            cls.selenium = webdriver.Chrome(options=chrome_options)
            cls.selenium.implicitly_wait(10)
        except Exception as e:
            print(f"Chrome WebDriver初期化エラー: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'selenium'):
            cls.selenium.quit()
        super().tearDownClass()
    
    def setUp(self):
        """テストユーザーの作成とログイン"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Djangoのテストクライアントでログイン状態を作成
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # セッションクッキーを取得してSeleniumに渡す
        self.selenium.get(f"{self.live_server_url}/")
        
        # Djangoのテストクライアントからセッションクッキーを取得
        session_cookie = self.client.cookies['sessionid']
        
        # Seleniumにセッションクッキーを設定
        self.selenium.add_cookie({
            'name': 'sessionid',
            'value': session_cookie.value,
            'secure': False,
            'path': '/'
        })
        
        # ページをリロードしてログイン状態を反映
        self.selenium.refresh()
    
    def test_add_custom_skill_to_combat_category(self):
        """戦闘カテゴリーにカスタム技能を追加するテスト"""
        # キャラクター作成画面を開く
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        
        # 基本情報を入力
        self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者")
        self.selenium.find_element(By.ID, "age").send_keys("25")
        
        # 能力値を入力（能力値タブへ移動してから）
        self.selenium.find_element(By.ID, "abilities-tab").click()
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, "abilities"))
        )
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            ability_input = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            ability_input.clear()
            ability_input.send_keys("10")
        
        # 技能タブに移動
        self.selenium.find_element(By.ID, "skills-tab").click()
        time.sleep(1)
        
        # 戦闘技能タブを確認
        self.selenium.find_element(By.ID, "combat-tab").click()
        time.sleep(1)
        
        # カスタム技能追加ボタンをクリック
        add_button = WebDriverWait(self.selenium, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#combat button[data-custom-skill-category='combat']"))
        )
        self.selenium.execute_script("arguments[0].click();", add_button)
        time.sleep(1)
        
        # カスタム技能が追加されたことを確認
        custom_skill = self.selenium.find_element(By.CSS_SELECTOR, ".custom-skill")
        self.assertIsNotNone(custom_skill)
        
        # カスタム技能名を変更
        skill_name_input = custom_skill.find_element(By.CSS_SELECTOR, ".custom-skill-name")
        skill_name_input.clear()
        skill_name_input.send_keys("カスタム格闘技")
        
        # 基本値を設定
        base_input = custom_skill.find_element(By.CSS_SELECTOR, ".skill-base")
        base_input.clear()
        base_input.send_keys("15")
        
        # 職業ポイントを割り振り
        occ_input = custom_skill.find_element(By.CSS_SELECTOR, ".occupation-skill")
        occ_input.clear()
        occ_input.send_keys("20")
        
        # 合計値が正しく計算されることを確認
        WebDriverWait(self.selenium, 20).until(
            lambda driver: "35%" in custom_skill.find_element(By.CSS_SELECTOR, ".skill-total").text
        )
    
    def test_add_multiple_custom_skills(self):
        """複数のカスタム技能を追加するテスト"""
        # キャラクター作成画面を開く
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        
        # 基本情報と能力値を入力
        self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者2")
        self.selenium.find_element(By.ID, "abilities-tab").click()
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, "abilities"))
        )
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            ability_input = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            ability_input.clear()
            ability_input.send_keys("12")
        
        # 技能タブに移動
        self.selenium.find_element(By.ID, "skills-tab").click()
        time.sleep(1)
        
        # 知識技能タブに移動
        self.selenium.find_element(By.ID, "knowledge-tab").click()
        time.sleep(1)
        
        # 3つのカスタム技能を追加
        for i in range(3):
            add_button = WebDriverWait(self.selenium, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#knowledge button[data-custom-skill-category='knowledge']"))
            )
            self.selenium.execute_script("arguments[0].click();", add_button)
            time.sleep(0.5)
        
        # カスタム技能が3つ追加されたことを確認
        custom_skills = self.selenium.find_elements(By.CSS_SELECTOR, "#knowledge .custom-skill")
        self.assertEqual(len(custom_skills), 3)
        
        # 各カスタム技能に名前を設定
        skill_names = ["オカルト文献", "古代言語", "神話生物学"]
        for i, (skill, name) in enumerate(zip(custom_skills, skill_names)):
            name_input = skill.find_element(By.CSS_SELECTOR, ".custom-skill-name")
            name_input.clear()
            name_input.send_keys(name)
    
    def test_remove_custom_skill(self):
        """カスタム技能を削除するテスト"""
        # キャラクター作成画面を開く
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        
        # 基本情報と能力値を入力
        self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者3")
        self.selenium.find_element(By.ID, "abilities-tab").click()
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, "abilities"))
        )
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            ability_input = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            ability_input.clear()
            ability_input.send_keys("10")
        
        # 技能タブに移動
        self.selenium.find_element(By.ID, "skills-tab").click()
        time.sleep(1)
        
        # カスタム技能を追加
        add_button = WebDriverWait(self.selenium, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#combat button[data-custom-skill-category='combat']"))
        )
        self.selenium.execute_script("arguments[0].click();", add_button)
        time.sleep(1)
        
        # カスタム技能が追加されたことを確認
        custom_skill = self.selenium.find_element(By.CSS_SELECTOR, ".custom-skill")
        self.assertIsNotNone(custom_skill)
        
        # 削除ボタンをクリック
        delete_button = custom_skill.find_element(By.CSS_SELECTOR, ".btn-outline-danger")
        delete_button.click()
        time.sleep(1)
        
        # カスタム技能が削除されたことを確認
        custom_skills = self.selenium.find_elements(By.CSS_SELECTOR, ".custom-skill")
        self.assertEqual(len(custom_skills), 0)
    
    def test_custom_skill_appears_in_all_skills_tab(self):
        """カスタム技能が全表示タブにも表示されることを確認"""
        # キャラクター作成画面を開く
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        
        # 基本情報と能力値を入力
        self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者4")
        self.selenium.find_element(By.ID, "abilities-tab").click()
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, "abilities"))
        )
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            ability_input = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            ability_input.clear()
            ability_input.send_keys("10")
        
        # 技能タブに移動
        self.selenium.find_element(By.ID, "skills-tab").click()
        time.sleep(1)
        
        # 探索技能タブでカスタム技能を追加
        self.selenium.find_element(By.ID, "exploration-tab").click()
        time.sleep(1)
        
        add_button = WebDriverWait(self.selenium, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#exploration button[data-custom-skill-category='exploration']"))
        )
        self.selenium.execute_script("arguments[0].click();", add_button)
        time.sleep(1)
        
        # カスタム技能名を設定
        custom_skill = self.selenium.find_element(By.CSS_SELECTOR, "#exploration .custom-skill")
        name_input = custom_skill.find_element(By.CSS_SELECTOR, ".custom-skill-name")
        name_input.clear()
        name_input.send_keys("特殊追跡")
        
        # 全表示タブに移動
        self.selenium.find_element(By.ID, "all-tab").click()
        WebDriverWait(self.selenium, 20).until(
            EC.visibility_of_element_located((By.ID, "all"))
        )
        
        # カスタム技能が全表示タブにも存在することを確認
        name_inputs = WebDriverWait(self.selenium, 20).until(
            lambda driver: driver.find_elements(By.CSS_SELECTOR, "#all .custom-skill-name")
        )
        self.assertTrue(
            any(inp.get_attribute("value") == "特殊追跡" for inp in name_inputs),
            "全表示タブにカスタム技能が表示されていません",
        )
    
    def test_custom_skill_with_allocated_points_appears_in_allocated_tab(self):
        """ポイントを振ったカスタム技能が振り分け済みタブに表示されることを確認"""
        # キャラクター作成画面を開く
        self.selenium.get(f"{self.live_server_url}/accounts/character/create/6th/")
        
        # 基本情報と能力値を入力
        self.selenium.find_element(By.ID, "character-name").send_keys("テスト探索者5")
        self.selenium.find_element(By.ID, "abilities-tab").click()
        WebDriverWait(self.selenium, 10).until(
            EC.visibility_of_element_located((By.ID, "abilities"))
        )
        abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for ability in abilities:
            ability_input = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable((By.ID, ability))
            )
            ability_input.clear()
            ability_input.send_keys("15")
        
        # 技能タブに移動
        self.selenium.find_element(By.ID, "skills-tab").click()
        time.sleep(1)
        
        # カスタム技能を追加
        add_button = WebDriverWait(self.selenium, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#combat button[data-custom-skill-category='combat']"))
        )
        self.selenium.execute_script("arguments[0].click();", add_button)
        time.sleep(1)
        
        # カスタム技能にポイントを割り振り
        custom_skill = self.selenium.find_element(By.CSS_SELECTOR, ".custom-skill")
        name_input = custom_skill.find_element(By.CSS_SELECTOR, ".custom-skill-name")
        name_input.clear()
        name_input.send_keys("特殊戦闘術")
        
        occ_input = custom_skill.find_element(By.CSS_SELECTOR, ".occupation-skill")
        occ_input.send_keys("30")
        
        # 振り分け済みタブに移動
        self.selenium.find_element(By.ID, "allocated-tab").click()
        time.sleep(1)
        
        # カスタム技能が表示されることを確認
        allocated_message = self.selenium.find_element(By.ID, "allocatedSkills").text
        self.assertNotIn("まだポイントを振り分けた技能がありません", allocated_message)


class CustomSkillFormTest(TestCase):
    """カスタム技能のフォーム送信テスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_save_character_with_custom_skills(self):
        """カスタム技能を含むキャラクターの保存テスト"""
        # フォームデータ作成
        character_data = {
            'name': 'カスタム技能テスト探索者',
            'player_name': 'テストプレイヤー',
            'age': 30,
            'gender': '男性',
            'occupation': 'オカルト研究者',
            'birthplace': '東京',
            'notes': 'テスト用のキャラクター',
            'str_value': 12,
            'con_value': 14,
            'pow_value': 16,
            'dex_value': 10,
            'app_value': 12,
            'siz_value': 13,
            'int_value': 17,
            'edu_value': 18,
            'skills': json.dumps([
                {
                    "skill_name": "カスタム魔術知識",
                    "base_value": 5,
                    "occupation_points": 40,
                    "interest_points": 10,
                    "other_points": 0,
                    "current_value": 55
                },
                {
                    "skill_name": "古代文字解読",
                    "base_value": 1,
                    "occupation_points": 30,
                    "interest_points": 0,
                    "other_points": 0,
                    "current_value": 31
                },
                {
                    "skill_name": "図書館",
                    "base_value": 25,
                    "occupation_points": 20,
                    "interest_points": 0,
                    "other_points": 0,
                    "current_value": 45
                }
            ])
        }
        
        # フォーム送信
        response = self.client.post('/api/accounts/character-sheets/create_6th_edition/', data=character_data)
        
        # レスポンスの確認
        self.assertEqual(response.status_code, 201)
        
        # 保存されたキャラクターの確認
        from accounts.models import CharacterSheet
        character = CharacterSheet.objects.filter(name='カスタム技能テスト探索者').first()
        self.assertIsNotNone(character)
        self.assertEqual(character.user, self.user)
        
        # カスタム技能が保存されているか確認
        skills = character.skills.all()
        skill_names = [skill.skill_name for skill in skills]
        self.assertIn('カスタム魔術知識', skill_names)
        self.assertIn('古代文字解読', skill_names)
        
        # カスタム技能の値が正しく保存されているか確認
        custom_skill = character.skills.filter(skill_name='カスタム魔術知識').first()
        if custom_skill:
            self.assertEqual(custom_skill.base_value, 5)
            self.assertEqual(custom_skill.occupation_points, 40)
            self.assertEqual(custom_skill.interest_points, 10)
            self.assertEqual(custom_skill.current_value, 55)
