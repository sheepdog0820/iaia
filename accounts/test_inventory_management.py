"""
所持品・装備管理システムのテストスイート
クトゥルフ神話TRPG 6版の所持品・装備管理機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import CharacterSheet
from .character_models import CharacterSheet6th, CharacterEquipment

User = get_user_model()


class InventoryModelTestCase(TestCase):
    """所持品モデルの基本テストケース"""
    
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
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10
        )
    
    def test_inventory_model_creation(self):
        """所持品モデルの作成テスト"""
        # 6版データに財務情報を追加して動作確認
        character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
        
        character_6th.cash = Decimal('1000.00')
        character_6th.assets = Decimal('5000.00')
        character_6th.annual_income = Decimal('30000.00')
        character_6th.real_estate = "アーカム市内のアパート"
        character_6th.save()
        
        # データが正しく保存されたか確認
        character_6th.refresh_from_db()
        self.assertEqual(character_6th.cash, Decimal('1000.00'))
        self.assertEqual(character_6th.assets, Decimal('5000.00'))
        self.assertEqual(character_6th.annual_income, Decimal('30000.00'))
        self.assertEqual(character_6th.real_estate, "アーカム市内のアパート")


class FinancialDataTestCase(TestCase):
    """財務データ管理のテストケース"""
    
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
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_financial_data_storage(self):
        """財務データの保存テスト"""
        # 6版データに財務情報を追加
        self.character_6th.cash = Decimal('1500.00')
        self.character_6th.assets = Decimal('10000.00')
        self.character_6th.annual_income = Decimal('45000.00')
        self.character_6th.real_estate = "ボストンの小さな家"
        self.character_6th.save()
        
        # データ確認
        self.character_6th.refresh_from_db()
        self.assertEqual(self.character_6th.cash, Decimal('1500.00'))
        self.assertEqual(self.character_6th.assets, Decimal('10000.00'))
        self.assertEqual(self.character_6th.annual_income, Decimal('45000.00'))
        self.assertEqual(self.character_6th.real_estate, "ボストンの小さな家")
    
    def test_financial_data_validation(self):
        """財務データのバリデーションテスト"""
        # 負の金額はエラー
        self.character_6th.cash = Decimal('-100.00')
        with self.assertRaises(ValidationError):
            self.character_6th.full_clean()
        
        # 資産の上限チェック（10億円以上はエラー）
        self.character_6th.cash = Decimal('1000000000.00')
        with self.assertRaises(ValidationError):
            self.character_6th.full_clean()
    
    def test_total_wealth_calculation(self):
        """総資産の計算テスト"""
        self.character_6th.cash = Decimal('2000.00')
        self.character_6th.assets = Decimal('15000.00')
        self.character_6th.save()
        
        total_wealth = self.character_6th.calculate_total_wealth()
        self.assertEqual(total_wealth, Decimal('17000.00'))


class ItemManagementTestCase(TestCase):
    """アイテム管理のテストケース"""
    
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
    
    def test_item_creation(self):
        """アイテム作成テスト"""
        item = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='医療キット',
            quantity=1,
            weight=2.5,
            description='応急手当に+20%のボーナス'
        )
        
        self.assertEqual(item.name, '医療キット')
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.weight, 2.5)
        self.assertEqual(item.item_type, 'item')
    
    def test_item_quantity_management(self):
        """アイテム数量管理テスト"""
        # 複数個のアイテムを作成
        item = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='懐中電灯',
            quantity=3,
            weight=0.5
        )
        
        # 数量の更新
        item.quantity = 2
        item.save()
        
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        
        # 総重量の計算
        total_weight = item.quantity * item.weight
        self.assertEqual(total_weight, 1.0)
    
    def test_item_validation(self):
        """アイテムバリデーションテスト"""
        # 負の数量はエラー
        with self.assertRaises(ValidationError):
            item = CharacterEquipment(
                character_sheet=self.character,
                item_type='item',
                name='テストアイテム',
                quantity=-1
            )
            item.full_clean()
        
        # 負の重量はエラー
        with self.assertRaises(ValidationError):
            item = CharacterEquipment(
                character_sheet=self.character,
                item_type='item',
                name='テストアイテム',
                weight=-1.0
            )
            item.full_clean()
    
    def test_multiple_items_management(self):
        """複数アイテムの管理テスト"""
        items_data = [
            {'name': '懐中電灯', 'quantity': 2, 'weight': 0.5},
            {'name': 'ロープ（50フィート）', 'quantity': 1, 'weight': 5.0},
            {'name': '水筒', 'quantity': 1, 'weight': 1.0},
            {'name': '非常食（3日分）', 'quantity': 3, 'weight': 1.5}
        ]
        
        for item_data in items_data:
            CharacterEquipment.objects.create(
                character_sheet=self.character,
                item_type='item',
                **item_data
            )
        
        # 全アイテムの確認
        items = CharacterEquipment.objects.filter(
            character_sheet=self.character,
            item_type='item'
        )
        self.assertEqual(items.count(), 4)
        
        # 総重量の計算
        total_weight = sum(
            item.weight * item.quantity 
            for item in items 
            if item.weight is not None
        )
        self.assertEqual(total_weight, 11.5)  # 1.0 + 5.0 + 1.0 + 4.5 = 11.5


class InventoryAPITestCase(APITestCase):
    """所持品管理APIのテストケース"""
    
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
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_get_financial_summary_api(self):
        """財務サマリー取得APIテスト"""
        # 財務データを設定
        self.character_6th.cash = Decimal('3000.00')
        self.character_6th.assets = Decimal('20000.00')
        self.character_6th.annual_income = Decimal('60000.00')
        self.character_6th.real_estate = "マサチューセッツ州の農場"
        self.character_6th.save()
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/financial-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cash'], '3000.00')
        self.assertEqual(response.data['assets'], '20000.00')
        self.assertEqual(response.data['annual_income'], '60000.00')
        self.assertEqual(response.data['real_estate'], "マサチューセッツ州の農場")
        self.assertEqual(response.data['total_wealth'], '23000.00')
    
    def test_update_financial_data_api(self):
        """財務データ更新APIテスト"""
        update_data = {
            'cash': '5000.00',
            'assets': '30000.00',
            'annual_income': '75000.00',
            'real_estate': 'ニューイングランドの別荘'
        }
        
        response = self.client.patch(
            f'/accounts/character-sheets/{self.character.id}/update-financial-data/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # データが更新されたか確認
        self.character_6th.refresh_from_db()
        self.assertEqual(self.character_6th.cash, Decimal('5000.00'))
        self.assertEqual(self.character_6th.assets, Decimal('30000.00'))
        self.assertEqual(self.character_6th.annual_income, Decimal('75000.00'))
        self.assertEqual(self.character_6th.real_estate, 'ニューイングランドの別荘')
    
    def test_create_item_api(self):
        """アイテム作成APIテスト"""
        item_data = {
            'item_type': 'item',
            'name': '古い日記',
            'quantity': 1,
            'weight': 0.3,
            'description': '謎めいた記述が含まれている'
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/equipment/',
            item_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], '古い日記')
        self.assertEqual(response.data['item_type'], 'item')
    
    def test_get_inventory_summary_api(self):
        """インベントリサマリー取得APIテスト"""
        # 複数のアイテムを作成
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='懐中電灯',
            quantity=2,
            weight=0.5
        )
        CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='ロープ',
            quantity=1,
            weight=5.0
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/inventory-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data)
        self.assertIn('total_items', response.data)
        self.assertIn('total_weight', response.data)
        self.assertEqual(response.data['total_items'], 2)
        self.assertEqual(response.data['total_weight'], 6.0)
    
    def test_bulk_update_items_api(self):
        """アイテム一括更新APIテスト"""
        # 既存アイテムを作成
        item1 = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='懐中電灯',
            quantity=2
        )
        item2 = CharacterEquipment.objects.create(
            character_sheet=self.character,
            item_type='item',
            name='ロープ',
            quantity=1
        )
        
        update_data = {
            'items': [
                {'id': item1.id, 'quantity': 3},
                {'id': item2.id, 'quantity': 2}
            ]
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/bulk-update-items/',
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        
        # 数量が更新されたか確認
        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(item1.quantity, 3)
        self.assertEqual(item2.quantity, 2)


class InventoryIntegrationTestCase(TestCase):
    """所持品管理統合テストケース"""
    
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
            age=35,
            occupation='私立探偵',
            str_value=12,
            con_value=14,
            pow_value=15,
            dex_value=13,
            app_value=11,
            siz_value=10,
            int_value=16,
            edu_value=18
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_complete_inventory_setup(self):
        """完全なインベントリセットアップのテスト"""
        # 財務情報の設定
        self.character_6th.cash = Decimal('1200.00')
        self.character_6th.assets = Decimal('8000.00')
        self.character_6th.annual_income = Decimal('35000.00')
        self.character_6th.real_estate = "アーカムの小さな事務所"
        self.character_6th.save()
        
        # 装備品の作成
        equipment_data = [
            # 武器
            {
                'item_type': 'weapon',
                'name': '.38口径リボルバー',
                'quantity': 1,
                'weight': 1.0,
                'damage': '1D10',
                'skill_name': '拳銃'
            },
            # 防具
            {
                'item_type': 'armor',
                'name': 'トレンチコート',
                'quantity': 1,
                'weight': 2.0,
                'armor_points': 1
            },
            # 一般アイテム
            {
                'item_type': 'item',
                'name': '虫眼鏡',
                'quantity': 1,
                'weight': 0.1,
                'description': '目星判定に+5%'
            },
            {
                'item_type': 'item',
                'name': 'ノートと鉛筆',
                'quantity': 1,
                'weight': 0.2,
                'description': '調査記録用'
            },
            {
                'item_type': 'item',
                'name': '懐中電灯',
                'quantity': 2,
                'weight': 0.5,
                'description': '予備電池付き'
            }
        ]
        
        created_items = []
        for item_data in equipment_data:
            item = CharacterEquipment.objects.create(
                character_sheet=self.character,
                **item_data
            )
            created_items.append(item)
        
        # 全装備の確認
        all_equipment = CharacterEquipment.objects.filter(
            character_sheet=self.character
        )
        self.assertEqual(all_equipment.count(), 5)
        
        # タイプ別の確認
        weapons = all_equipment.filter(item_type='weapon')
        armors = all_equipment.filter(item_type='armor')
        items = all_equipment.filter(item_type='item')
        
        self.assertEqual(weapons.count(), 1)
        self.assertEqual(armors.count(), 1)
        self.assertEqual(items.count(), 3)
        
        # 総重量の計算
        total_weight = sum(
            item.weight * item.quantity 
            for item in all_equipment 
            if item.weight is not None
        )
        self.assertAlmostEqual(total_weight, 4.3, places=1)  # 1.0 + 2.0 + 0.1 + 0.2 + 1.0
        
        # 総資産の確認
        total_wealth = self.character_6th.calculate_total_wealth()
        self.assertEqual(total_wealth, Decimal('9200.00'))
    
    def test_inventory_weight_limit(self):
        """所持重量制限のテスト"""
        # STR12の場合の運搬能力を計算
        carry_capacity = self.character.calculate_carry_capacity()
        
        # 重いアイテムを複数作成
        heavy_items = [
            {'name': '大型テント', 'weight': 15.0, 'quantity': 1},
            {'name': '登山用具一式', 'weight': 10.0, 'quantity': 1},
            {'name': '食料（1週間分）', 'weight': 7.0, 'quantity': 1}
        ]
        
        total_weight = 0
        for item_data in heavy_items:
            CharacterEquipment.objects.create(
                character_sheet=self.character,
                item_type='item',
                **item_data
            )
            total_weight += item_data['weight'] * item_data['quantity']
        
        # 総重量が運搬能力を超えているかチェック
        is_overloaded = total_weight > carry_capacity
        
        # 必要に応じて移動ペナルティを計算
        if is_overloaded:
            movement_penalty = self.character.calculate_movement_penalty(total_weight)
            self.assertGreater(movement_penalty, 0)