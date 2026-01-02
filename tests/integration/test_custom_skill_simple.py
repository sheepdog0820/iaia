"""
カスタム技能機能の簡易統合テスト
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
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

    def _read_static(self, relative_path):
        static_path = finders.find(relative_path)
        self.assertIsNotNone(static_path, f"Static file not found: {relative_path}")
        with open(static_path, encoding='utf-8') as handle:
            return handle.read()
    
    def test_character_create_page_loads(self):
        """キャラクター作成ページが正常に表示されることを確認"""
        response = self.client.get(reverse('character_create_6th'))
        self.assertEqual(response.status_code, 200)

        # 必要な静的アセットが読み込まれているか確認
        self.assertContains(response, 'accounts/js/character6th.js')
        self.assertContains(response, 'accounts/css/character6th.css')
    
    def test_javascript_functions_exist(self):
        """必要なJavaScript関数が定義されているか確認"""
        javascript = self._read_static('accounts/js/character6th.js')

        # JavaScript関数の確認
        self.assertIn('function addCustomSkill', javascript)
        self.assertIn('function removeCustomSkill', javascript)
        self.assertIn('function updateCustomSkillName', javascript)
        self.assertIn('function createAddCustomSkillButton', javascript)
        self.assertIn('function createCustomSkillItemHTML', javascript)
    
    def test_skill_categories_have_custom_button(self):
        """各技能カテゴリーにカスタム技能追加ボタンが生成されることを確認"""
        javascript = self._read_static('accounts/js/character6th.js')

        # カテゴリー定義が存在することを確認
        self.assertIn('CUSTOM_SKILL_CATEGORIES', javascript)
        categories = ['combat', 'exploration', 'action', 'social', 'knowledge', 'all']
        for category in categories:
            self.assertIn(f"'{category}'", javascript)
    
    def test_custom_skill_styles_exist(self):
        """カスタム技能用のCSSスタイルが定義されているか確認"""
        stylesheet = self._read_static('accounts/css/character6th.css')

        # CSSクラスの確認
        self.assertIn('.custom-skill', stylesheet)
        self.assertIn('.custom-skill-name', stylesheet)
        self.assertIn('background-color: #fff3cd', stylesheet)  # カスタム技能の背景色
