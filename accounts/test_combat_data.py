"""
戦闘データ管理システムのテストスイート
クトゥルフ神話TRPG 6版の戦闘データ管理機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CharacterSheet
from .character_models import CharacterSheet6th, CharacterEquipment

User = get_user_model()


class CombatDataCalculationTestCase(TestCase):
    """戦闘データ計算のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=15,  # STR 15
            con_value=12,
            pow_value=10,
            dex_value=13,
            app_value=11,
            siz_value=14,  # SIZ 14, STR+SIZ=29
            int_value=16,
            edu_value=12
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_damage_bonus_calculation_6th(self):
        """6版ダメージボーナス計算テスト"""
        # STR 15 + SIZ 14 = 29 → +1D4
        expected_damage_bonus = "+1D4"
        self.assertEqual(self.character_6th.damage_bonus, expected_damage_bonus)
    
    def test_damage_bonus_various_values(self):
        """様々なSTR+SIZ値でのダメージボーナステスト"""
        test_cases = [
            (5, 5, "-1D6"),    # 10 (<=12)
            (8, 4, "-1D6"),    # 12 (<=12)
            (10, 6, "-1D4"),   # 16 (<=16)
            (10, 10, "+0"),    # 20 (<=24)
            (12, 13, "+1D4"),  # 25 (<=32)
            (15, 18, "+1D6"),  # 33 (<=40)
            (20, 20, "+1D6"),  # 40 (<=40)
        ]
        
        for str_val, siz_val, expected_bonus in test_cases:
            with self.subTest(str=str_val, siz=siz_val):
                self.character.str_value = str_val
                self.character.siz_value = siz_val
                self.character.save()
                
                # 6版データの再計算
                self.character_6th.save()
                self.character_6th.refresh_from_db()
                self.assertEqual(self.character_6th.damage_bonus, expected_bonus)


class WeaponManagementTestCase(TestCase):
    """武器管理のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=60
        )
    
    def test_weapon_creation(self):
        """武器作成テスト"""
        weapon = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー',
            skill_name='拳銃',
            damage='1D10',
            base_range='15m',
            attacks_per_round=2,
            ammo=6,
            malfunction_number=100,
            description='信頼性の高い護身用拳銃'
        )
        
        self.assertEqual(weapon.name, '.38口径リボルバー')
        self.assertEqual(weapon.skill_name, '拳銃')
        self.assertEqual(weapon.damage, '1D10')
        self.assertEqual(weapon.base_range, '15m')
        self.assertEqual(weapon.attacks_per_round, 2)
        self.assertEqual(weapon.ammo, 6)
        self.assertEqual(weapon.malfunction_number, 100)
    
    def test_weapon_validation(self):
        """武器データのバリデーションテスト"""
        # 武器名必須チェック
        with self.assertRaises(ValidationError):
            weapon = CharacterEquipment(
                character_sheet=self.character,
                item_type='weapon',
                name='',  # 空文字
                skill_name='拳銃'
            )
            weapon.full_clean()
        
        # 攻撃回数の範囲チェック
        with self.assertRaises(ValidationError):
            weapon = CharacterEquipment(
                character_sheet=self.character,
                item_type='weapon',
                name='テスト武器',
                attacks_per_round=-1  # 負の値
            )
            weapon.full_clean()
    
    def test_multiple_weapons_management(self):
        """複数武器の管理テスト"""
        weapons_data = [
            {
                'name': '.38口径リボルバー',
                'skill_name': '拳銃',
                'damage': '1D10',
                'base_range': '15m',
                'attacks_per_round': 2,
                'ammo': 6
            },
            {
                'name': 'ショットガン',
                'skill_name': 'ショットガン',
                'damage': '2D6',
                'base_range': '50m',
                'attacks_per_round': 1,
                'ammo': 2
            },
            {
                'name': 'ナイフ',
                'skill_name': '格闘',
                'damage': '1D4+DB',
                'base_range': '接触',
                'attacks_per_round': 1,
                'ammo': None
            }
        ]
        
        created_weapons = []
        for weapon_data in weapons_data:
            weapon = CharacterEquipment.objects.create(
                character_sheet=self.character,
                item_type='weapon',
                **weapon_data
            )
            created_weapons.append(weapon)
        
        # 武器が正しく作成されているか確認
        weapons = CharacterEquipment.objects.filter(
            character_sheet=self.character,
            item_type='weapon'
        )
        self.assertEqual(weapons.count(), 3)
        
        # 各武器の詳細確認
        revolver = weapons.get(name='.38口径リボルバー')
        self.assertEqual(revolver.skill_name, '拳銃')
        self.assertEqual(revolver.ammo, 6)


class ArmorManagementTestCase(TestCase):
    """防具管理のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=60
        )
    
    def test_armor_creation(self):
        """防具作成テスト"""
        armor = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='armor',
            name='レザージャケット',
            armor_points=1,
            description='胴体部位を保護する革製ジャケット'
        )
        
        self.assertEqual(armor.name, 'レザージャケット')
        self.assertEqual(armor.armor_points, 1)
        self.assertEqual(armor.item_type, 'armor')
    
    def test_armor_validation(self):
        """防具バリデーションテスト"""
        # 防護点の範囲チェック
        with self.assertRaises(ValidationError):
            armor = CharacterEquipment(
                character_sheet=self.character,
                item_type='armor',
                name='テスト防具',
                armor_points=-1  # 負の値
            )
            armor.full_clean()
    
    def test_multiple_armor_pieces(self):
        """複数防具の管理テスト"""
        armor_data = [
            {'name': 'レザージャケット', 'armor_points': 1},
            {'name': 'ヘルメット', 'armor_points': 2},
            {'name': 'ブーツ', 'armor_points': 1}
        ]
        
        for armor_info in armor_data:
            CharacterEquipment.objects.create(
                character_sheet=self.character,
                item_type='armor',
                **armor_info
            )
        
        armors = CharacterEquipment.objects.filter(
            character_sheet=self.character,
            item_type='armor'
        )
        self.assertEqual(armors.count(), 3)
        
        # 総防護点の計算
        total_armor_points = sum(armor.armor_points for armor in armors)
        self.assertEqual(total_armor_points, 4)


