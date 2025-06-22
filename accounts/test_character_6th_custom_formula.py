"""
クトゥルフ神話TRPG 6版 任意式職業技能ポイント計算テスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

from .character_models import CharacterSheet

User = get_user_model()


class CustomFormulaCalculatorTestCase(TestCase):
    """任意式職業技能ポイント計算のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # テスト用キャラクター（7版仕様の値）
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Character',
            edition='6th',
            age=25,
            str_value=60,  # 6版なら12
            con_value=70,  # 6版なら14
            pow_value=55,  # 6版なら11
            dex_value=65,  # 6版なら13
            app_value=50,  # 6版なら10
            siz_value=60,  # 6版なら12
            int_value=75,  # 6版なら15
            edu_value=80   # 6版なら16
        )
    
    def test_parse_custom_formula(self):
        """カスタム式のパースをテスト"""
        # parse_custom_formula関数をテスト
        from accounts.utils import parse_custom_formula
        
        test_cases = [
            ("EDU × 20", ["EDU", "×", "20"]),
            ("(EDU + STR) × 10", ["(", "EDU", "+", "STR", ")", "×", "10"]),
            ("EDU × 15 + INT × 5", ["EDU", "×", "15", "+", "INT", "×", "5"]),
            ("(EDU + APP + POW) ÷ 3 × 20", ["(", "EDU", "+", "APP", "+", "POW", ")", "÷", "3", "×", "20"]),
        ]
        
        for formula, expected in test_cases:
            result = parse_custom_formula(formula)
            self.assertEqual(result, expected)
    
    def test_validate_custom_formula(self):
        """カスタム式のバリデーションテスト"""
        from accounts.utils import validate_custom_formula
        
        # 有効な式
        valid_formulas = [
            "EDU × 20",
            "(EDU + STR) × 10",
            "EDU × 15 + INT × 5",
            "(EDU + APP + POW) ÷ 3 × 20",
            "(EDU + STR + INT) × 6",
        ]
        
        for formula in valid_formulas:
            self.assertTrue(validate_custom_formula(formula))
        
        # 無効な式
        invalid_formulas = [
            "EDU × XYZ",  # 無効な能力値
            "EDU + + STR",  # 構文エラー
            "DROP TABLE;",  # SQLインジェクション
            "EDU * 20",  # 無効な演算子（×を使用すべき）
            "eval('malicious')",  # 危険な関数
        ]
        
        for formula in invalid_formulas:
            self.assertFalse(validate_custom_formula(formula))
    
    def test_calculate_custom_formula(self):
        """カスタム式の計算テスト"""
        from accounts.utils import calculate_custom_formula
        
        # 6版の値に変換（現在の値を5で割る）
        edu_6th = 16  # 80 / 5
        str_6th = 12  # 60 / 5
        int_6th = 15  # 75 / 5
        app_6th = 10  # 50 / 5
        pow_6th = 11  # 55 / 5
        
        test_cases = [
            ("EDU × 20", edu_6th * 20),  # 16 × 20 = 320
            ("(EDU + STR) × 10", (edu_6th + str_6th) * 10),  # (16 + 12) × 10 = 280
            ("EDU × 15 + INT × 5", edu_6th * 15 + int_6th * 5),  # 16 × 15 + 15 × 5 = 315
            ("(EDU + APP + POW) ÷ 3 × 20", int((edu_6th + app_6th + pow_6th) / 3 * 20)),  # (16 + 10 + 11) ÷ 3 × 20 ≈ 246
            ("(EDU + STR + INT) × 6", (edu_6th + str_6th + int_6th) * 6),  # (16 + 12 + 15) × 6 = 258
        ]
        
        for formula, expected in test_cases:
            result = calculate_custom_formula(self.character, formula)
            self.assertEqual(result, expected)
    
    def test_custom_formula_edge_cases(self):
        """エッジケースのテスト"""
        from accounts.utils import calculate_custom_formula
        
        # ゼロ除算のテスト
        with self.assertRaises(ValueError):
            calculate_custom_formula(self.character, "EDU ÷ 0")
        
        # 長すぎる式
        long_formula = " + ".join(["EDU"] * 100)
        with self.assertRaises(ValueError):
            calculate_custom_formula(self.character, long_formula)
        
        # 負の結果
        # 最小値は0になるべき
        result = calculate_custom_formula(self.character, "STR - 100")
        self.assertEqual(result, 0)


class OccupationSkillPointsTestCase(TestCase):
    """職業技能ポイント計算式の拡張テスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Character',
            edition='6th',
            age=25,
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80
        )
    
    def test_standard_formulas(self):
        """標準的な職業技能ポイント計算式のテスト"""
        from accounts.utils import calculate_occupation_skill_points
        
        # 6版の値に変換
        test_cases = [
            ('edu20', 16 * 20),  # EDU × 20
            ('edu10app10', 16 * 10 + 10 * 10),  # EDU × 10 + APP × 10
            ('edu10dex10', 16 * 10 + 13 * 10),  # EDU × 10 + DEX × 10
            ('edu10pow10', 16 * 10 + 11 * 10),  # EDU × 10 + POW × 10
            ('edu10str10', 16 * 10 + 12 * 10),  # EDU × 10 + STR × 10
            ('edu10con10', 16 * 10 + 14 * 10),  # EDU × 10 + CON × 10
            ('edu10siz10', 16 * 10 + 12 * 10),  # EDU × 10 + SIZ × 10
            ('edu10int10', 16 * 10 + 15 * 10),  # EDU × 10 + INT × 10
        ]
        
        for formula_type, expected in test_cases:
            result = calculate_occupation_skill_points(self.character, formula_type)
            self.assertEqual(result, expected)
    
    def test_custom_formula_integration(self):
        """任意式の職業技能ポイント計算の統合テスト"""
        from accounts.utils import calculate_occupation_skill_points
        
        # カスタム式
        custom_formula = "(EDU + STR + INT) × 6"
        result = calculate_occupation_skill_points(self.character, 'custom', custom_formula)
        
        # 期待値: (16 + 12 + 15) × 6 = 258
        self.assertEqual(result, 258)
    
    def test_invalid_custom_formula(self):
        """無効な任意式のエラーハンドリングテスト"""
        from accounts.utils import calculate_occupation_skill_points
        
        # 無効な式
        with self.assertRaises(ValueError):
            calculate_occupation_skill_points(self.character, 'custom', "INVALID × FORMULA")