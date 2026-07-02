#!/usr/bin/env python3
"""
能力値制限削除テスト
"""

import os

import django
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

# Django設定の初期化
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tableno.settings")
django.setup()

from accounts.character_models import CharacterSheet
from accounts.forms import CharacterSheet6thForm

User = get_user_model()


class AbilityLimitsRemovedTest(TestCase):
    """能力値制限削除テスト"""

    def setUp(self):
        """テストユーザーとクライアントの準備"""
        self.user = User.objects.create_user(
            username="ability_test_user", password="testpass123", email="ability@example.com"
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_high_ability_values_allowed(self):
        """高い能力値（999）の許可テスト"""
        print("=== 高い能力値（999）許可テスト ===")

        import time

        unique_name = f"高能力値テスト_{int(time.time())}"

        # 999の能力値でテスト
        high_ability_data = {
            "name": unique_name,
            "age": 25,
            "str_value": 999,
            "con_value": 999,
            "pow_value": 999,
            "dex_value": 999,
            "app_value": 999,
            "siz_value": 999,
            "int_value": 999,
            "edu_value": 999,
        }

        response = self.client.post("/accounts/character/create/6th/", high_ability_data)

        # 成功を確認
        self.assertEqual(response.status_code, 302, "高い能力値でのキャラクター作成が失敗")

        # データベース確認
        character = CharacterSheet.objects.filter(user=self.user, name=unique_name).first()
        self.assertIsNotNone(character, "高い能力値キャラクターが作成されていない")
        self.assertEqual(character.str_value, 999, "STR値が正しく保存されていない")
        self.assertEqual(character.int_value, 999, "INT値が正しく保存されていない")

        print(f"[OK] 高い能力値キャラクター作成成功: {character.name}")
        print(f"  - STR={character.str_value}, INT={character.int_value}, EDU={character.edu_value}")

    def test_low_ability_values_allowed(self):
        """低い能力値（1）の許可テスト"""
        print("\\n=== 低い能力値（1）許可テスト ===")

        import time

        unique_name = f"低能力値テスト_{int(time.time())}"

        # 1の能力値でテスト
        low_ability_data = {
            "name": unique_name,
            "age": 25,
            "str_value": 1,
            "con_value": 1,
            "pow_value": 1,
            "dex_value": 1,
            "app_value": 1,
            "siz_value": 1,
            "int_value": 1,
            "edu_value": 1,
        }

        response = self.client.post("/accounts/character/create/6th/", low_ability_data)

        # 成功を確認
        self.assertEqual(response.status_code, 302, "低い能力値でのキャラクター作成が失敗")

        # データベース確認
        character = CharacterSheet.objects.filter(user=self.user, name=unique_name).first()
        self.assertIsNotNone(character, "低い能力値キャラクターが作成されていない")
        self.assertEqual(character.str_value, 1, "STR値が正しく保存されていない")
        self.assertEqual(character.int_value, 1, "INT値が正しく保存されていない")

        print(f"[OK] 低い能力値キャラクター作成成功: {character.name}")
        print(f"  - STR={character.str_value}, INT={character.int_value}, EDU={character.edu_value}")

    def test_duplicate_character_names_allowed(self):
        """同名キャラクター作成許可テスト"""
        print("\\n=== 同名キャラクター作成許可テスト ===")

        base_name = "重複許可テスト探索者"

        # 最初のキャラクター作成
        first_data = {
            "name": base_name,
            "age": 25,
            "str_value": 13,
            "con_value": 12,
            "pow_value": 15,
            "dex_value": 14,
            "app_value": 11,
            "siz_value": 13,
            "int_value": 16,
            "edu_value": 17,
        }

        response1 = self.client.post("/accounts/character/create/6th/", first_data)
        self.assertEqual(response1.status_code, 302, "最初の同名キャラクター作成が失敗")

        # 同名の2番目のキャラクター作成（異なる能力値）
        second_data = {
            "name": base_name,  # 同じ名前
            "age": 30,
            "str_value": 18,
            "con_value": 16,
            "pow_value": 12,
            "dex_value": 17,
            "app_value": 14,
            "siz_value": 15,
            "int_value": 19,
            "edu_value": 20,
        }

        response2 = self.client.post("/accounts/character/create/6th/", second_data)
        self.assertEqual(response2.status_code, 302, "2番目の同名キャラクター作成が失敗")

        # 同名の3番目のキャラクター作成（さらに異なる能力値）
        third_data = {
            "name": base_name,  # 同じ名前
            "age": 35,
            "str_value": 50,
            "con_value": 60,
            "pow_value": 70,
            "dex_value": 80,
            "app_value": 90,
            "siz_value": 100,
            "int_value": 110,
            "edu_value": 120,
        }

        response3 = self.client.post("/accounts/character/create/6th/", third_data)
        self.assertEqual(response3.status_code, 302, "3番目の同名キャラクター作成が失敗")

        # データベース確認
        characters = CharacterSheet.objects.filter(user=self.user, name=base_name).order_by("id")
        self.assertEqual(characters.count(), 3, "同名キャラクターが3つ作成されるべき")

        # 各キャラクターの独立性確認
        char1, char2, char3 = characters
        self.assertNotEqual(char1.id, char2.id, "キャラクターIDが重複している")
        self.assertNotEqual(char2.id, char3.id, "キャラクターIDが重複している")
        self.assertNotEqual(char1.str_value, char2.str_value, "キャラクターが区別されていない")
        self.assertNotEqual(char2.str_value, char3.str_value, "キャラクターが区別されていない")

        print("[OK] 同名キャラクター3つの作成成功:")
        print(f"  - {char1.name} (ID:{char1.id}) STR={char1.str_value}")
        print(f"  - {char2.name} (ID:{char2.id}) STR={char2.str_value}")
        print(f"  - {char3.name} (ID:{char3.id}) STR={char3.str_value}")


def run_ability_tests():
    """能力値制限削除テストの実行"""
    print("🧪 能力値制限削除テストを開始します...\\n")

    from django.conf import settings
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    # テストスイートの作成
    import unittest

    suite = unittest.TestSuite()
    suite.addTest(AbilityLimitsRemovedTest("test_high_ability_values_allowed"))
    suite.addTest(AbilityLimitsRemovedTest("test_low_ability_values_allowed"))
    suite.addTest(AbilityLimitsRemovedTest("test_duplicate_character_names_allowed"))

    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\\n[OK] 全ての能力値制限削除テストが成功しました！")
    else:
        print(f"\\n[FAIL] テスト失敗: {len(result.failures)} 個の失敗, {len(result.errors)} 個のエラー")
        for failure in result.failures:
            print(f"失敗: {failure[0]}")
            print(f"詳細: {failure[1]}")
        for error in result.errors:
            print(f"エラー: {error[0]}")
            print(f"詳細: {error[1]}")


if __name__ == "__main__":
    run_ability_tests()
