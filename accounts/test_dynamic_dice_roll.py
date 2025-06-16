"""
6版ダイスロール動的設定機能のテスト

TDD: RED フェーズ - 動的ダイス設定を使用する失敗するテストケースを作成
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import CustomUser, CharacterDiceRollSetting
from accounts.utils import (
    roll_ability_with_setting,
    get_current_dice_settings,
    calculate_abilities_with_setting,
    validate_dice_settings
)
import json

User = get_user_model()


class DynamicDiceRollTestCase(TestCase):
    """動的ダイスロール機能のテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 標準設定を作成
        self.standard_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="標準6版設定",
            is_default=True,
            str_dice_count=3, str_dice_sides=6, str_bonus=0,
            con_dice_count=3, con_dice_sides=6, con_bonus=0,
            pow_dice_count=3, pow_dice_sides=6, pow_bonus=0,
            dex_dice_count=3, dex_dice_sides=6, dex_bonus=0,
            app_dice_count=3, app_dice_sides=6, app_bonus=0,
            siz_dice_count=2, siz_dice_sides=6, siz_bonus=6,
            int_dice_count=2, int_dice_sides=6, int_bonus=6,
            edu_dice_count=3, edu_dice_sides=6, edu_bonus=3
        )
        
        # カスタム設定を作成
        self.custom_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="カスタム設定",
            is_default=False,
            str_dice_count=4, str_dice_sides=6, str_bonus=-2,
            con_dice_count=5, con_dice_sides=4, con_bonus=2,
            pow_dice_count=2, pow_dice_sides=8, pow_bonus=1,
            dex_dice_count=3, dex_dice_sides=10, dex_bonus=0,
            app_dice_count=1, app_dice_sides=20, app_bonus=-5,
            siz_dice_count=3, siz_dice_sides=6, siz_bonus=3,
            int_dice_count=4, int_dice_sides=6, int_bonus=-1,
            edu_dice_count=2, edu_dice_sides=12, edu_bonus=4
        )
    
    def test_roll_ability_with_standard_setting(self):
        """標準設定でのダイスロールテスト"""
        # STR: 3D6 (範囲: 3-18)
        str_roll = roll_ability_with_setting('str', self.standard_setting)
        self.assertGreaterEqual(str_roll, 3)
        self.assertLessEqual(str_roll, 18)
        
        # SIZ: 2D6+6 (範囲: 8-18)
        siz_roll = roll_ability_with_setting('siz', self.standard_setting)
        self.assertGreaterEqual(siz_roll, 8)
        self.assertLessEqual(siz_roll, 18)
        
        # EDU: 3D6+3 (範囲: 6-21)
        edu_roll = roll_ability_with_setting('edu', self.standard_setting)
        self.assertGreaterEqual(edu_roll, 6)
        self.assertLessEqual(edu_roll, 21)
    
    def test_roll_ability_with_custom_setting(self):
        """カスタム設定でのダイスロールテスト"""
        # STR: 4D6-2 (範囲: 2-22)
        str_roll = roll_ability_with_setting('str', self.custom_setting)
        self.assertGreaterEqual(str_roll, 2)
        self.assertLessEqual(str_roll, 22)
        
        # CON: 5D4+2 (範囲: 7-22)
        con_roll = roll_ability_with_setting('con', self.custom_setting)
        self.assertGreaterEqual(con_roll, 7)
        self.assertLessEqual(con_roll, 22)
        
        # POW: 2D8+1 (範囲: 3-17)
        pow_roll = roll_ability_with_setting('pow', self.custom_setting)
        self.assertGreaterEqual(pow_roll, 3)
        self.assertLessEqual(pow_roll, 17)
        
        # APP: 1D20-5 (範囲: -4-15)
        app_roll = roll_ability_with_setting('app', self.custom_setting)
        self.assertGreaterEqual(app_roll, -4)
        self.assertLessEqual(app_roll, 15)
    
    def test_get_current_dice_settings(self):
        """現在のダイス設定取得テスト"""
        # デフォルト設定の取得
        settings = get_current_dice_settings(self.user)
        self.assertEqual(settings.setting_name, "標準6版設定")
        self.assertEqual(settings.str_dice_count, 3)
        self.assertEqual(settings.str_dice_sides, 6)
        self.assertEqual(settings.str_bonus, 0)
        
        # カスタム設定をデフォルトに変更
        self.custom_setting.set_as_default()
        
        settings = get_current_dice_settings(self.user)
        self.assertEqual(settings.setting_name, "カスタム設定")
        self.assertEqual(settings.str_dice_count, 4)
        self.assertEqual(settings.str_dice_sides, 6)
        self.assertEqual(settings.str_bonus, -2)
    
    def test_calculate_abilities_with_setting(self):
        """設定を使った全能力値計算テスト"""
        abilities = calculate_abilities_with_setting(self.standard_setting)
        
        # 戻り値の構造確認
        expected_keys = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for key in expected_keys:
            self.assertIn(key, abilities)
        
        # 標準設定での範囲確認
        self.assertGreaterEqual(abilities['str'], 3)
        self.assertLessEqual(abilities['str'], 18)
        self.assertGreaterEqual(abilities['siz'], 8)
        self.assertLessEqual(abilities['siz'], 18)
        self.assertGreaterEqual(abilities['edu'], 6)
        self.assertLessEqual(abilities['edu'], 21)
    
    def test_calculate_abilities_with_custom_setting(self):
        """カスタム設定での全能力値計算テスト"""
        abilities = calculate_abilities_with_setting(self.custom_setting)
        
        # カスタム設定での範囲確認
        self.assertGreaterEqual(abilities['str'], 2)  # 4D6-2
        self.assertLessEqual(abilities['str'], 22)
        self.assertGreaterEqual(abilities['con'], 7)  # 5D4+2
        self.assertLessEqual(abilities['con'], 22)
        self.assertGreaterEqual(abilities['pow'], 3)  # 2D8+1
        self.assertLessEqual(abilities['pow'], 17)
    
    def test_validate_dice_settings(self):
        """ダイス設定のバリデーションテスト"""
        # 正常な設定
        valid_settings = {
            'count': 3,
            'sides': 6,
            'bonus': 0
        }
        self.assertTrue(validate_dice_settings(valid_settings))
        
        # 境界値テスト
        boundary_settings = [
            {'count': 1, 'sides': 2, 'bonus': -50},  # 最小値
            {'count': 10, 'sides': 100, 'bonus': 50},  # 最大値
        ]
        for settings in boundary_settings:
            self.assertTrue(validate_dice_settings(settings))
        
        # 不正な設定
        invalid_settings = [
            {'count': 0, 'sides': 6, 'bonus': 0},     # ダイス数が0
            {'count': 11, 'sides': 6, 'bonus': 0},    # ダイス数が上限超過
            {'count': 3, 'sides': 1, 'bonus': 0},     # ダイス面数が1
            {'count': 3, 'sides': 101, 'bonus': 0},   # ダイス面数が上限超過
            {'count': 3, 'sides': 6, 'bonus': -51},   # ボーナスが下限未満
            {'count': 3, 'sides': 6, 'bonus': 51},    # ボーナスが上限超過
        ]
        for settings in invalid_settings:
            self.assertFalse(validate_dice_settings(settings))
    
    def test_dice_setting_consistency(self):
        """ダイス設定の一貫性テスト"""
        # 同じ設定で複数回ロールして一貫性を確認
        setting = self.standard_setting
        
        # STRで100回ロールして範囲内かチェック
        for _ in range(100):
            roll = roll_ability_with_setting('str', setting)
            self.assertGreaterEqual(roll, 3)
            self.assertLessEqual(roll, 18)
        
        # SIZで100回ロールして範囲内かチェック
        for _ in range(100):
            roll = roll_ability_with_setting('siz', setting)
            self.assertGreaterEqual(roll, 8)
            self.assertLessEqual(roll, 18)
    
    def test_extreme_dice_settings(self):
        """極端なダイス設定のテスト"""
        # 極端な設定を作成
        extreme_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="極端設定",
            str_dice_count=10, str_dice_sides=100, str_bonus=50,
            con_dice_count=1, con_dice_sides=2, con_bonus=-50,
            pow_dice_count=5, pow_dice_sides=20, pow_bonus=0,
            dex_dice_count=3, dex_dice_sides=6, dex_bonus=0,
            app_dice_count=3, app_dice_sides=6, app_bonus=0,
            siz_dice_count=2, siz_dice_sides=6, siz_bonus=6,
            int_dice_count=2, int_dice_sides=6, int_bonus=6,
            edu_dice_count=3, edu_dice_sides=6, edu_bonus=3
        )
        
        # STR: 10D100+50 (範囲: 60-1050)
        str_roll = roll_ability_with_setting('str', extreme_setting)
        self.assertGreaterEqual(str_roll, 60)
        self.assertLessEqual(str_roll, 1050)
        
        # CON: 1D2-50 (範囲: -49～-48)
        con_roll = roll_ability_with_setting('con', extreme_setting)
        self.assertGreaterEqual(con_roll, -49)
        self.assertLessEqual(con_roll, -48)
        
        # POW: 5D20 (範囲: 5-100)
        pow_roll = roll_ability_with_setting('pow', extreme_setting)
        self.assertGreaterEqual(pow_roll, 5)
        self.assertLessEqual(pow_roll, 100)
    
    def test_setting_not_found_handling(self):
        """設定が見つからない場合のハンドリングテスト"""
        # 存在しないユーザーでの設定取得
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # デフォルト設定がない場合のテスト
        settings = get_current_dice_settings(other_user)
        self.assertIsNone(settings)
    
    def test_ability_name_validation(self):
        """能力値名のバリデーションテスト"""
        valid_abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        
        for ability in valid_abilities:
            # 正常にロールできることを確認
            try:
                result = roll_ability_with_setting(ability, self.standard_setting)
                self.assertIsInstance(result, int)
            except Exception as e:
                self.fail(f"Valid ability '{ability}' raised an exception: {e}")
        
        # 無効な能力値名のテスト
        invalid_abilities = ['strength', 'constitution', 'power', 'xyz', '', None]
        
        for ability in invalid_abilities:
            with self.assertRaises((ValueError, AttributeError, TypeError)):
                roll_ability_with_setting(ability, self.standard_setting)
    
    def test_dice_setting_modification_real_time(self):
        """ダイス設定のリアルタイム変更テスト"""
        # 設定を動的に変更
        self.standard_setting.str_dice_count = 5
        self.standard_setting.str_dice_sides = 8
        self.standard_setting.str_bonus = 10
        self.standard_setting.save()
        
        # 変更が即座に反映されることを確認
        str_roll = roll_ability_with_setting('str', self.standard_setting)
        # 5D8+10 (範囲: 15-50)
        self.assertGreaterEqual(str_roll, 15)
        self.assertLessEqual(str_roll, 50)
        
        # 複数回テストして一貫性を確認
        for _ in range(20):
            roll = roll_ability_with_setting('str', self.standard_setting)
            self.assertGreaterEqual(roll, 15)
            self.assertLessEqual(roll, 50)
    
    def test_concurrent_dice_settings(self):
        """複数の設定の並行使用テスト"""
        # 2つの異なる設定を同時に使用
        abilities_standard = calculate_abilities_with_setting(self.standard_setting)
        abilities_custom = calculate_abilities_with_setting(self.custom_setting)
        
        # 異なる結果が期待される（ランダムなので完全一致は極めて低確率）
        # 少なくとも設定が独立して動作していることを確認
        self.assertIsInstance(abilities_standard, dict)
        self.assertIsInstance(abilities_custom, dict)
        
        # 設定値の違いが反映されていることを確認
        # STR設定比較: 標準(3D6) vs カスタム(4D6-2)
        # 複数回テストして範囲の違いを確認
        standard_results = []
        custom_results = []
        
        for _ in range(50):
            standard_results.append(roll_ability_with_setting('str', self.standard_setting))
            custom_results.append(roll_ability_with_setting('str', self.custom_setting))
        
        # 範囲の確認
        self.assertTrue(all(3 <= r <= 18 for r in standard_results))
        self.assertTrue(all(2 <= r <= 22 for r in custom_results))


