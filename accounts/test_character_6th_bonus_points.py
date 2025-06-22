"""
クトゥルフ神話TRPG 6版 ボーナスポイント機能テスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from .character_models import CharacterSheet, CharacterSkill

User = get_user_model()


class BonusPointsTestCase(TestCase):
    """ボーナスポイント機能のテストケース"""
    
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
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80
        )
    
    def test_bonus_points_field_exists(self):
        """ボーナスポイントフィールドが存在することをテスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5  # ボーナスポイント
        )
        
        self.assertEqual(skill.bonus_points, 5)
    
    def test_skill_total_calculation_with_bonus(self):
        """ボーナスポイントを含めた技能値合計の計算テスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5
        )
        
        expected_total = 25 + 40 + 20 + 5
        self.assertEqual(skill.current_value, expected_total)
    
    def test_skill_with_notes_field(self):
        """備考フィールドのテスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5,
            notes='成長ボーナス+5'
        )
        
        self.assertEqual(skill.notes, '成長ボーナス+5')
    
    def test_skill_category_field(self):
        """技能カテゴリフィールドのテスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            category='探索系',
            base_value=25,
            occupation_points=40,
            interest_points=20,
            bonus_points=5
        )
        
        self.assertEqual(skill.category, '探索系')
    
    def test_custom_skill_creation(self):
        """カスタム技能の作成テスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='芸術（イラスト）',
            category='特殊・その他',
            base_value=5,
            occupation_points=30,
            interest_points=10,
            bonus_points=0,
            notes='専門技能'
        )
        
        self.assertEqual(skill.skill_name, '芸術（イラスト）')
        self.assertEqual(skill.category, '特殊・その他')
        self.assertEqual(skill.notes, '専門技能')
    
    def test_skill_point_breakdown(self):
        """技能ポイントの内訳が正しく保持されることをテスト"""
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='説得',
            base_value=15,
            occupation_points=35,
            interest_points=25,
            bonus_points=10
        )
        
        # 各項目が正しく保持されている
        self.assertEqual(skill.base_value, 15)
        self.assertEqual(skill.occupation_points, 35)
        self.assertEqual(skill.interest_points, 25)
        self.assertEqual(skill.bonus_points, 10)
        self.assertEqual(skill.current_value, 85)
    
    def test_skill_category_choices(self):
        """技能カテゴリの選択肢テスト"""
        # 仕様書に定められたカテゴリ
        valid_categories = [
            '探索系',
            '対人系', 
            '戦闘系',
            '知識系',
            '技術系',
            '行動系',
            '言語系',
            '特殊・その他'
        ]
        
        for category in valid_categories:
            skill = CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=f'テスト技能_{category}',
                category=category,
                base_value=10
            )
            self.assertEqual(skill.category, category)


class SkillManagementTestCase(TestCase):
    """技能管理システムのテストケース"""
    
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
            str_value=60,
            con_value=70,
            pow_value=55,
            dex_value=65,
            app_value=50,
            siz_value=60,
            int_value=75,
            edu_value=80
        )
    
    def test_get_skills_by_category(self):
        """カテゴリ別技能取得のテスト"""
        # 複数の技能を作成
        skills_data = [
            ('目星', '探索系'),
            ('聞き耳', '探索系'),
            ('説得', '対人系'),
            ('言いくるめ', '対人系'),
            ('拳銃', '戦闘系'),
        ]
        
        for skill_name, category in skills_data:
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=skill_name,
                category=category,
                base_value=25
            )
        
        # カテゴリ別取得をテスト
        exploration_skills = self.character.skills.filter(category='探索系')
        self.assertEqual(exploration_skills.count(), 2)
        
        social_skills = self.character.skills.filter(category='対人系')
        self.assertEqual(social_skills.count(), 2)
        
        combat_skills = self.character.skills.filter(category='戦闘系')
        self.assertEqual(combat_skills.count(), 1)
    
    def test_skill_point_tracking(self):
        """技能ポイント使用量追跡のテスト"""
        # 複数技能にポイントを振り分け
        skills_data = [
            ('目星', 40, 20),
            ('説得', 30, 15),
            ('拳銃', 25, 10),
        ]
        
        total_occupation_used = 0
        total_interest_used = 0
        
        for skill_name, occ_points, int_points in skills_data:
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name=skill_name,
                occupation_points=occ_points,
                interest_points=int_points
            )
            total_occupation_used += occ_points
            total_interest_used += int_points
        
        # 使用済みポイントの集計
        actual_occ_used = sum(skill.occupation_points for skill in self.character.skills.all())
        actual_int_used = sum(skill.interest_points for skill in self.character.skills.all())
        
        self.assertEqual(actual_occ_used, total_occupation_used)
        self.assertEqual(actual_int_used, total_interest_used)
    
    def test_duplicate_skill_prevention(self):
        """重複技能の防止テスト"""
        # 同じ技能名は同一キャラクターで重複できない
        CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name='目星',
            base_value=25
        )
        
        # 同じ技能名での作成を試行
        with self.assertRaises(Exception):
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='目星',
                base_value=30
            )