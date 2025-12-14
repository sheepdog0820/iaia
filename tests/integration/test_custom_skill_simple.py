"""
カスタム技能機能の簡易統合テスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class CustomSkillSimpleTest(TestCase):
    """カスタム技能機能の簡易テスト"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_character_create_page_loads(self):
        """キャラクター作成ページが正常に表示されることを確認"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # カスタム技能追加ボタンが含まれているか確認
        self.assertContains(response, 'addCustomSkill')
        self.assertContains(response, 'カスタム技能を追加')
    
    def test_javascript_functions_exist(self):
        """必要なJavaScript関数が定義されているか確認"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # JavaScript関数の確認
        self.assertContains(response, 'function addCustomSkill')
        self.assertContains(response, 'function removeCustomSkill')
        self.assertContains(response, 'function updateCustomSkillName')
        self.assertContains(response, 'function createAddCustomSkillButton')
        self.assertContains(response, 'function createCustomSkillItemHTML')
    
    def test_skill_categories_have_custom_button(self):
        """各技能カテゴリーにカスタム技能追加ボタンが生成されることを確認"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # 各カテゴリーの技能生成部分でcreateAddCustomSkillButtonが呼ばれていることを確認
        categories = ['combat', 'exploration', 'action', 'social', 'knowledge', 'all']
        for category in categories:
            self.assertContains(response, f"createAddCustomSkillButton('{category}')")
    
    def test_custom_skill_styles_exist(self):
        """カスタム技能用のCSSスタイルが定義されているか確認"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)
        
        # CSSクラスの確認
        self.assertContains(response, '.custom-skill')
        self.assertContains(response, '.custom-skill-name')
        self.assertContains(response, 'background-color: #fff3cd')  # カスタム技能の背景色