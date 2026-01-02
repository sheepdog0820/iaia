#!/usr/bin/env python3
"""
キャラクター技能データの統合テスト
"""
import os
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

# Django設定の初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
django.setup()

from accounts.character_models import CharacterSheet, CharacterSkill
from accounts.forms import CharacterSheet6thForm

User = get_user_model()

class CharacterSkillsIntegrationTest(TestCase):
    """キャラクター技能データの統合テスト"""
    
    def setUp(self):
        """テストユーザーとクライアントの準備"""
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123',
            email='test@example.com'
        )
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_character_creation_with_skills(self):
        """技能データを含むキャラクター作成テスト"""
        print("=== 技能データ付きキャラクター作成テスト ===")
        
        import time
        unique_name = f'技能テスト探索者_{int(time.time())}'
        
        # テストデータ
        form_data = {
            'name': unique_name,
            'age': 25,
            'gender': '男性',
            'occupation': '探偵',
            'birthplace': '東京',
            'residence': '東京',
            'str_value': 13,
            'con_value': 12,
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 11,
            'siz_value': 13,
            'int_value': 16,
            'edu_value': 17,
            'notes': '技能テスト用キャラクター',
            'mental_disorder': '',
            # 必須フィールド（副次ステータス）
            'hit_points_max': 13,  # (CON + SIZ) / 2 = (12 + 13) / 2 = 12.5 → 13
            'magic_points_max': 15,  # POW = 15
            'sanity_starting': 75,  # POW × 5 = 15 × 5 = 75
            # 技能データ（複数技能）
            'skill_目星_name': '目星',
            'skill_目星_base': '25',
            'skill_目星_occupation': '60',
            'skill_目星_interest': '10',
            'skill_目星_bonus': '0',
            'skill_目星_total': '95',
            'skill_聞き耳_name': '聞き耳',
            'skill_聞き耳_base': '25',
            'skill_聞き耳_occupation': '40',
            'skill_聞き耳_interest': '20',
            'skill_聞き耳_bonus': '5',
            'skill_聞き耳_total': '90',
            'skill_回避_name': '回避',
            'skill_回避_base': '28',  # DEX×2
            'skill_回避_occupation': '0',
            'skill_回避_interest': '30',
            'skill_回避_bonus': '0',
            'skill_回避_total': '58',
            'skill_図書館_name': '図書館',
            'skill_図書館_base': '25',
            'skill_図書館_occupation': '50',
            'skill_図書館_interest': '0',
            'skill_図書館_bonus': '0',
            'skill_図書館_total': '75',
        }
        
        print(f"✅ テストキャラクター名: {unique_name}")
        print(f"📝 技能データ数: {len([k for k in form_data.keys() if k.startswith('skill_') and k.endswith('_name')])}")
        
        # フォーム送信
        response = self.client.post('/accounts/character/create/6th/', form_data)
        
        # レスポンス確認
        self.assertEqual(response.status_code, 302, "キャラクター作成後のリダイレクトが失敗")
        # キャラクター作成後は詳細ページにリダイレクトされる
        self.assertIn('/accounts/character/', response.get('Location', ''), "正しいURLにリダイレクトされていない")
        
        # データベース確認
        character = CharacterSheet.objects.filter(user=self.user, name=unique_name).first()
        self.assertIsNotNone(character, "キャラクターが作成されていない")
        
        print(f"✅ キャラクター作成成功: {character.name}")
        print(f"  - 能力値: STR={character.str_value}, DEX={character.dex_value}, INT={character.int_value}, EDU={character.edu_value}")
        
        # 技能データ確認
        skills = CharacterSkill.objects.filter(character_sheet=character)
        skill_count = skills.count()
        print(f"  - 保存された技能数: {skill_count}")
        
        self.assertGreater(skill_count, 0, "技能データが保存されていない")
        
        # 個別技能の確認
        expected_skills = ['目星', '聞き耳', '回避', '図書館']
        for skill_name in expected_skills:
            skill = skills.filter(skill_name=skill_name).first()
            self.assertIsNotNone(skill, f"技能「{skill_name}」が保存されていない")
            print(f"    {skill_name}: 基本={skill.base_value}, 職業={skill.occupation_points}, 趣味={skill.interest_points}, 合計={skill.current_value}")
        
        # 回避技能の特別確認（DEX×2）
        dodge_skill = skills.filter(skill_name='回避').first()
        if dodge_skill:
            expected_dodge_base = character.dex_value * 2
            self.assertEqual(dodge_skill.base_value, expected_dodge_base, 
                           f"回避技能の基本値が正しくない。期待値:{expected_dodge_base}, 実際:{dodge_skill.base_value}")
            print(f"  ✅ 回避技能の基本値が正しく設定されています: {dodge_skill.base_value} (DEX×2)")
        
        return character
    
    def test_skill_calculation_logic(self):
        """技能計算ロジックのテスト"""
        print("\n=== 技能計算ロジックテスト ===")
        
        character = self.test_character_creation_with_skills()
        skills = CharacterSkill.objects.filter(character_sheet=character)
        
        for skill in skills:
            expected_total = skill.base_value + skill.occupation_points + skill.interest_points + skill.other_points
            self.assertEqual(skill.current_value, expected_total, 
                           f"技能「{skill.skill_name}」の合計値が正しくない")
            print(f"  ✅ {skill.skill_name}: {skill.base_value}+{skill.occupation_points}+{skill.interest_points}+{skill.other_points}={skill.current_value}")
    
    def test_derived_stats_calculation(self):
        """副次ステータス計算のテスト"""
        print("\n=== 副次ステータス計算テスト ===")
        
        character = self.test_character_creation_with_skills()
        
        # HP計算 (CON + SIZ) / 2（端数切り上げ）
        import math
        expected_hp = math.ceil((character.con_value + character.siz_value) / 2)
        self.assertEqual(character.hit_points_max, expected_hp, "最大HP計算が正しくない")
        self.assertEqual(character.hit_points_current, expected_hp, "現在HP初期値が正しくない")
        print(f"  ✅ HP: {character.hit_points_current}/{character.hit_points_max} = ceil((CON{character.con_value} + SIZ{character.siz_value}) / 2)")
        
        # MP計算 POW
        expected_mp = character.pow_value
        self.assertEqual(character.magic_points_max, expected_mp, "最大MP計算が正しくない")
        self.assertEqual(character.magic_points_current, expected_mp, "現在MP初期値が正しくない")
        print(f"  ✅ MP: {character.magic_points_current}/{character.magic_points_max} = POW{character.pow_value}")
        
        # 正気度計算（6版: POW × 5）
        expected_sanity_start = character.pow_value * 5
        self.assertEqual(character.sanity_starting, expected_sanity_start, "初期正気度計算が正しくない")
        self.assertEqual(character.sanity_max, expected_sanity_start, "最大正気度計算が正しくない")
        self.assertEqual(character.sanity_current, expected_sanity_start, "現在正気度初期値が正しくない")
        print(f"  ✅ 正気度: {character.sanity_current}/{character.sanity_max} (初期:{character.sanity_starting}) = POW{character.pow_value} × 5")

def run_tests():
    """テストの実行"""
    print("🧪 キャラクター技能データ統合テストを開始します...\n")
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # テストスイートの作成
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(CharacterSkillsIntegrationTest('test_character_creation_with_skills'))
    suite.addTest(CharacterSkillsIntegrationTest('test_skill_calculation_logic'))
    suite.addTest(CharacterSkillsIntegrationTest('test_derived_stats_calculation'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ 全テストが成功しました！")
    else:
        print(f"\n❌ テスト失敗: {len(result.failures)} 個の失敗, {len(result.errors)} 個のエラー")
        for failure in result.failures:
            print(f"失敗: {failure[0]}")
            print(f"詳細: {failure[1]}")
        for error in result.errors:
            print(f"エラー: {error[0]}")
            print(f"詳細: {error[1]}")

if __name__ == '__main__':
    run_tests()
