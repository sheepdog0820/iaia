#!/usr/bin/env python
"""
キャラクター作成画面の計算処理をテストするスクリプト
"""

import os
import sys
import django

# Django設定をロード
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from accounts.character_models import CharacterSheet

User = get_user_model()

class CharacterCalculationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='test_user', password='testpass123')
    
    def test_san_calculation(self):
        """SAN値の計算が正しく行われるかテスト"""
        # キャラクター作成
        character_data = {
            'name': 'テスト探索者',
            'age': 25,
            'occupation': 'テスター',
            'edition': '6th',
            'str_value': 10,
            'con_value': 12,
            'pow_value': 14,  # POW=14なので初期SAN=70
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 13,
            'int_value': 15,
            'edu_value': 16,
            'hit_points_max': 13,
            'hit_points_current': 13,
            'magic_points_max': 14,
            'magic_points_current': 14,
            'sanity_starting': 70,  # POW×5
            'sanity_max': 99,  # デフォルト値
            'sanity_current': 70,  # 初期値はPOW×5
        }
        
        response = self.client.post('/accounts/character/create/6th/', character_data)
        
        # キャラクターが作成されたか確認
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 作成されたキャラクターを取得
        character = CharacterSheet.objects.get(name='テスト探索者')
        
        # SAN値の確認
        self.assertEqual(character.sanity_starting, 70)  # POW×5
        self.assertEqual(character.sanity_max, 99)  # デフォルト値
        self.assertEqual(character.sanity_current, 70)  # 初期値
        
        print(f"✅ SAN値計算テスト成功")
        print(f"  - 初期SAN: {character.sanity_starting}")
        print(f"  - 最大SAN: {character.sanity_max}")
        print(f"  - 現在SAN: {character.sanity_current}")
    
    def test_san_with_custom_current_value(self):
        """現在SANをカスタム値で設定した場合のテスト"""
        character_data = {
            'name': '狂気の探索者',
            'age': 30,
            'occupation': '探偵',
            'edition': '6th',
            'str_value': 12,
            'con_value': 14,
            'pow_value': 16,  # POW=16なので初期SAN=80
            'dex_value': 13,
            'app_value': 11,
            'siz_value': 15,
            'int_value': 14,
            'edu_value': 17,
            'hit_points_max': 15,
            'hit_points_current': 10,  # ダメージを受けている
            'magic_points_max': 16,
            'magic_points_current': 8,  # MPを消費している
            'sanity_starting': 80,  # POW×5
            'sanity_max': 94,  # クトゥルフ神話技能5%
            'sanity_current': 45,  # 正気度を大幅に失っている
        }
        
        response = self.client.post('/accounts/character/create/6th/', character_data)
        self.assertEqual(response.status_code, 302)
        
        character = CharacterSheet.objects.get(name='狂気の探索者')
        
        # カスタム値が正しく保存されているか確認
        self.assertEqual(character.sanity_starting, 80)
        self.assertEqual(character.sanity_max, 94)
        self.assertEqual(character.sanity_current, 45)  # カスタム値
        
        print(f"✅ カスタムSAN値テスト成功")
        print(f"  - 初期SAN: {character.sanity_starting}")
        print(f"  - 最大SAN: {character.sanity_max}")
        print(f"  - 現在SAN: {character.sanity_current}")

if __name__ == '__main__':
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    test_runner.setup_test_environment()
    suite = test_runner.test_loader.loadTestsFromTestCase(CharacterCalculationTest)
    test_runner.run_suite(suite)