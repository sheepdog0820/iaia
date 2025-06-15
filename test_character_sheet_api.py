#!/usr/bin/env python3
"""
キャラクターシートAPI テストスクリプト

実装したキャラクターシートREST APIの動作テスト
"""

import os
import sys
import django
import json
import requests
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkham_nexus.settings')
django.setup()

from accounts.models import CharacterSheet, CharacterSheet6th, CharacterSheet7th, CharacterSkill, CharacterEquipment

User = get_user_model()


class CharacterSheetAPITest(APITestCase):
    """キャラクターシートAPI統合テスト"""
    
    def setUp(self):
        """テストデータ準備"""
        # テストユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            nickname='テストユーザー'
        )
        
        # 認証
        self.client.force_authenticate(user=self.user)
        
        # テスト用キャラクターシートデータ
        self.character_data_6th = {
            'edition': '6th',
            'name': 'テスト探索者6版',
            'player_name': 'テストプレイヤー',
            'age': 28,
            'gender': '男性',
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 65,
            'con_value': 70,
            'pow_value': 75,
            'dex_value': 80,
            'app_value': 60,
            'siz_value': 65,
            'int_value': 85,
            'edu_value': 80,
            'hit_points_current': 13,
            'magic_points_current': 15,
            'sanity_current': 75,
            'notes': '6版テストキャラクター'
        }
        
        self.character_data_7th = {
            'edition': '7th',
            'name': 'テスト探索者7版',
            'player_name': 'テストプレイヤー',
            'age': 25,
            'gender': '女性',
            'occupation': '大学生',
            'birthplace': '大阪',
            'residence': '京都',
            'str_value': 60,
            'con_value': 65,
            'pow_value': 70,
            'dex_value': 85,
            'app_value': 80,
            'siz_value': 55,
            'int_value': 90,
            'edu_value': 85,
            'hit_points_current': 12,
            'magic_points_current': 14,
            'sanity_current': 70,
            'notes': '7版テストキャラクター',
            'seventh_edition_data': {
                'luck_points': 75,
                'personal_description': '好奇心旺盛な大学生',
                'ideology_beliefs': '真実を追求する',
                'significant_people': '指導教授',
                'meaningful_locations': '大学図書館',
                'treasured_possessions': '祖母の指輪',
                'traits': '几帳面',
                'injuries_scars': 'なし',
                'phobias_manias': '高所恐怖症'
            }
        }
    
    def test_create_6th_edition_character(self):
        """6版キャラクターシート作成テスト"""
        print("\n=== 6版キャラクターシート作成テスト ===")
        
        url = '/api/accounts/character-sheets/'
        response = self.client.post(url, self.character_data_6th, format='json')
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['edition'], '6th')
        self.assertEqual(response.data['name'], 'テスト探索者6版')
        
        # データベースでも確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertEqual(character.edition, '6th')
        self.assertEqual(character.hit_points_max, 13)  # (CON + SIZ) / 10
        self.assertEqual(character.magic_points_max, 15)  # POW / 5
        
        return response.data['id']
    
    def test_create_7th_edition_character(self):
        """7版キャラクターシート作成テスト"""
        print("\n=== 7版キャラクターシート作成テスト ===")
        
        url = '/api/accounts/character-sheets/'
        response = self.client.post(url, self.character_data_7th, format='json')
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['edition'], '7th')
        self.assertEqual(response.data['name'], 'テスト探索者7版')
        
        # 7版固有データの確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(character, 'seventh_edition_data'))
        
        return response.data['id']
    
    def test_list_character_sheets(self):
        """キャラクターシート一覧取得テスト"""
        print("\n=== キャラクターシート一覧取得テスト ===")
        
        # まずキャラクター作成
        self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        self.client.post('/api/accounts/character-sheets/', self.character_data_7th, format='json')
        
        url = '/api/accounts/character-sheets/'
        response = self.client.get(url)
        
        print(f"ステータスコード: {response.status_code}")
        print(f"取得件数: {len(response.data)}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_character_sheet_detail(self):
        """キャラクターシート詳細取得テスト"""
        print("\n=== キャラクターシート詳細取得テスト ===")
        
        # キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_7th, format='json')
        character_id = create_response.data['id']
        
        url = f'/api/accounts/character-sheets/{character_id}/'
        response = self.client.get(url)
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], character_id)
        self.assertIn('abilities', response.data)
        self.assertIn('skills', response.data)
        self.assertIn('equipment', response.data)
    
    def test_update_character_sheet(self):
        """キャラクターシート更新テスト"""
        print("\n=== キャラクターシート更新テスト ===")
        
        # キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        character_id = create_response.data['id']
        
        # 更新データ
        update_data = {
            'name': '更新された探索者',
            'age': 30,
            'hit_points_current': 10,
            'sanity_current': 65,
            'notes': '更新されたメモ'
        }
        
        url = f'/api/accounts/character-sheets/{character_id}/'
        response = self.client.patch(url, update_data, format='json')
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '更新された探索者')
        self.assertEqual(response.data['age'], 30)
        self.assertEqual(response.data['hit_points_current'], 10)
    
    def test_delete_character_sheet(self):
        """キャラクターシート削除テスト"""
        print("\n=== キャラクターシート削除テスト ===")
        
        # キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        character_id = create_response.data['id']
        
        url = f'/api/accounts/character-sheets/{character_id}/'
        response = self.client.delete(url)
        
        print(f"ステータスコード: {response.status_code}")
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 削除確認
        self.assertFalse(CharacterSheet.objects.filter(id=character_id).exists())
    
    def test_create_character_version(self):
        """キャラクターシートバージョン作成テスト"""
        print("\n=== キャラクターシートバージョン作成テスト ===")
        
        # 元キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        original_id = create_response.data['id']
        
        # バージョン作成
        version_data = {
            'hit_points_current': 8,
            'sanity_current': 60,
            'notes': 'バージョン2のメモ'
        }
        
        url = f'/api/accounts/character-sheets/{original_id}/create_version/'
        response = self.client.post(url, version_data, format='json')
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['version'], 2)
        self.assertEqual(response.data['parent_sheet'], original_id)
        self.assertEqual(response.data['hit_points_current'], 8)
    
    def test_filter_by_edition(self):
        """版別フィルタリングテスト"""
        print("\n=== 版別フィルタリングテスト ===")
        
        # 両版のキャラクター作成
        self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        self.client.post('/api/accounts/character-sheets/', self.character_data_7th, format='json')
        
        # 6版のみ取得
        url = '/api/accounts/character-sheets/by_edition/?edition=6th'
        response = self.client.get(url)
        
        print(f"6版フィルタ - ステータスコード: {response.status_code}")
        print(f"6版フィルタ - 取得件数: {len(response.data)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['edition'], '6th')
        
        # 7版のみ取得
        url = '/api/accounts/character-sheets/by_edition/?edition=7th'
        response = self.client.get(url)
        
        print(f"7版フィルタ - ステータスコード: {response.status_code}")
        print(f"7版フィルタ - 取得件数: {len(response.data)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['edition'], '7th')
    
    def test_character_skills(self):
        """キャラクタースキルテスト"""
        print("\n=== キャラクタースキルテスト ===")
        
        # キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_6th, format='json')
        character_id = create_response.data['id']
        
        # スキル追加
        skill_data = {
            'skill_name': '目星',
            'base_value': 25,
            'occupation_points': 40,
            'interest_points': 10,
            'other_points': 0
        }
        
        url = f'/api/accounts/character-sheets/{character_id}/skills/'
        response = self.client.post(url, skill_data, format='json')
        
        print(f"スキル作成 - ステータスコード: {response.status_code}")
        print(f"スキル作成 - レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['skill_name'], '目星')
        self.assertEqual(response.data['current_value'], 75)  # 25+40+10+0
        
        # スキル一覧取得
        response = self.client.get(url)
        
        print(f"スキル一覧 - ステータスコード: {response.status_code}")
        print(f"スキル一覧 - 取得件数: {len(response.data)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_character_equipment(self):
        """キャラクター装備テスト"""
        print("\n=== キャラクター装備テスト ===")
        
        # キャラクター作成
        create_response = self.client.post('/api/accounts/character-sheets/', self.character_data_7th, format='json')
        character_id = create_response.data['id']
        
        # 装備追加
        equipment_data = {
            'item_type': 'weapon',
            'name': '.38リボルバー',
            'skill_name': '拳銃',
            'damage': '1d10',
            'base_range': '15m',
            'attacks_per_round': 3,
            'ammo': 6,
            'malfunction_number': 100,
            'description': '一般的な回転式拳銃',
            'quantity': 1
        }
        
        url = f'/api/accounts/character-sheets/{character_id}/equipment/'
        response = self.client.post(url, equipment_data, format='json')
        
        print(f"装備作成 - ステータスコード: {response.status_code}")
        print(f"装備作成 - レスポンス: {json.dumps(response.data, ensure_ascii=False, indent=2)}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], '.38リボルバー')
        self.assertEqual(response.data['item_type'], 'weapon')
        
        # 装備一覧取得
        response = self.client.get(url)
        
        print(f"装備一覧 - ステータスコード: {response.status_code}")
        print(f"装備一覧 - 取得件数: {len(response.data)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


def run_tests():
    """テスト実行"""
    print("キャラクターシートAPI統合テスト開始")
    print("=" * 50)
    
    # テストケース作成
    test = CharacterSheetAPITest()
    test.setUp()
    
    # 各テスト実行
    try:
        test.test_create_6th_edition_character()
        test.test_create_7th_edition_character()
        test.test_list_character_sheets()
        test.test_get_character_sheet_detail()
        test.test_update_character_sheet()
        test.test_create_character_version()
        test.test_filter_by_edition()
        test.test_character_skills()
        test.test_character_equipment()
        test.test_delete_character_sheet()  # 最後に実行
        
        print("\n" + "=" * 50)
        print("🎉 全テストが正常に完了しました！")
        print("✅ キャラクターシートAPI実装成功")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = run_tests()
    if success:
        print("\n🔊 API実装完了通知")
        # 完了音
        os.system('echo -e "\\a\\a\\a"')
    sys.exit(0 if success else 1)