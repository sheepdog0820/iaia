"""
クトゥルフ神話TRPG 6版キャラクター作成のダイスロール設定機能のテスト

TDD: RED フェーズ - 失敗するテストケースを作成
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, CharacterDiceRollSetting
import json

User = get_user_model()


class CharacterDiceRollSettingModelTestCase(TestCase):
    """CharacterDiceRollSettingモデルのテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_dice_roll_setting_creation_success(self):
        """正常系: ダイスロール設定の作成成功"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="標準6版設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            con_dice_count=3,
            con_dice_sides=6,
            con_bonus=0,
            pow_dice_count=3,
            pow_dice_sides=6,
            pow_bonus=0,
            dex_dice_count=3,
            dex_dice_sides=6,
            dex_bonus=0,
            app_dice_count=3,
            app_dice_sides=6,
            app_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6,
            int_dice_count=2,
            int_dice_sides=6,
            int_bonus=6,
            edu_dice_count=3,
            edu_dice_sides=6,
            edu_bonus=3
        )
        
        self.assertEqual(dice_setting.setting_name, "標準6版設定")
        self.assertEqual(dice_setting.user, self.user)
        self.assertTrue(dice_setting.is_default)  # 最初の設定はデフォルト
        
        # STR設定の確認
        self.assertEqual(dice_setting.str_dice_count, 3)
        self.assertEqual(dice_setting.str_dice_sides, 6)
        self.assertEqual(dice_setting.str_bonus, 0)
        
        # SIZ設定の確認（2D6+6）
        self.assertEqual(dice_setting.siz_dice_count, 2)
        self.assertEqual(dice_setting.siz_dice_sides, 6)
        self.assertEqual(dice_setting.siz_bonus, 6)
    
    def test_dice_setting_validation_errors(self):
        """バリデーション: 不正データでのエラー"""
        # ダイス数が範囲外
        with self.assertRaises(ValidationError):
            dice_setting = CharacterDiceRollSetting(
                user=self.user,
                setting_name="無効設定",
                str_dice_count=0,  # 無効値: 1未満
                str_dice_sides=6,
                str_bonus=0
            )
            dice_setting.full_clean()
        
        # ダイス面数が範囲外
        with self.assertRaises(ValidationError):
            dice_setting = CharacterDiceRollSetting(
                user=self.user,
                setting_name="無効設定",
                str_dice_count=3,
                str_dice_sides=1,  # 無効値: 2未満
                str_bonus=0
            )
            dice_setting.full_clean()
        
        # ボーナス値が範囲外
        with self.assertRaises(ValidationError):
            dice_setting = CharacterDiceRollSetting(
                user=self.user,
                setting_name="無効設定",
                str_dice_count=3,
                str_dice_sides=6,
                str_bonus=100  # 無効値: 50超過
            )
            dice_setting.full_clean()
    
    def test_dice_setting_str_representation(self):
        """__str__メソッドのテスト"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0
        )
        
        expected_str = f"{self.user.username} - テスト設定"
        self.assertEqual(str(dice_setting), expected_str)
    
    def test_get_formula_methods(self):
        """ダイス式取得メソッドのテスト"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6,
            edu_dice_count=3,
            edu_dice_sides=6,
            edu_bonus=3
        )
        
        # STR: 3D6+0 → "3D6"
        self.assertEqual(dice_setting.get_str_formula(), "3D6")
        
        # SIZ: 2D6+6 → "2D6+6"
        self.assertEqual(dice_setting.get_siz_formula(), "2D6+6")
        
        # EDU: 3D6+3 → "3D6+3"
        self.assertEqual(dice_setting.get_edu_formula(), "3D6+3")
        
        # ボーナスが負の場合
        dice_setting.str_bonus = -2
        dice_setting.save()
        self.assertEqual(dice_setting.get_str_formula(), "3D6-2")
    
    def test_roll_ability_methods(self):
        """能力値ロールメソッドのテスト"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6
        )
        
        # STRロール（3D6: 3-18の範囲）
        str_roll = dice_setting.roll_str()
        self.assertGreaterEqual(str_roll, 3)
        self.assertLessEqual(str_roll, 18)
        
        # SIZロール（2D6+6: 8-18の範囲）
        siz_roll = dice_setting.roll_siz()
        self.assertGreaterEqual(siz_roll, 8)
        self.assertLessEqual(siz_roll, 18)
    
    def test_roll_all_abilities(self):
        """全能力値一括ロールのテスト"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="テスト設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            con_dice_count=3,
            con_dice_sides=6,
            con_bonus=0,
            pow_dice_count=3,
            pow_dice_sides=6,
            pow_bonus=0,
            dex_dice_count=3,
            dex_dice_sides=6,
            dex_bonus=0,
            app_dice_count=3,
            app_dice_sides=6,
            app_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6,
            int_dice_count=2,
            int_dice_sides=6,
            int_bonus=6,
            edu_dice_count=3,
            edu_dice_sides=6,
            edu_bonus=3
        )
        
        abilities = dice_setting.roll_all_abilities()
        
        # 戻り値の構造確認
        expected_keys = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu']
        for key in expected_keys:
            self.assertIn(key, abilities)
        
        # 6版の能力値範囲確認
        self.assertGreaterEqual(abilities['str'], 3)
        self.assertLessEqual(abilities['str'], 18)
        self.assertGreaterEqual(abilities['siz'], 8)  # 2D6+6の最小値
        self.assertLessEqual(abilities['siz'], 18)   # 2D6+6の最大値
        self.assertGreaterEqual(abilities['int'], 8)  # 2D6+6の最小値
        self.assertGreaterEqual(abilities['edu'], 6)  # 3D6+3の最小値
    
    def test_preset_creation_methods(self):
        """プリセット作成メソッドのテスト"""
        # 標準6版プリセット
        standard_preset = CharacterDiceRollSetting.create_standard_6th_preset(self.user)
        
        self.assertEqual(standard_preset.user, self.user)
        self.assertEqual(standard_preset.setting_name, "標準6版設定")
        self.assertTrue(standard_preset.is_default)
        
        # STR: 3D6
        self.assertEqual(standard_preset.str_dice_count, 3)
        self.assertEqual(standard_preset.str_dice_sides, 6)
        self.assertEqual(standard_preset.str_bonus, 0)
        
        # SIZ: 2D6+6
        self.assertEqual(standard_preset.siz_dice_count, 2)
        self.assertEqual(standard_preset.siz_dice_sides, 6)
        self.assertEqual(standard_preset.siz_bonus, 6)
        
        # 高能力値プリセット
        high_preset = CharacterDiceRollSetting.create_high_stats_6th_preset(self.user)
        
        self.assertEqual(high_preset.setting_name, "高能力値6版設定")
        self.assertFalse(high_preset.is_default)  # デフォルトではない
        
        # 高能力値設定の確認（4D6のベスト3など）
        self.assertGreaterEqual(high_preset.str_dice_count, 3)
    
    def test_default_setting_management(self):
        """デフォルト設定管理のテスト"""
        # 最初の設定
        setting1 = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="設定1",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0
        )
        self.assertTrue(setting1.is_default)
        
        # 2番目の設定
        setting2 = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="設定2", 
            str_dice_count=4,
            str_dice_sides=6,
            str_bonus=0
        )
        self.assertFalse(setting2.is_default)
        
        # デフォルト変更
        setting2.set_as_default()
        
        # 設定1のデフォルトが解除される
        setting1.refresh_from_db()
        self.assertFalse(setting1.is_default)
        self.assertTrue(setting2.is_default)
    
    def test_json_export_import(self):
        """JSON形式でのエクスポート・インポートテスト"""
        dice_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="エクスポートテスト",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            siz_dice_count=2,
            siz_dice_sides=6,
            siz_bonus=6
        )
        
        # エクスポートテスト
        exported_data = dice_setting.export_to_json()
        self.assertIsInstance(exported_data, str)
        
        # JSONとしてパース可能か確認
        parsed_data = json.loads(exported_data)
        self.assertEqual(parsed_data['setting_name'], "エクスポートテスト")
        self.assertEqual(parsed_data['str_dice_count'], 3)
        
        # インポートテスト
        new_user = User.objects.create_user(
            username='importuser',
            email='import@example.com',
            password='testpass123'
        )
        
        imported_setting = CharacterDiceRollSetting.import_from_json(
            user=new_user,
            json_data=exported_data,
            new_name="インポート設定"
        )
        
        self.assertEqual(imported_setting.user, new_user)
        self.assertEqual(imported_setting.setting_name, "インポート設定")
        self.assertEqual(imported_setting.str_dice_count, 3)
        self.assertEqual(imported_setting.siz_bonus, 6)


class CharacterDiceRollSettingAPITestCase(TestCase):
    """ダイスロール設定のAPI機能テストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='testpass123'
        )
    
    def test_get_user_dice_settings(self):
        """ユーザーのダイス設定一覧取得テスト"""
        # 複数の設定を作成
        setting1 = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="設定1",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0
        )
        
        setting2 = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="設定2",
            str_dice_count=4,
            str_dice_sides=6,
            str_bonus=0
        )
        
        # 一覧取得
        user_settings = CharacterDiceRollSetting.get_user_settings(self.user)
        
        self.assertEqual(len(user_settings), 2)
        self.assertIn(setting1, user_settings)
        self.assertIn(setting2, user_settings)
    
    def test_get_default_setting(self):
        """デフォルト設定取得テスト"""
        # デフォルト設定がない場合
        default_setting = CharacterDiceRollSetting.get_default_setting(self.user)
        self.assertIsNone(default_setting)
        
        # デフォルト設定を作成
        setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="デフォルト設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            is_default=True
        )
        
        # デフォルト設定取得
        default_setting = CharacterDiceRollSetting.get_default_setting(self.user)
        self.assertEqual(default_setting, setting)
    
    def test_setting_duplication(self):
        """設定の複製テスト"""
        original_setting = CharacterDiceRollSetting.objects.create(
            user=self.user,
            setting_name="元設定",
            str_dice_count=3,
            str_dice_sides=6,
            str_bonus=0,
            description="元の説明"
        )
        
        # 複製
        duplicated_setting = original_setting.duplicate(new_name="複製設定")
        
        self.assertEqual(duplicated_setting.user, self.user)
        self.assertEqual(duplicated_setting.setting_name, "複製設定")
        self.assertEqual(duplicated_setting.str_dice_count, 3)
        self.assertEqual(duplicated_setting.description, "元の説明")
        self.assertFalse(duplicated_setting.is_default)  # 複製はデフォルトでない
        self.assertNotEqual(duplicated_setting.id, original_setting.id)