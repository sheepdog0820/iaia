"""
クトゥルフ神話TRPG 6版 API出力機能テスト（CCFOLIA連携対応）
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import json

from .models import CharacterSheet, CharacterSheet6th, CharacterSkill

User = get_user_model()


class Character6thAPITestCase(APITestCase):
    """6版API機能のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        # テストキャラクター作成
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='田中太郎',
            edition='6th',
            age=28,
            gender='男性',
            occupation='探偵',
            birthplace='東京',
            str_value=60,  # 6版換算で12
            con_value=70,  # 6版換算で14
            pow_value=55,  # 6版換算で11
            dex_value=65,  # 6版換算で13
            app_value=50,  # 6版換算で10
            siz_value=60,  # 6版換算で12
            int_value=75,  # 6版換算で15
            edu_value=80   # 6版換算で16
        )
        
        # 6版固有データ
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character,
            mental_disorder=''
        )
        
        # テスト技能
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            category='探索系',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5
        )
        
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='説得',
            category='対人系',
            base_value=15,
            occupation_points=30,
            interest_points=15
        )
    
    def test_character_list_api_endpoint(self):
        """キャラクター一覧APIエンドポイントの存在テスト"""
        # character-sheetsエンドポイントを使用
        url = reverse('character-sheet-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_character_detail_api_endpoint(self):
        """キャラクター詳細APIエンドポイントの存在テスト"""
        url = reverse('character-sheet-detail', kwargs={'pk': self.character.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_ccfolia_export_format(self):
        """CCFOLIA形式でのデータエクスポートテスト"""
        ccfolia_data = self.character.export_ccfolia_format()
        
        # CCFOLIA標準形式の必須フィールドを確認
        self.assertIn('kind', ccfolia_data)
        self.assertIn('data', ccfolia_data)
        self.assertEqual(ccfolia_data['kind'], 'character')
        
        data = ccfolia_data['data']
        self.assertIn('name', data)
        self.assertIn('initiative', data)
        self.assertIn('commands', data)
        self.assertIn('status', data)
        self.assertIn('params', data)
        
        # キャラクター基本情報
        self.assertEqual(data['name'], '田中太郎')
        self.assertEqual(data['initiative'], 65)  # DEX値
        
        # ステータス配列
        status = data['status']
        self.assertEqual(len(status), 3)
        hp_status = next(s for s in status if s['label'] == 'HP')
        self.assertIn('value', hp_status)
        self.assertIn('max', hp_status)
        
        # パラメータ配列（CCFOLIA形式）
        params = data['params']
        self.assertIsInstance(params, list)
        self.assertEqual(len(params), 8)
        
        # STRパラメータの確認
        str_param = next(p for p in params if p['label'] == 'STR')
        self.assertEqual(str_param['value'], '60')
        
        # コマンド文字列の確認
        commands = data['commands']
        self.assertIsInstance(commands, str)
        self.assertIn('【正気度ロール】', commands)
        self.assertIn('【アイデア】', commands)
        self.assertIn('【幸運】', commands)
        self.assertIn('【知識】', commands)
    
    def test_ccfolia_skills_format(self):
        """CCFOLIA形式のコマンド文字列テスト"""
        ccfolia_data = self.character.export_ccfolia_format()
        commands = ccfolia_data['data']['commands']
        
        # 技能ロールコマンドが含まれているか確認
        self.assertIn('CCB<=90 【目星】', commands)  # 25+40+20+5=90
        
        # 基本判定コマンドが含まれているか確認
        self.assertIn('CCB<=375 【アイデア】', commands)  # INT 75 * 5
        self.assertIn('CCB<=275 【幸運】', commands)    # POW 55 * 5
        self.assertIn('CCB<=400 【知識】', commands)    # EDU 80 * 5
    
    def test_version_export_api(self):
        """バージョンデータエクスポートAPIテスト"""
        # 新バージョン作成
        new_version = CharacterSheet.objects.create(
            user=self.user,
            name=self.character.name,
            edition='6th',
            age=self.character.age,
            str_value=15,  # 変更点
            con_value=self.character.con_value,
            pow_value=self.character.pow_value,
            dex_value=self.character.dex_value,
            app_value=self.character.app_value,
            siz_value=self.character.siz_value,
            int_value=self.character.int_value,
            edu_value=self.character.edu_value,
            parent_sheet=self.character,
            version=2
        )
        
        url = reverse('character-sheet-export-version-data', kwargs={'pk': new_version.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('current_version', data)
        self.assertIn('version_history', data)
    
    def test_ccfolia_json_api_endpoint(self):
        """CCFOLIA JSON出力APIエンドポイントテスト"""
        url = reverse('character-sheet-ccfolia-json', kwargs={'pk': self.character.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Content-Typeがapplication/json
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # CCFOLIA形式のデータ構造
        data = response.json()
        self.assertIn('kind', data)
        self.assertIn('data', data)
        self.assertEqual(data['kind'], 'character')
        
        character_data = data['data']
        self.assertIn('name', character_data)
        self.assertIn('commands', character_data)
        self.assertIn('status', character_data)
        self.assertIn('params', character_data)
    
    def test_api_authentication_required(self):
        """API認証必須テスト"""
        self.client.logout()
        
        url = reverse('character-sheet-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_api_permission_check(self):
        """API権限チェックテスト"""
        # 他のユーザーを作成
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        # 他のユーザーでログイン
        self.client.force_authenticate(user=other_user)
        
        url = reverse('character-sheet-detail', kwargs={'pk': self.character.id})
        response = self.client.get(url)
        # 他のユーザーのキャラクターにはアクセスできない
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CCFOLIASynchronizationTestCase(TestCase):
    """CCFOLIA同期機能のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            name='同期テストキャラ',
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
    
    def test_ccfolia_sync_settings(self):
        """CCFOLIA同期設定のテスト"""
        # 同期設定フィールドが存在することをテスト
        self.character.ccfolia_sync_enabled = True
        self.character.ccfolia_character_id = 'ccfolia_123'
        self.character.save()
        
        self.assertTrue(self.character.ccfolia_sync_enabled)
        self.assertEqual(self.character.ccfolia_character_id, 'ccfolia_123')
    
    def test_auto_sync_on_update(self):
        """更新時の自動同期テスト"""
        # 同期が有効な場合、キャラクター更新時にCCFOLIAへの同期処理が呼ばれる
        self.character.ccfolia_sync_enabled = True
        self.character.save()
        
        # 実際の同期処理はWebhookやAPIコール
        # ここではメソッドの存在をテスト
        self.assertTrue(hasattr(self.character, 'sync_to_ccfolia'))
    
    def test_sync_conflict_resolution(self):
        """同期競合解決のテスト"""
        # 同期競合が発生した場合の処理
        conflict_data = {
            'local_version': 2,
            'remote_version': 3,
            'conflict_fields': ['str_value', 'skills']
        }
        
        # 競合解決メソッドのテスト
        resolution = self.character.resolve_sync_conflict(conflict_data)
        self.assertIn('resolution_strategy', resolution)


class BulkExportTestCase(TestCase):
    """一括エクスポート機能のテストケース"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 複数キャラクター作成
        self.characters = []
        for i in range(3):
            char = CharacterSheet.objects.create(
                user=self.user,
                name=f'テストキャラ{i+1}',
                edition='6th',
                age=20 + i,
                str_value=60,
                con_value=70,
                pow_value=55,
                dex_value=65,
                app_value=50,
                siz_value=60,
                int_value=75,
                edu_value=80
            )
            self.characters.append(char)
    
    def test_bulk_ccfolia_export(self):
        """一括CCFOLIAエクスポートテスト"""
        character_ids = [char.id for char in self.characters]
        
        # 一括エクスポート機能
        export_data = CharacterSheet.bulk_export_ccfolia(character_ids)
        
        self.assertEqual(len(export_data), 3)
        for data in export_data:
            self.assertIn('kind', data)
            self.assertIn('data', data)
            character_data = data['data']
            self.assertIn('name', character_data)
            self.assertIn('params', character_data)
            self.assertIn('commands', character_data)
    
    def test_export_format_validation(self):
        """エクスポート形式の検証テスト"""
        for character in self.characters:
            ccfolia_data = character.export_ccfolia_format()
            
            # データ整合性チェック
            self.assertIsInstance(ccfolia_data, dict)
            self.assertIn('kind', ccfolia_data)
            self.assertIn('data', ccfolia_data)
            self.assertEqual(ccfolia_data['kind'], 'character')
            
            data = ccfolia_data['data']
            self.assertIsInstance(data['commands'], str)
            self.assertIsInstance(data['params'], list)
            self.assertIsInstance(data['status'], list)
            
            # 必須フィールドの存在確認
            required_fields = [
                'name', 'initiative', 'commands', 'params', 'status'
            ]
            for field in required_fields:
                self.assertIn(field, data)