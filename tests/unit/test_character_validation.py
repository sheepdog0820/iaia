#!/usr/bin/env python3
"""
キャラクター作成バリデーション・エラーハンドリングテスト
"""
import os
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

# Django設定の初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.character_models import CharacterSheet, CharacterSkill
from accounts.forms import CharacterSheet6thForm
from django.core.exceptions import ValidationError

User = get_user_model()

class CharacterValidationTest(TestCase):
    """キャラクター作成バリデーションテスト"""
    
    def setUp(self):
        """テストユーザーとクライアントの準備"""
        self.user = User.objects.create_user(
            username='validation_test_user',
            password='testpass123',
            email='validation@example.com'
        )
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_required_fields_validation(self):
        """必須フィールドのバリデーションテスト"""
        print("=== 必須フィールドバリデーションテスト ===")
        
        # 必須フィールドを空にしてテスト
        incomplete_data = {
            # name が空
            'age': 25,
            'str_value': 13,
            'con_value': 12,
            'pow_value': 15,
            'dex_value': 14,
            # app_value が空
            'siz_value': 13,
            'int_value': 16,
            'edu_value': 17,
        }
        
        response = self.client.post('/accounts/character/create/6th/', incomplete_data)
        
        # バリデーションエラーでフォームが戻ることを確認
        self.assertEqual(response.status_code, 200, "必須フィールド不足時はフォームに戻るべき")
        print("OK 必須フィールド不足時は正しく処理される")
    
    def test_ability_value_range_validation(self):
        """能力値範囲のバリデーションテスト"""
        print("\n=== 能力値範囲バリデーションテスト ===")
        
        import time
        unique_name = f'範囲テスト_{int(time.time())}'
        
        # 能力値が範囲外のデータ
        invalid_data = {
            'name': unique_name,
            'age': 25,
            'str_value': 1000,  # 999を超える
            'con_value': 0,     # 1未満
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 11,
            'siz_value': 13,
            'int_value': 16,
            'edu_value': 17,
        }
        
        response = self.client.post('/accounts/character/create/6th/', invalid_data)
        
        # バリデーションエラーでフォームが戻ることを確認
        self.assertEqual(response.status_code, 200, "範囲外能力値はバリデーションエラーになるべき")
        print("OK 能力値範囲外エラーは正しく処理される")
    
    def test_age_validation(self):
        """年齢のバリデーションテスト"""
        print("\n=== 年齢バリデーションテスト ===")
        
        import time
        unique_name = f'年齢テスト_{int(time.time())}'
        
        # 年齢が範囲外のデータ
        invalid_age_data = {
            'name': unique_name,
            'age': 10,  # 15未満
            'str_value': 13,
            'con_value': 12,
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 11,
            'siz_value': 13,
            'int_value': 16,
            'edu_value': 17,
        }
        
        response = self.client.post('/accounts/character/create/6th/', invalid_age_data)
        
        # バリデーションエラーでフォームが戻ることを確認
        self.assertEqual(response.status_code, 200, "範囲外年齢はバリデーションエラーになるべき")
        print("OK 年齢範囲外エラーは正しく処理される")
    
    def test_skill_value_limit_6th_edition(self):
        """6版の技能値上限テスト（999）"""
        print("\n=== 6版技能値上限テスト ===")
        
        # まず正常なキャラクターを作成
        import time
        unique_name = f'技能上限テスト_{int(time.time())}'
        
        character = CharacterSheet.objects.create(
            user=self.user,
            name=unique_name,
            edition='6th',
            age=25,
            str_value=13,
            con_value=12,
            pow_value=15,
            dex_value=14,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17,
            hit_points_max=12,
            hit_points_current=12,
            magic_points_max=15,
            magic_points_current=15,
            sanity_starting=15,
            sanity_max=15,
            sanity_current=15,
        )
        
        # 999以下の技能は作成できるはず
        valid_skill = CharacterSkill(
            character_sheet=character,
            skill_name='テスト技能999',
            base_value=25,
            occupation_points=300,
            interest_points=0,
            other_points=674  # 合計999
        )
        
        try:
            valid_skill.save()
            print("OK 999技能の作成は成功")
        except ValidationError:
            self.fail("999技能の作成でエラーが発生")

        # 1000の技能は作成できないはず
        invalid_skill = CharacterSkill(
            character_sheet=character,
            skill_name='テスト技能1000',
            base_value=25,
            occupation_points=300,
            interest_points=0,
            other_points=675  # 合計1000（上限999）
        )
        
        with self.assertRaises(ValidationError):
            invalid_skill.save()
        print("OK 1000技能の作成は正しく拒否される")
    
    def test_duplicate_character_name_allowed(self):
        """同名キャラクター作成は許可されることのテスト"""
        print("\n=== 同名キャラクター許可テスト ===")
        
        base_name = "重複テスト探索者"
        
        # 最初のキャラクター作成
        form_data_1 = {
            'name': base_name,
            'age': 25,
            'str_value': 13,
            'con_value': 12,
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 11,
            'siz_value': 13,
            'int_value': 16,
            'edu_value': 17,
        }
        
        response1 = self.client.post('/accounts/character/create/6th/', form_data_1)
        self.assertEqual(response1.status_code, 302, "最初のキャラクター作成が失敗")
        
        # 同名の2番目のキャラクター作成
        form_data_2 = {
            'name': base_name,  # 同じ名前
            'age': 30,
            'str_value': 15,
            'con_value': 14,
            'pow_value': 13,
            'dex_value': 16,
            'app_value': 12,
            'siz_value': 14,
            'int_value': 17,
            'edu_value': 18,
        }
        
        response2 = self.client.post('/accounts/character/create/6th/', form_data_2)
        self.assertEqual(response2.status_code, 302, "同名キャラクター作成が失敗")
        
        # 両方作成されていることを確認
        characters = CharacterSheet.objects.filter(user=self.user, name=base_name)
        self.assertEqual(characters.count(), 2, "同名キャラクターが2つ作成されるべき")
        print("OK 同名キャラクターの作成は正しく許可される")

def run_validation_tests():
    """バリデーションテストの実行"""
    print("🧪 キャラクター作成バリデーションテストを開始します...\n")
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # テストスイートの作成
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(CharacterValidationTest('test_required_fields_validation'))
    suite.addTest(CharacterValidationTest('test_ability_value_range_validation'))
    suite.addTest(CharacterValidationTest('test_age_validation'))
    suite.addTest(CharacterValidationTest('test_skill_value_limit_6th_edition'))
    suite.addTest(CharacterValidationTest('test_duplicate_character_name_allowed'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\nOK 全バリデーションテストが成功しました！")
    else:
        print(f"\nNG テスト失敗: {len(result.failures)} 個の失敗, {len(result.errors)} 個のエラー")
        for failure in result.failures:
            print(f"失敗: {failure[0]}")
            print(f"詳細: {failure[1]}")
        for error in result.errors:
            print(f"エラー: {error[0]}")
            print(f"詳細: {error[1]}")

if __name__ == '__main__':
    run_validation_tests()
