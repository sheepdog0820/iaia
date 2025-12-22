"""
技能ポイント管理システムのテストスイート
クトゥルフ神話TRPG 6版の技能ポイント管理機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CharacterSheet
from .character_models import CharacterSheet6th, CharacterSkill

User = get_user_model()


class SkillPointCalculationTestCase(TestCase):
    """技能ポイント計算のテストケース"""
    
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
            int_value=14,  # INT×10 = 140 趣味技能ポイント
            edu_value=16   # EDU×20 = 320 職業技能ポイント（標準）
        )
        self.character_6th = CharacterSheet6th.objects.create(
            character_sheet=self.character
        )
    
    def test_occupation_skill_points_calculation(self):
        """職業技能ポイントの計算テスト"""
        # 標準: EDU×20
        self.assertEqual(self.character.calculate_occupation_points(), 320)
        
        # 職業による倍率変更
        self.character.occupation_multiplier = 25  # EDU×25
        self.assertEqual(self.character.calculate_occupation_points(), 400)
    
    def test_hobby_skill_points_calculation(self):
        """趣味技能ポイントの計算テスト"""
        # INT×10
        self.assertEqual(self.character.calculate_hobby_points(), 140)
    
    def test_used_skill_points_calculation(self):
        """使用済み技能ポイントの計算テスト"""
        # 技能を追加
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25,
            occupation_points=40,
            interest_points=10,
            bonus_points=0
        )
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25,
            occupation_points=30,
            interest_points=15,
            bonus_points=0
        )
        
        # 使用済みポイントの確認
        self.assertEqual(self.character.calculate_used_occupation_points(), 70)  # 40 + 30
        self.assertEqual(self.character.calculate_used_hobby_points(), 25)  # 10 + 15
    
    def test_remaining_skill_points_calculation(self):
        """残り技能ポイントの計算テスト"""
        # 技能を追加
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25,
            occupation_points=40,
            interest_points=15
        )
        
        # 残りポイントの確認
        self.assertEqual(self.character.calculate_remaining_occupation_points(), 280)  # 320 - 40
        self.assertEqual(self.character.calculate_remaining_hobby_points(), 125)  # 140 - 15


class SkillPointValidationTestCase(TestCase):
    """技能ポイント割り振りのバリデーションテスト"""
    
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
            int_value=10,  # INT×10 = 100 趣味技能ポイント
            edu_value=10   # EDU×20 = 200 職業技能ポイント
        )
    
    def test_skill_point_over_allocation_validation(self):
        """技能ポイント過剰割り振りのバリデーション"""
        skill = CharacterSkill(
            character_sheet=self.character,
            skill_name='図書館',
            occupation_points=250  # 200を超える
        )
        
        with self.assertRaises(ValidationError) as cm:
            skill.clean()
        
        self.assertIn('occupation_points', str(cm.exception))
    
    def test_skill_value_cap_validation(self):
        """技能値上限（999）のバリデーション"""
        high_cap_character = CharacterSheet.objects.create(
            user=self.user,
            name='High Cap Investigator',
            edition='6th',
            age=25,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=999,
            edu_value=999
        )

        skill = CharacterSkill(
            character_sheet=high_cap_character,
            skill_name='図書館',
            base_value=25,
            occupation_points=500,
            interest_points=500,  # 合計1025となる（上限999を超える）
            bonus_points=0
        )
        
        with self.assertRaises(ValidationError) as cm:
            skill.clean()
        
        self.assertIn('技能値の合計は999を超えることはできません。', str(cm.exception))
    
    def test_negative_skill_points_validation(self):
        """負の技能ポイントのバリデーション"""
        skill = CharacterSkill(
            character_sheet=self.character,
            skill_name='図書館',
            occupation_points=-10
        )
        
        with self.assertRaises(ValidationError) as cm:
            skill.clean()
        
        self.assertIn('occupation_points', str(cm.exception))


class SkillPointManagementAPITestCase(APITestCase):
    """技能ポイント管理APIのテストケース"""
    
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
            int_value=50,  # INT×10 = 500 趣味技能ポイント
            edu_value=60   # EDU×20 = 1200 職業技能ポイント
        )
    
    def test_get_skill_points_summary(self):
        """技能ポイントサマリー取得APIテスト"""
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/skill-points-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_occupation_points'], 1200)
        self.assertEqual(response.data['total_hobby_points'], 500)
        self.assertEqual(response.data['used_occupation_points'], 0)
        self.assertEqual(response.data['used_hobby_points'], 0)
        self.assertEqual(response.data['remaining_occupation_points'], 1200)
        self.assertEqual(response.data['remaining_hobby_points'], 500)
    
    def test_allocate_skill_points(self):
        """技能ポイント割り振りAPIテスト"""
        # 既存技能にポイントを割り振る
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25
        )
        
        allocation_data = {
            'skill_id': skill.id,
            'occupation_points': 40,
            'interest_points': 15
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/allocate-skill-points/',
            allocation_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 技能ポイントが更新されたか確認
        skill.refresh_from_db()
        self.assertEqual(skill.occupation_points, 40)
        self.assertEqual(skill.interest_points, 15)
        self.assertEqual(skill.current_value, 80)  # 25 + 40 + 15 = 80
    
    def test_batch_skill_points_allocation(self):
        """一括技能ポイント割り振りAPIテスト"""
        # 複数の技能を作成
        skill1 = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25
        )
        skill2 = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25
        )
        
        allocation_data = {
            'allocations': [
                {
                    'skill_id': skill1.id,
                    'occupation_points': 40,
                    'interest_points': 10
                },
                {
                    'skill_id': skill2.id,
                    'occupation_points': 30,
                    'interest_points': 15
                }
            ]
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/batch-allocate-skill-points/',
            allocation_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        
        # 残りポイントの確認
        self.assertEqual(response.data['remaining_occupation_points'], 1130)  # 1200 - 70
        self.assertEqual(response.data['remaining_hobby_points'], 475)  # 500 - 25
    
    def test_skill_points_validation_on_allocation(self):
        """技能ポイント割り振り時のバリデーションテスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25
        )
        
        # ポイントを超過して割り振ろうとする
        allocation_data = {
            'skill_id': skill.id,
            'occupation_points': 1250  # 総ポイント1200を超える
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/allocate-skill-points/',
            allocation_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('職業技能ポイントが不足しています', response.data['error'])
    
    def test_reset_skill_points(self):
        """技能ポイントリセットAPIテスト"""
        # 技能にポイントを割り振る
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='図書館',
            base_value=25,
            occupation_points=40,
            interest_points=15
        )
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/reset-skill-points/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # ポイントがリセットされたか確認
        skill.refresh_from_db()
        self.assertEqual(skill.occupation_points, 0)
        self.assertEqual(skill.interest_points, 0)
        self.assertEqual(skill.current_value, 25)  # 基本値のみ残る


class OccupationSkillSetTestCase(TestCase):
    """職業別技能セットのテストケース"""
    
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
            edu_value=60,  # EDU×20 = 1200
            occupation='医師'
        )
    
    def test_occupation_skill_set_template(self):
        """職業別推奨技能セットのテスト"""
        # 医師の推奨技能セット
        doctor_skills = self.character.get_occupation_recommended_skills()
        
        expected_skills = [
            '医学', '応急手当', '生物学', '薬学',
            '心理学', '精神分析', '信用', '言いくるめ'
        ]
        
        for skill in expected_skills:
            self.assertIn(skill, doctor_skills)
    
    def test_apply_occupation_template(self):
        """職業テンプレート適用のテスト"""
        # 職業テンプレートを適用
        self.character.apply_occupation_template()
        
        # 推奨技能が作成されているか確認
        skills = CharacterSkill.objects.filter(character_sheet=self.character)
        skill_names = [skill.skill_name for skill in skills]
        
        self.assertIn('医学', skill_names)
        self.assertIn('応急手当', skill_names)
        
        # EDU×25などの特殊な職業倍率も確認
        if self.character.occupation == '教授':
            self.assertEqual(self.character.occupation_multiplier, 25)