class CombatDataAPITestCase(APITestCase):
    """戦闘データ管理APIのテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=60
        )
    
    def test_create_weapon_api(self):
        """武器作成APIテスト"""
        weapon_data = {
            'item_type': 'weapon',
            'name': '.38口径リボルバー',
            'skill_name': '拳銃',
            'damage': '1D10',
            'base_range': '15m',
            'attacks_per_round': 2,
            'ammo': 6,
            'malfunction_number': 100,
            'description': '信頼性の高い護身用拳銃'
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/equipment/',
            weapon_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], '.38口径リボルバー')
        self.assertEqual(response.data['item_type'], 'weapon')
    
    def test_create_armor_api(self):
        """防具作成APIテスト"""
        armor_data = {
            'item_type': 'armor',
            'name': 'レザージャケット',
            'armor_points': 1,
            'description': '胴体部位を保護する革製ジャケット'
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/equipment/',
            armor_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'レザージャケット')
        self.assertEqual(response.data['item_type'], 'armor')
    
    def test_get_weapons_list_api(self):
        """武器一覧取得APIテスト"""
        # テスト用武器を作成
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー',
            skill_name='拳銃',
            damage='1D10'
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/equipment/?type=weapon'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], '.38口径リボルバー')
    
    def test_get_armor_list_api(self):
        """防具一覧取得APIテスト"""
        # テスト用防具を作成
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='armor',
            name='レザージャケット',
            armor_points=1
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/equipment/?type=armor'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'レザージャケット')
    
    def test_get_combat_summary_api(self):
        """戦闘サマリー取得APIテスト"""
        # テスト用武器・防具を作成
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー',
            damage='1D10'
        )
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='armor',
            name='レザージャケット',
            armor_points=1
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/combat-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('damage_bonus', response.data)
        self.assertIn('total_armor_points', response.data)
        self.assertIn('weapons_count', response.data)
        self.assertIn('armor_count', response.data)
    
    def test_update_weapon_api(self):
        """武器更新APIテスト"""
        weapon = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー',
            damage='1D10',
            ammo=6
        )
        
        update_data = {
            'ammo': 5  # 弾数を更新
        }
        
        response = self.client.patch(
            f'/accounts/character-sheets/{self.character.id}/equipment/{weapon.id}/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ammo'], 5)
    
    def test_delete_equipment_api(self):
        """装備削除APIテスト"""
        weapon = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー'
        )
        
        response = self.client.delete(
            f'/accounts/character-sheets/{self.character.id}/equipment/{weapon.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 削除されたか確認
        with self.assertRaises(CharacterEquipment.DoesNotExist):
            CharacterEquipment.objects.get(id=weapon.id)


class CombatCalculationIntegrationTestCase(TestCase):
    """戦闘計算統合テストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='Test Investigator',
            edition='6th',
            age=25,
            str_value=15,
            con_value=12,
            pow_value=10,
            dex_value=13,
            app_value=11,
            siz_value=16,  # STR+SIZ=31 → +1D4
            int_value=16,
            edu_value=12
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_complete_combat_setup(self):
        """完全な戦闘セットアップのテスト"""
        # 武器作成
        revolver = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='.38口径リボルバー',
            skill_name='拳銃',
            damage='1D10',
            base_range='15m',
            attacks_per_round=2,
            ammo=6,
            malfunction_number=100
        )
        
        knife = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='weapon',
            name='ナイフ',
            skill_name='格闘',
            damage='1D4+DB',
            base_range='接触',
            attacks_per_round=1
        )
        
        # 防具作成
        leather_jacket = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='armor',
            name='レザージャケット',
            armor_points=1
        )
        
        # 戦闘データの確認
        weapons = CharacterEquipment.objects.filter(
            character_sheet=self.character,
            item_type='weapon'
        )
        armors = CharacterEquipment.objects.filter(
            character_sheet=self.character,
            item_type='armor'
        )
        
        self.assertEqual(weapons.count(), 2)
        self.assertEqual(armors.count(), 1)
        
        # ダメージボーナスの確認
        self.assertEqual(self.character_6th.damage_bonus, '+1D4')
        
        # 総防護点の確認
        total_armor = sum(armor.armor_points for armor in armors)
        self.assertEqual(total_armor, 1)
        
        # ナイフのダメージにDBが含まれているか確認
        self.assertIn('DB', knife.damage)