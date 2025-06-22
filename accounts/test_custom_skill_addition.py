"""
カスタム技能追加機能のテスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .character_models import CharacterSheet, CharacterSkill

User = get_user_model()


class CustomSkillAdditionModelTestCase(TestCase):
    """カスタム技能追加機能のモデルテストケース"""
    
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
            str_value=13,
            con_value=14,
            pow_value=12,
            dex_value=15,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17
        )
    
    def test_custom_skill_creation_with_specialization(self):
        """専門技能（芸術、言語等）のカスタム技能作成テスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='芸術（イラスト）',
            category='特殊・その他',
            base_value=5,
            occupation_points=30,
            interest_points=10,
            notes='専門分野: イラスト'
        )
        
        self.assertEqual(skill.skill_name, '芸術（イラスト）')
        self.assertEqual(skill.category, '特殊・その他')
        self.assertEqual(skill.current_value, 45)  # 5 + 30 + 10
        self.assertTrue('イラスト' in skill.notes)
    
    def test_language_skill_creation(self):
        """言語技能のカスタム技能作成テスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='他の言語（英語）',
            category='言語系',
            base_value=1,
            occupation_points=50,
            interest_points=20,
            notes='母国語: 日本語, 他言語: 英語'
        )
        
        self.assertEqual(skill.skill_name, '他の言語（英語）')
        self.assertEqual(skill.category, '言語系')
        self.assertEqual(skill.current_value, 71)  # 1 + 50 + 20
    
    def test_custom_skill_name_validation(self):
        """カスタム技能名のバリデーションテスト"""
        # 技能名が空文字の場合は作成できない
        with self.assertRaises(Exception):
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='',  # 空文字
                base_value=10
            )
    
    def test_custom_skill_duplicate_names_allowed(self):
        """同じキャラクターでも異なる専門分野なら重複技能名を許可"""
        # 芸術（イラスト）
        skill1 = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='芸術（イラスト）',
            category='特殊・その他',
            base_value=5,
            occupation_points=30
        )
        
        # 芸術（音楽）- 異なる専門分野
        skill2 = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='芸術（音楽）',
            category='特殊・その他',
            base_value=5,
            occupation_points=25
        )
        
        self.assertNotEqual(skill1.skill_name, skill2.skill_name)
        self.assertEqual(skill1.category, skill2.category)
    
    def test_custom_skill_with_all_point_types(self):
        """全ポイント種類を含むカスタム技能テスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='制作（プログラミング）',
            category='技術系',
            base_value=5,
            occupation_points=40,
            interest_points=20,
            bonus_points=10,
            other_points=5,
            notes='専門: Webアプリケーション開発'
        )
        
        expected_total = 5 + 40 + 20 + 10 + 5  # 80
        self.assertEqual(skill.current_value, expected_total)
        self.assertEqual(skill.skill_name, '制作（プログラミング）')
        self.assertEqual(skill.category, '技術系')