class DiceSettingUtilityFunctionTestCase(TestCase):
    """ダイス設定のユーティリティ関数テスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='utiluser',
            email='util@example.com',
            password='testpass123'
        )
    
    def test_get_dice_count_function(self):
        """ダイス数取得関数のテスト"""
        setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_count=5,
            con_dice_count=3,
            pow_dice_count=2
        )
        
        # この関数は実装される予定
        from accounts.utils import get_dice_count
        
        self.assertEqual(get_dice_count('str', setting), 5)
        self.assertEqual(get_dice_count('con', setting), 3)
        self.assertEqual(get_dice_count('pow', setting), 2)
    
    def test_get_dice_sides_function(self):
        """ダイス面数取得関数のテスト"""
        setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_sides=8,
            con_dice_sides=10,
            pow_dice_sides=12
        )
        
        # この関数は実装される予定
        from accounts.utils import get_dice_sides
        
        self.assertEqual(get_dice_sides('str', setting), 8)
        self.assertEqual(get_dice_sides('con', setting), 10)
        self.assertEqual(get_dice_sides('pow', setting), 12)
    
    def test_get_dice_bonus_function(self):
        """ダイスボーナス取得関数のテスト"""
        setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_bonus=5,
            con_bonus=-2,
            pow_bonus=0
        )
        
        # この関数は実装される予定
        from accounts.utils import get_dice_bonus
        
        self.assertEqual(get_dice_bonus('str', setting), 5)
        self.assertEqual(get_dice_bonus('con', setting), -2)
        self.assertEqual(get_dice_bonus('pow', setting), 0)


class DiceSettingIntegrationTestCase(TestCase):
    """ダイス設定の統合テスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='intuser',
            email='int@example.com',
            password='testpass123'
        )
    
    def test_complete_character_creation_workflow(self):
        """完全なキャラクター作成ワークフローテスト"""
        # 1. カスタムダイス設定を作成
        custom_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="統合テスト設定",
            is_default=True,
            str_dice_count=4, str_dice_sides=6, str_bonus=-1,
            con_dice_count=4, con_dice_sides=6, con_bonus=-1,
            pow_dice_count=4, pow_dice_sides=6, pow_bonus=-1,
            dex_dice_count=4, dex_dice_sides=6, dex_bonus=-1,
            app_dice_count=4, app_dice_sides=6, app_bonus=-1,
            siz_dice_count=3, siz_dice_sides=6, siz_bonus=3,
            int_dice_count=3, int_dice_sides=6, int_bonus=3,
            edu_dice_count=4, edu_dice_sides=6, edu_bonus=0
        )
        
        # 2. 設定を使って能力値を生成
        abilities = calculate_abilities_with_setting(custom_setting)
        
        # 3. 生成された能力値の妥当性確認
        self.assertGreaterEqual(abilities['str'], 3)  # 4D6-1の最小値
        self.assertLessEqual(abilities['str'], 23)    # 4D6-1の最大値
        
        # 4. 同じ設定で複数回生成して一貫性確認
        for _ in range(10):
            test_abilities = calculate_abilities_with_setting(custom_setting)
            for ability_name, value in test_abilities.items():
                self.assertIsInstance(value, int)
                self.assertGreater(value, -100)  # 極端に低い値でないことを確認
                self.assertLess(value, 200)     # 極端に高い値でないことを確認
    
    def test_setting_persistence_and_retrieval(self):
        """設定の永続化と取得テスト"""
        # 設定を保存
        original_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="永続化テスト",
            is_default=True,
            str_dice_count=3, str_dice_sides=8, str_bonus=2
        )
        
        # データベースから再取得
        retrieved_setting = get_current_dice_settings(self.user)
        
        # 設定が正しく保存・取得されることを確認
        self.assertEqual(retrieved_setting.setting_name, "永続化テスト")
        self.assertEqual(retrieved_setting.str_dice_count, 3)
        self.assertEqual(retrieved_setting.str_dice_sides, 8)
        self.assertEqual(retrieved_setting.str_bonus, 2)
        
        # 取得した設定でロールが正常に動作することを確認
        str_roll = roll_ability_with_setting('str', retrieved_setting)
        # 3D8+2 (範囲: 5-26)
        self.assertGreaterEqual(str_roll, 5)
        self.assertLessEqual(str_roll, 26)