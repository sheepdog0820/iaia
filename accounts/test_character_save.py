from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.character_models import CharacterSheet, CharacterSheet6th, CharacterSkill
import json

User = get_user_model()


class CharacterSheetSaveTestCase(APITestCase):
    """キャラクターシート保存機能のテストケース - TDD"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)

    def test_save_6th_edition_character_success(self):
        """正常系: 6版キャラクターの保存成功"""
        character_data = {
            'edition': '6th',
            'name': 'テスト探索者',
            'player_name': 'テストプレイヤー',
            'age': 25,
            'gender': '男性',
            'occupation': '探偵',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 12,
            'con_value': 14,
            'pow_value': 11,
            'dex_value': 13,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 14,
            'notes': 'テストキャラクター',
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['name'], 'テスト探索者')
        self.assertEqual(response.data['edition'], '6th')
        
        # DBに保存されているか確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertEqual(character.name, 'テスト探索者')
        self.assertEqual(character.user, self.user)

    def test_save_character_with_skills(self):
        """正常系: 技能を含むキャラクターの保存"""
        character_data = {
            'edition': '6th',
            'name': 'スキル持ち探索者',
            'age': 30,
            'str_value': 12,
            'con_value': 14,
            'pow_value': 11,
            'dex_value': 13,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 14,
            'skills': [
                {
                    'skill_name': '目星',
                    'category': '探索系',
                    'base_value': 25,
                    'occupation_points': 30,
                    'interest_points': 10,
                    'bonus_points': 0,
                    'other_points': 0,
                },
                {
                    'skill_name': '図書館',
                    'category': '探索系',
                    'base_value': 25,
                    'occupation_points': 20,
                    'interest_points': 0,
                    'bonus_points': 0,
                    'other_points': 0,
                }
            ]
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 技能が保存されているか確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        skills = character.skills.all()
        self.assertEqual(skills.count(), 2)
        
        meboshi = skills.get(skill_name='目星')
        self.assertEqual(meboshi.current_value, 65)  # 25 + 30 + 10 + 0 + 0

    def test_save_character_authentication_required(self):
        """認証: 未認証でのアクセス拒否"""
        self.client.logout()
        
        character_data = {
            'edition': '6th',
            'name': '認証なし探索者',
            'age': 25,
            'str_value': 12,
            'con_value': 14,
            'pow_value': 11,
            'dex_value': 13,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 14,
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        # DRFはデフォルトで403を返すこともある
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_save_character_validation_errors(self):
        """バリデーション: 不正データでのエラー"""
        # 必須フィールド不足
        character_data = {
            'edition': '6th',
            'name': '',  # 名前が空
            'age': 150,  # 年齢が範囲外
            'str_value': 5,  # 能力値が範囲外（6版は3-18）
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_existing_character(self):
        """正常系: 既存キャラクターの更新"""
        # まず作成
        character = CharacterSheet.objects.create(
            user=self.user,
            edition='6th',
            name='更新前探索者',
            age=25,
            str_value=12,
            con_value=14,
            pow_value=11,
            dex_value=13,
            app_value=10,
            siz_value=15,
            int_value=16,
            edu_value=14,
        )
        
        # 更新
        update_data = {
            'name': '更新後探索者',
            'age': 26,
            'str_value': 15,
        }
        
        response = self.client.patch(f'/api/accounts/character-sheets/{character.id}/', update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '更新後探索者')
        self.assertEqual(response.data['age'], 26)
        self.assertEqual(response.data['str_value'], 15)

    def test_delete_character(self):
        """正常系: キャラクターの削除"""
        character = CharacterSheet.objects.create(
            user=self.user,
            edition='6th',
            name='削除予定探索者',
            age=25,
            str_value=12,
            con_value=14,
            pow_value=11,
            dex_value=13,
            app_value=10,
            siz_value=15,
            int_value=16,
            edu_value=14,
        )
        
        response = self.client.delete(f'/api/accounts/character-sheets/{character.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CharacterSheet.objects.filter(id=character.id).exists())

    def test_list_user_characters(self):
        """正常系: ユーザーのキャラクター一覧取得"""
        # 複数のキャラクターを作成
        for i in range(3):
            CharacterSheet.objects.create(
                user=self.user,
                edition='6th',
                name=f'探索者{i}',
                age=25 + i,
                str_value=12,
                con_value=14,
                pow_value=11,
                dex_value=13,
                app_value=10,
                siz_value=15,
                int_value=16,
                edu_value=14,
            )
        
        # 他のユーザーのキャラクター（見えないはず）
        other_user = User.objects.create_user('other', 'pass')
        CharacterSheet.objects.create(
            user=other_user,
            edition='6th',
            name='他人の探索者',
            age=30,
            str_value=12,
            con_value=14,
            pow_value=11,
            dex_value=13,
            app_value=10,
            siz_value=15,
            int_value=16,
            edu_value=14,
        )
        
        response = self.client.get('/api/accounts/character-sheets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRFのページネーションがない場合はリストがそのまま返る
        if isinstance(response.data, list):
            self.assertEqual(len(response.data), 3)  # 自分のキャラクターのみ
        else:
            # ページネーションがある場合
            self.assertEqual(len(response.data['results']), 3)  # 自分のキャラクターのみ

    def test_save_character_auto_calculate_derived_stats(self):
        """正常系: 派生ステータスの自動計算"""
        character_data = {
            'edition': '6th',
            'name': '自動計算テスト',
            'age': 25,
            'str_value': 12,
            'con_value': 14,
            'pow_value': 11,
            'dex_value': 13,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 14,
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 派生ステータスが自動計算されているか確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        # 6版の値は内部的に×5で保存されている
        self.assertEqual(character.hit_points_max, 14)  # (14*5 + 15*5) / 10 = 14.5 -> 14
        self.assertEqual(character.magic_points_max, 11)  # 11*5 / 5 = 11
        self.assertEqual(character.sanity_starting, 55)  # POW*5と同じ
        self.assertEqual(character.sanity_max, 55)  # POW*5と同じ（99以下）

    def test_save_6th_edition_specific_data(self):
        """正常系: 6版固有データの保存"""
        character_data = {
            'edition': '6th',
            'name': '6版固有データテスト',
            'age': 25,
            'str_value': 12,
            'con_value': 14,
            'pow_value': 11,
            'dex_value': 13,
            'app_value': 10,
            'siz_value': 15,
            'int_value': 16,
            'edu_value': 14,
            'sixth_edition_data': {
                'mental_disorder': '恐怖症（高所）'
            }
        }
        
        response = self.client.post('/api/accounts/character-sheets/', character_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 6版固有データが保存されているか確認
        character = CharacterSheet.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(character, 'sixth_edition_data'))
        self.assertEqual(character.sixth_edition_data.mental_disorder, '恐怖症（高所）')
        
        # 6版の自動計算値が正しいか確認（内部的には能力値は×5で保存されている）
        # idea_roll = INT(16*5=80) * 5 = 400
        self.assertEqual(character.sixth_edition_data.idea_roll, 400)  # INT * 5 （内部値）
        self.assertEqual(character.sixth_edition_data.luck_roll, 275)  # POW * 5 （内部値）
        self.assertEqual(character.sixth_edition_data.know_roll, 350)  # EDU * 5 （内部値）

    def test_character_permission_check(self):
        """認可: 他人のキャラクターへのアクセス拒否"""
        # 他のユーザーのキャラクター
        other_user = User.objects.create_user('other', 'pass')
        character = CharacterSheet.objects.create(
            user=other_user,
            edition='6th',
            name='他人の探索者',
            age=30,
            str_value=12,
            con_value=14,
            pow_value=11,
            dex_value=13,
            app_value=10,
            siz_value=15,
            int_value=16,
            edu_value=14,
        )
        
        # 更新しようとする
        update_data = {'name': '勝手に変更'}
        response = self.client.patch(f'/api/accounts/character-sheets/{character.id}/', update_data, format='json')
        
        # 403 Forbiddenが返ることを確認
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        
        # 削除しようとする
        response = self.client.delete(f'/api/accounts/character-sheets/{character.id}/')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])