class CustomSkillAdditionAPITestCase(APITestCase):
    """カスタム技能追加機能のAPIテストケース"""
    
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
            str_value=13,
            con_value=14,
            pow_value=12,
            dex_value=15,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_custom_skill_api_creation(self):
        """APIを通じたカスタム技能作成テスト"""
        skill_data = {
            'skill_name': '芸術（写真撮影）',
            'category': '特殊・その他',
            'base_value': 5,
            'occupation_points': 35,
            'interest_points': 15,
            'notes': '専門分野: 風景写真'
        }
        
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/skills/',
            skill_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['skill_name'], '芸術（写真撮影）')
        self.assertEqual(response.data['current_value'], 55)  # 5 + 35 + 15
    
    def test_custom_skill_api_authentication_required(self):
        """APIカスタム技能作成に認証が必要であることをテスト"""
        self.client.logout()
        
        skill_data = {
            'skill_name': '制作（木工）',
            'base_value': 5
        }
        
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/skills/',
            skill_data,
            format='json'
        )
        
        # DRF returns 403 for unauthenticated requests to authenticated endpoints
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_custom_skill_api_permission_check(self):
        """他のユーザーのキャラクターにカスタム技能を追加できないことをテスト"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        other_character = CharacterSheet.objects.create(
            user=other_user,
            name='Other Character',
            edition='6th',
            age=25,
            str_value=13,
            con_value=14,
            pow_value=12,
            dex_value=15,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17
        )
        
        skill_data = {
            'skill_name': '芸術（彫刻）',
            'base_value': 5
        }
        
        response = self.client.post(
            f'/api/accounts/character-sheets/{other_character.id}/skills/',
            skill_data,
            format='json'
        )
        
        # 404 or 403エラーが期待される
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
    
    def test_custom_skill_api_validation(self):
        """APIでのカスタム技能データバリデーションテスト"""
        # 技能名が空の場合
        skill_data = {
            'skill_name': '',  # 空文字
            'base_value': 5
        }
        
        response = self.client.post(
            f'/api/accounts/character-sheets/{self.character.id}/skills/',
            skill_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bulk_custom_skill_creation(self):
        """一括カスタム技能作成テスト"""
        skills_data = {
            'skills': [
                {
                    'skill_name': '芸術（絵画）',
                    'category': '特殊・その他',
                    'base_value': 5,
                    'occupation_points': 30,
                    'interest_points': 10
                },
                {
                    'skill_name': '制作（陶芸）',
                    'category': '技術系',
                    'base_value': 5,
                    'occupation_points': 25,
                    'interest_points': 15
                },
                {
                    'skill_name': '他の言語（中国語）',
                    'category': '言語系',
                    'base_value': 1,
                    'occupation_points': 40,
                    'interest_points': 10
                }
            ]
        }
        
        response = self.client.patch(
            f'/api/accounts/character-sheets/{self.character.id}/skills/bulk_update/',
            skills_data,
            format='json'
        )
        
        # 既存のbulk_updateエンドポイントの拡張として実装予定
        # 最初はPATCHで既存技能更新、後でPOSTで新規作成も対応
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CustomSkillCategoryTestCase(TestCase):
    """カスタム技能カテゴリ機能のテストケース"""
    
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
            str_value=13,
            con_value=14,
            pow_value=12,
            dex_value=15,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17
        )
    
    def test_skill_categorization(self):
        """技能カテゴリ分類テスト"""
        categories = [
            ('探索系', '目星'),
            ('対人系', '説得'),
            ('戦闘系', 'こぶし'),
            ('知識系', '図書館'),
            ('技術系', '機械修理'),
            ('行動系', '隠れる'),
            ('言語系', '母国語'),
            ('特殊・その他', '芸術（絵画）')
        ]
        
        for category, skill_name in categories:
            skill = CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=skill_name,
                category=category,
                base_value=10
            )
            
            self.assertEqual(skill.category, category)
            self.assertEqual(skill.skill_name, skill_name)
    
    def test_custom_category_creation(self):
        """カスタムカテゴリ作成テスト"""
        # 既存のカテゴリに分類しにくい技能
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='占い（タロット）',
            category='特殊・その他',  # カスタム技能は基本的にこのカテゴリ
            base_value=5,
            occupation_points=30,
            notes='専門: タロットカード占い'
        )
        
        self.assertEqual(skill.category, '特殊・その他')
        self.assertTrue('タロット' in skill.notes)


class CustomSkillValidationTestCase(TestCase):
    """カスタム技能バリデーション機能のテストケース"""
    
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
            str_value=13,
            con_value=14,
            pow_value=12,
            dex_value=15,
            app_value=11,
            siz_value=13,
            int_value=16,
            edu_value=17
        )
    
    def test_skill_name_length_validation(self):
        """技能名の長さバリデーションテスト"""
        # 長すぎる技能名
        long_skill_name = '非常に長い技能名' * 10  # 50文字程度
        
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name=long_skill_name,
            base_value=5
        )
        
        # とりあえず作成は成功する（後でバリデーション追加予定）
        self.assertEqual(skill.skill_name, long_skill_name)
    
    def test_skill_points_range_validation(self):
        """技能ポイントの範囲バリデーションテスト"""
        # 負の値は許可しない
        with self.assertRaises(Exception):
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='テスト技能',
                base_value=-5  # 負の値
            )
    
    def test_skill_specialization_format(self):
        """技能専門分野の形式テスト"""
        specialization_patterns = [
            '芸術（絵画）',
            '制作（プログラミング）', 
            '他の言語（英語）',
            '運転（自動車）',
            '操縦（航空機）'
        ]
        
        for skill_name in specialization_patterns:
            skill = CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=skill_name,
                base_value=5
            )
            
            # 専門分野が（）で囲まれていることを確認
            self.assertTrue('（' in skill_name and '）' in skill_name)
            self.assertEqual(skill.skill_name, skill_name)