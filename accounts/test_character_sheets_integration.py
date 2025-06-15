"""
キャラクターシート機能の統合テスト

このテストでは以下の機能を検証します：
- キャラクターシートのCRUD操作
- バージョン管理機能
- 権限制御（参照は全ユーザ、編集は作成者のみ）
- Web ビューの動作
- API エンドポイントの動作
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import (
    CharacterSheet, CharacterSheet6th, CharacterSheet7th,
    CharacterSkill, CharacterEquipment
)
import json

User = get_user_model()


class CharacterSheetModelTestCase(TestCase):
    """キャラクターシートモデルのテスト"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='testpass123',
            nickname='テストユーザー1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123',
            nickname='テストユーザー2'
        )
    
    def test_character_sheet_creation_6th(self):
        """6版キャラクターシート作成テスト"""
        character = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='テスト探索者6版',
            player_name='テストプレイヤー',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        self.assertEqual(character.edition, '6th')
        self.assertEqual(character.name, 'テスト探索者6版')
        self.assertEqual(character.version, 1)
        self.assertIsNone(character.parent_sheet)
        self.assertTrue(character.is_active)
        
        # 自動計算値の確認
        expected_hp = (character.con_value + character.siz_value) // 10
        expected_mp = character.pow_value // 5
        self.assertEqual(character.hit_points_max, expected_hp)
        self.assertEqual(character.magic_points_max, expected_mp)
    
    def test_character_sheet_creation_7th(self):
        """7版キャラクターシート作成テスト"""
        character = CharacterSheet.objects.create(
            user=self.user1,
            edition='7th',
            name='テスト探索者7版',
            player_name='テストプレイヤー',
            age=30,
            str_value=60,
            con_value=65,
            pow_value=70,
            dex_value=75,
            app_value=80,
            siz_value=55,
            int_value=85,
            edu_value=90
        )
        
        self.assertEqual(character.edition, '7th')
        self.assertEqual(character.name, 'テスト探索者7版')
        self.assertEqual(character.version, 1)
    
    def test_version_creation(self):
        """バージョン作成テスト"""
        # 元のキャラクターシートを作成
        original = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='オリジナル探索者',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        # バージョン2を作成
        version2 = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='オリジナル探索者',
            age=26,  # 年齢を変更
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80,
            parent_sheet=original,
            version=2
        )
        
        self.assertEqual(version2.version, 2)
        self.assertEqual(version2.parent_sheet, original)
        self.assertEqual(version2.age, 26)
        
        # オリジナルのバージョンリストに含まれることを確認
        versions = original.versions.all()
        self.assertIn(version2, versions)
    
    def test_character_skills(self):
        """キャラクター技能テスト"""
        character = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='技能テスト探索者',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        # 技能を追加
        skill = CharacterSkill.objects.create(
            character_sheet=character,
            skill_name='図書館',
            base_value=25,
            occupation_points=40,
            interest_points=10,
            other_points=0,
            current_value=75
        )
        
        self.assertEqual(skill.character_sheet, character)
        self.assertEqual(skill.current_value, 75)
        self.assertEqual(character.skills.count(), 1)
    
    def test_character_equipment(self):
        """キャラクター装備テスト"""
        character = CharacterSheet.objects.create(
            user=self.user1,
            edition='7th',
            name='装備テスト探索者',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        # 武器を追加
        weapon = CharacterEquipment.objects.create(
            character_sheet=character,
            item_type='weapon',
            name='ピストル',
            damage='1d10',
            base_range='15m',
            ammo=6,
            description='小型拳銃'
        )
        
        self.assertEqual(weapon.character_sheet, character)
        self.assertEqual(weapon.item_type, 'weapon')
        self.assertEqual(character.equipment.count(), 1)


class CharacterSheetAPITestCase(APITestCase):
    """キャラクターシートAPI統合テスト"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='apiuser1',
            password='testpass123',
            nickname='APIユーザー1'
        )
        self.user2 = User.objects.create_user(
            username='apiuser2',
            password='testpass123',
            nickname='APIユーザー2'
        )
        
        self.client = APIClient()
        
        # テスト用キャラクターシートを作成
        self.character1 = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='APIテスト探索者1',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        self.character2 = CharacterSheet.objects.create(
            user=self.user2,
            edition='7th',
            name='APIテスト探索者2',
            age=30,
            str_value=60,
            con_value=65,
            pow_value=70,
            dex_value=75,
            app_value=80,
            siz_value=55,
            int_value=85,
            edu_value=90
        )
    
    def test_character_list_api_public_access(self):
        """キャラクター一覧API - 全ユーザアクセステスト"""
        # user1でログイン
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/accounts/character-sheets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertGreaterEqual(len(data), 2)  # user1とuser2のキャラクター両方が見える
        
        # キャラクター名を確認
        character_names = [char['name'] for char in data]
        self.assertIn('APIテスト探索者1', character_names)
        self.assertIn('APIテスト探索者2', character_names)
    
    def test_character_detail_api_public_access(self):
        """キャラクター詳細API - 他ユーザーのキャラクター参照テスト"""
        # user1でuser2のキャラクターを参照
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(f'/api/accounts/character-sheets/{self.character2.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['name'], 'APIテスト探索者2')
        self.assertEqual(data['edition'], '7th')
    
    def test_character_edit_permission_denied(self):
        """キャラクター編集API - 他ユーザーのキャラクター編集拒否テスト"""
        # user1でuser2のキャラクターを編集しようとする
        self.client.force_authenticate(user=self.user1)
        
        update_data = {
            'name': '変更された名前',
            'age': 35
        }
        
        response = self.client.patch(
            f'/api/accounts/character-sheets/{self.character2.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_character_creation_api(self):
        """キャラクター作成APIテスト"""
        self.client.force_authenticate(user=self.user1)
        
        character_data = {
            'edition': '7th',
            'name': '新規作成探索者',
            'player_name': '新規プレイヤー',
            'age': 28,
            'gender': '女性',
            'occupation': '学者',
            'str_value': 55,
            'con_value': 60,
            'pow_value': 80,
            'dex_value': 75,
            'app_value': 70,
            'siz_value': 50,
            'int_value': 90,
            'edu_value': 85,
            'hit_points_current': 11,
            'magic_points_current': 16,
            'sanity_current': 80
        }
        
        response = self.client.post(
            '/api/accounts/character-sheets/',
            data=json.dumps(character_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = response.json()
        self.assertEqual(data['name'], '新規作成探索者')
        self.assertEqual(data['edition'], '7th')
        self.assertEqual(data['age'], 28)
        
        # データベースに保存されているか確認
        created_character = CharacterSheet.objects.get(id=data['id'])
        self.assertEqual(created_character.user, self.user1)
    
    def test_version_creation_api(self):
        """バージョン作成APIテスト"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(f'/api/accounts/character-sheets/{self.character1.id}/create_version/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = response.json()
        self.assertEqual(data['version'], 2)
        self.assertEqual(data['parent_sheet'], self.character1.id)
        self.assertEqual(data['name'], self.character1.name)
    
    def test_edition_filter_api(self):
        """版別フィルタリングAPIテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 6版のみ取得
        response = self.client.get('/api/accounts/character-sheets/by_edition/?edition=6th')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        for character in data:
            self.assertEqual(character['edition'], '6th')
    
    def test_unauthenticated_access_denied(self):
        """未認証アクセス拒否テスト"""
        response = self.client.get('/api/accounts/character-sheets/')
        # IsAuthenticatedはログインが必要で、未認証の場合は403を返す場合がある
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class CharacterSheetWebViewTestCase(TestCase):
    """キャラクターシートWebビュー統合テスト"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='webuser1',
            password='testpass123',
            nickname='Webユーザー1'
        )
        self.user2 = User.objects.create_user(
            username='webuser2',
            password='testpass123',
            nickname='Webユーザー2'
        )
        
        self.client = Client()
        
        # テスト用キャラクターシートを作成
        self.character1 = CharacterSheet.objects.create(
            user=self.user1,
            edition='6th',
            name='Webテスト探索者1',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        self.character2 = CharacterSheet.objects.create(
            user=self.user2,
            edition='7th',
            name='Webテスト探索者2',
            age=30,
            str_value=60,
            con_value=65,
            pow_value=70,
            dex_value=75,
            app_value=80,
            siz_value=55,
            int_value=85,
            edu_value=90
        )
    
    def test_character_list_view_public_access(self):
        """キャラクター一覧ビュー - 全ユーザのキャラクター表示テスト"""
        self.client.force_login(self.user1)
        
        response = self.client.get('/accounts/character/list/')
        self.assertEqual(response.status_code, 200)
        
        # ページが正常に表示されることを確認（キャラクターはJavaScriptで動的に読み込まれる）
        self.assertContains(response, 'キャラクターシート一覧')
        self.assertContains(response, 'loadCharacters')
    
    def test_character_detail_view_public_access(self):
        """キャラクター詳細ビュー - 他ユーザーのキャラクター参照テスト"""
        self.client.force_login(self.user1)
        
        # user2のキャラクターを参照
        response = self.client.get(f'/accounts/character/{self.character2.id}/')
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'Webテスト探索者2')
        self.assertContains(response, '7版')
    
    def test_character_edit_view_owner_only(self):
        """キャラクター編集ビュー - 作成者のみアクセス可能テスト"""
        # 作成者はアクセス可能
        self.client.force_login(self.user1)
        response = self.client.get(f'/accounts/character/{self.character1.id}/edit/')
        self.assertEqual(response.status_code, 200)
        
        # 他ユーザーはアクセス不可
        self.client.force_login(self.user2)
        response = self.client.get(f'/accounts/character/{self.character1.id}/edit/')
        self.assertEqual(response.status_code, 404)
    
    def test_character_new_view(self):
        """新規キャラクター作成ビューテスト"""
        self.client.force_login(self.user1)
        
        response = self.client.get('/accounts/character/new/')
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, 'キャラクターシート作成')
        self.assertContains(response, 'エディションを選択')
    
    def test_character_creation_forms_access(self):
        """版別キャラクター作成フォームアクセステスト"""
        self.client.force_login(self.user1)
        
        # 6版作成フォーム
        response = self.client.get('/accounts/character/create/6th/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '6版')
        
        # 7版作成フォーム
        response = self.client.get('/accounts/character/create/7th/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '7版')
    
    def test_unauthenticated_web_access_redirect(self):
        """未認証Webアクセスリダイレクトテスト"""
        # ログインページにリダイレクトされる
        response = self.client.get('/accounts/character/list/')
        self.assertEqual(response.status_code, 302)
        
        response = self.client.get(f'/accounts/character/{self.character1.id}/')
        self.assertEqual(response.status_code, 302)


class CharacterSheetIntegrationTestCase(TestCase):
    """キャラクターシート機能統合テスト"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='integrationuser1',
            password='testpass123',
            nickname='統合テストユーザー1'
        )
        self.user2 = User.objects.create_user(
            username='integrationuser2',
            password='testpass123',
            nickname='統合テストユーザー2'
        )
    
    def test_complete_character_lifecycle(self):
        """完全なキャラクターライフサイクルテスト"""
        api_client = APIClient()
        api_client.force_authenticate(user=self.user1)
        
        # 1. キャラクター作成
        character_data = {
            'edition': '6th',
            'name': 'ライフサイクルテスト探索者',
            'player_name': 'テストプレイヤー',
            'age': 25,
            'gender': '男性',
            'occupation': '私立探偵',
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
            'sanity_current': 75
        }
        
        response = api_client.post(
            '/api/accounts/character-sheets/',
            data=json.dumps(character_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.json()['id']
        
        # 2. 技能追加
        skill_data = {
            'skill_name': '図書館',
            'base_value': 25,
            'occupation_points': 50,
            'interest_points': 0,
            'other_points': 0,
            'current_value': 75
        }
        
        response = api_client.post(
            f'/api/accounts/character-sheets/{character_id}/skills/',
            data=json.dumps(skill_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. 装備追加
        equipment_data = {
            'item_type': 'weapon',
            'name': 'ピストル',
            'damage': '1d10',
            'base_range': '15m',
            'ammo': 6
        }
        
        response = api_client.post(
            f'/api/accounts/character-sheets/{character_id}/equipment/',
            data=json.dumps(equipment_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. 他ユーザーから参照可能かテスト
        api_client.force_authenticate(user=self.user2)
        response = api_client.get(f'/api/accounts/character-sheets/{character_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['name'], 'ライフサイクルテスト探索者')
        self.assertEqual(len(data['skills']), 1)
        self.assertEqual(len(data['equipment']), 1)
        
        # 5. 他ユーザーから編集試行（失敗）
        update_data = {'name': '変更しようとした名前'}
        response = api_client.patch(
            f'/api/accounts/character-sheets/{character_id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 6. 作成者がバージョン作成
        api_client.force_authenticate(user=self.user1)
        response = api_client.post(f'/api/accounts/character-sheets/{character_id}/create_version/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        version_data = response.json()
        self.assertEqual(version_data['version'], 2)
        self.assertEqual(version_data['parent_sheet'], character_id)
        
        # 7. バージョン履歴確認
        response = api_client.get(f'/api/accounts/character-sheets/{character_id}/versions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        versions = response.json()
        self.assertEqual(len(versions), 2)  # オリジナル + バージョン2
    
    def test_cross_user_permission_matrix(self):
        """ユーザー間権限マトリックステスト"""
        # user1のキャラクター作成
        character = CharacterSheet.objects.create(
            user=self.user1,
            edition='7th',
            name='権限テスト探索者',
            age=25,
            str_value=65,
            con_value=70,
            pow_value=75,
            dex_value=80,
            app_value=60,
            siz_value=65,
            int_value=85,
            edu_value=80
        )
        
        api_client = APIClient()
        
        # user2の権限テスト
        api_client.force_authenticate(user=self.user2)
        
        # 参照 - 成功
        response = api_client.get(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 更新 - 失敗
        response = api_client.patch(
            f'/api/accounts/character-sheets/{character.id}/',
            data=json.dumps({'name': '変更試行'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 削除 - 失敗
        response = api_client.delete(f'/api/accounts/character-sheets/{character.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # バージョン作成 - 失敗
        response = api_client.post(f'/api/accounts/character-sheets/{character.id}/create_version/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)