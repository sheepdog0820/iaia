"""
現在HP/MP/SAN入力機能のテストケース
キャラクター作成時に現在値を任意入力できることを検証
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.character_models import CharacterSheet

User = get_user_model()


class CharacterCurrentStatusTestCase(TestCase):
    """現在HP/MP/SAN入力機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        self.create_url = reverse('character_create_6th')
    
    def test_create_character_with_current_values(self):
        """現在HP/MP/SANを指定してキャラクター作成"""
        data = {
            'name': 'テスト探索者',
            'player_name': 'テストプレイヤー',
            'age': 25,
            'gender': '男性',
            'occupation': '探偵',
            'birthplace': '東京',
            'residence': '東京',
            'str_value': 12,
            'con_value': 14,
            'pow_value': 16,
            'dex_value': 13,
            'app_value': 11,
            'siz_value': 15,
            'int_value': 14,
            'edu_value': 15,
            'notes': 'テストキャラクター',
            # 最大値を追加（フォームバリデーション対応）
            'hit_points_max': 15,
            'magic_points_max': 16,
            'sanity_starting': 80,
            # 現在値を明示的に指定
            'hit_points_current': 5,  # 瀕死状態
            'magic_points_current': 3,  # MP残り少ない
            'sanity_current': 20,  # 正気度大幅減少
        }
        
        response = self.client.post(self.create_url, data)
        
        # リダイレクト成功確認
        self.assertEqual(response.status_code, 302)
        
        # 作成されたキャラクターの確認
        character = CharacterSheet.objects.get(name='テスト探索者')
        
        # 最大値は自動計算される
        self.assertEqual(character.hit_points_max, 15)  # フォームで指定した値
        self.assertEqual(character.magic_points_max, 16)  # POW値
        self.assertEqual(character.sanity_starting, 80)  # POW*5
        
        # 現在値は入力値が反映される
        self.assertEqual(character.hit_points_current, 5)
        self.assertEqual(character.magic_points_current, 3)
        self.assertEqual(character.sanity_current, 20)
    
    def test_create_character_without_current_values(self):
        """現在値を指定せずにキャラクター作成（デフォルト値確認）"""
        data = {
            'name': 'テスト探索者2',
            'player_name': 'テストプレイヤー',
            'age': 30,
            'gender': '女性',
            'occupation': '医師',
            'birthplace': '大阪',
            'residence': '大阪',
            'str_value': 10,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 15,
            'app_value': 13,
            'siz_value': 11,
            'int_value': 16,
            'edu_value': 18,
            'notes': 'テストキャラクター2',
            # 最大値を追加（フォームバリデーション対応）
            'hit_points_max': 12,
            'magic_points_max': 14,
            'sanity_starting': 70,
            # 現在値は指定しない
        }
        
        response = self.client.post(self.create_url, data)
        
        # リダイレクト成功確認
        self.assertEqual(response.status_code, 302)
        
        # 作成されたキャラクターの確認
        character = CharacterSheet.objects.get(name='テスト探索者2')
        
        # 現在値は最大値で初期化される
        self.assertEqual(character.hit_points_current, character.hit_points_max)
        self.assertEqual(character.magic_points_current, character.magic_points_max)
        self.assertEqual(character.sanity_current, character.sanity_starting)
    
    def test_create_character_with_zero_current_values(self):
        """現在値に0を指定してキャラクター作成"""
        data = {
            'name': '死亡探索者',
            'player_name': 'テストプレイヤー',
            'age': 35,
            'gender': '男性',
            'occupation': '学者',
            'birthplace': '京都',
            'residence': '京都',
            'str_value': 8,
            'con_value': 10,
            'pow_value': 12,
            'dex_value': 14,
            'app_value': 12,
            'siz_value': 10,
            'int_value': 18,
            'edu_value': 20,
            'notes': 'HP0の死亡キャラクター',
            # 最大値を追加（フォームバリデーション対応）
            'hit_points_max': 10,
            'magic_points_max': 12,
            'sanity_starting': 60,
            # 現在値を0に指定
            'hit_points_current': 0,  # 死亡
            'magic_points_current': 0,  # MP枯渇
            'sanity_current': 0,  # 完全発狂
        }
        
        response = self.client.post(self.create_url, data)
        
        # リダイレクト成功確認
        self.assertEqual(response.status_code, 302)
        
        # 作成されたキャラクターの確認
        character = CharacterSheet.objects.get(name='死亡探索者')
        
        # 0値が正しく保存される
        self.assertEqual(character.hit_points_current, 0)
        self.assertEqual(character.magic_points_current, 0)
        self.assertEqual(character.sanity_current, 0)
    
    def test_create_character_with_negative_current_values(self):
        """現在値に負の値を指定してキャラクター作成（制限なし）"""
        data = {
            'name': '異常探索者',
            'player_name': 'テストプレイヤー',
            'age': 40,
            'gender': '不明',
            'occupation': '???',
            'birthplace': '不明',
            'residence': '不明',
            'str_value': 99,
            'con_value': 99,
            'pow_value': 99,
            'dex_value': 99,
            'app_value': 99,
            'siz_value': 99,
            'int_value': 99,
            'edu_value': 99,
            'notes': '異常な値のキャラクター',
            # 最大値を追加（フォームバリデーション対応）
            'hit_points_max': 99,
            'magic_points_max': 99,
            'sanity_starting': 495,
            # 負の値を指定（制限なしなので保存される）
            'hit_points_current': -10,
            'magic_points_current': -5,
            'sanity_current': -100,
        }
        
        response = self.client.post(self.create_url, data)
        
        # リダイレクト成功確認
        self.assertEqual(response.status_code, 302)
        
        # 作成されたキャラクターの確認
        character = CharacterSheet.objects.get(name='異常探索者')
        
        # 負の値も保存される（制限なし）
        self.assertEqual(character.hit_points_current, -10)
        self.assertEqual(character.magic_points_current, -5)
        self.assertEqual(character.sanity_current, -100)
    
    def test_create_character_with_over_max_current_values(self):
        """現在値に最大値を超える値を指定してキャラクター作成（制限なし）"""
        data = {
            'name': '超人探索者',
            'player_name': 'テストプレイヤー',
            'age': 25,
            'gender': '男性',
            'occupation': '超人',
            'birthplace': '東京',
            'residence': '東京',
            'str_value': 18,
            'con_value': 18,
            'pow_value': 18,
            'dex_value': 18,
            'app_value': 18,
            'siz_value': 18,
            'int_value': 18,
            'edu_value': 21,
            'notes': '最大値を超えるキャラクター',
            # 最大値を追加（フォームバリデーション対応）
            'hit_points_max': 18,
            'magic_points_max': 18,
            'sanity_starting': 90,
            # 最大値を大幅に超える値を指定
            'hit_points_current': 999,
            'magic_points_current': 999,
            'sanity_current': 999,
        }
        
        response = self.client.post(self.create_url, data)
        
        # リダイレクト成功確認
        self.assertEqual(response.status_code, 302)
        
        # 作成されたキャラクターの確認
        character = CharacterSheet.objects.get(name='超人探索者')
        
        # 最大値を超える値も保存される（制限なし）
        self.assertEqual(character.hit_points_current, 999)
        self.assertEqual(character.magic_points_current, 999)
        self.assertEqual(character.sanity_current, 999)
    
    def test_form_displays_current_value_fields(self):
        """フォームに現在値入力欄が表示されることを確認"""
        response = self.client.get(self.create_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hit_points_current')
        self.assertContains(response, 'magic_points_current')
        self.assertContains(response, 'sanity_current')
        self.assertContains(response, '現在HP')
        self.assertContains(response, '現在MP')
        self.assertContains(response, '現在正気度')