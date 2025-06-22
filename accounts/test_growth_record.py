"""
成長記録システムのテストスイート
クトゥルフ神話TRPG 6版の成長記録システム機能をテスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date
from .models import CharacterSheet
from .character_models import CharacterSheet6th, CharacterSkill, GrowthRecord, SkillGrowthRecord

User = get_user_model()


class GrowthRecordModelTestCase(TestCase):
    """成長記録モデルのテストケース"""
    
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
    
    def test_growth_record_creation(self):
        """成長記録の作成テスト"""
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="影の館",
            gm_name="田中GM",
            sanity_gained=0,
            sanity_lost=5,
            experience_gained=3,
            special_rewards="古い日記を発見",
            notes="初回セッション。恐怖体験により正気度を失った"
        )
        
        self.assertEqual(growth_record.character_sheet, self.character)
        self.assertEqual(growth_record.session_date, date(2024, 1, 15))
        self.assertEqual(growth_record.scenario_name, "影の館")
        self.assertEqual(growth_record.gm_name, "田中GM")
        self.assertEqual(growth_record.sanity_gained, 0)
        self.assertEqual(growth_record.sanity_lost, 5)
        self.assertEqual(growth_record.experience_gained, 3)
        self.assertEqual(growth_record.special_rewards, "古い日記を発見")
        self.assertEqual(growth_record.notes, "初回セッション。恐怖体験により正気度を失った")
    
    def test_growth_record_validation(self):
        """成長記録のバリデーションテスト"""
        # 負の値のテスト
        with self.assertRaises(ValidationError):
            growth_record = GrowthRecord(
                character_sheet=self.character,
                session_date=date(2024, 1, 15),
                scenario_name="テストシナリオ",
                sanity_lost=-1  # 負の値は無効
            )
            growth_record.full_clean()
        
        # 正気度獲得・喪失の上限テスト
        with self.assertRaises(ValidationError):
            growth_record = GrowthRecord(
                character_sheet=self.character,
                session_date=date(2024, 1, 15),
                scenario_name="テストシナリオ",
                sanity_lost=100  # 99を超える値は無効
            )
            growth_record.full_clean()
    
    def test_net_sanity_calculation(self):
        """正気度増減の計算テスト"""
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="テストシナリオ",
            sanity_gained=2,
            sanity_lost=7
        )
        
        net_sanity = growth_record.calculate_net_sanity_change()
        self.assertEqual(net_sanity, -5)  # 2 - 7 = -5


class SkillGrowthRecordModelTestCase(TestCase):
    """技能成長記録モデルのテストケース"""
    
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
        
        # 成長記録を作成
        self.growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="テストシナリオ"
        )
        
        # 技能を作成
        self.skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
            current_value=65
        )
    
    def test_skill_growth_record_creation(self):
        """技能成長記録の作成テスト"""
        skill_growth = SkillGrowthRecord.objects.create(
            growth_record=self.growth_record,
            skill_name="目星",
            had_experience_check=True,
            growth_roll_result=85,
            old_value=65,
            new_value=70,
            growth_amount=5
        )
        
        self.assertEqual(skill_growth.growth_record, self.growth_record)
        self.assertEqual(skill_growth.skill_name, "目星")
        self.assertTrue(skill_growth.had_experience_check)
        self.assertEqual(skill_growth.growth_roll_result, 85)
        self.assertEqual(skill_growth.old_value, 65)
        self.assertEqual(skill_growth.new_value, 70)
        self.assertEqual(skill_growth.growth_amount, 5)
    
    def test_skill_growth_validation(self):
        """技能成長記録のバリデーションテスト"""
        # 技能値の範囲チェック
        with self.assertRaises(ValidationError):
            skill_growth = SkillGrowthRecord(
                growth_record=self.growth_record,
                skill_name="目星",
                old_value=95,  # 90を超える値
                new_value=98
            )
            skill_growth.full_clean()
        
        # 成長量の整合性チェック
        with self.assertRaises(ValidationError):
            skill_growth = SkillGrowthRecord(
                growth_record=self.growth_record,
                skill_name="目星",
                old_value=60,
                new_value=65,
                growth_amount=10  # 実際は5なのに10と記録
            )
            skill_growth.full_clean()
    
    def test_growth_success_calculation(self):
        """成長成功判定の計算テスト"""
        # 成功ケース (成長ロール > 現在値)
        skill_growth = SkillGrowthRecord.objects.create(
            growth_record=self.growth_record,
            skill_name="目星",
            had_experience_check=True,
            growth_roll_result=85,  # 65より大きい
            old_value=65,
            new_value=70,
            growth_amount=5  # 成長量を明示的に設定
        )
        
        self.assertTrue(skill_growth.is_growth_successful())
        
        # 失敗ケース (成長ロール <= 現在値)
        skill_growth_fail = SkillGrowthRecord.objects.create(
            growth_record=self.growth_record,
            skill_name="聞き耳",
            had_experience_check=True,
            growth_roll_result=50,  # 65以下
            old_value=65,
            new_value=65,
            growth_amount=0  # 成長なし
        )
        
        self.assertFalse(skill_growth_fail.is_growth_successful())


class GrowthRecordAPITestCase(APITestCase):
    """成長記録管理APIのテストケース"""
    
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
    
    def test_create_growth_record_api(self):
        """成長記録作成APIテスト"""
        growth_data = {
            'session_date': '2024-01-15',
            'scenario_name': '影の館',
            'gm_name': '田中GM',
            'sanity_gained': 0,
            'sanity_lost': 5,
            'experience_gained': 3,
            'special_rewards': '古い日記を発見',
            'notes': '初回セッション'
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/growth-records/',
            growth_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['scenario_name'], '影の館')
        self.assertEqual(response.data['sanity_lost'], 5)
        
        # データベースに保存されたか確認
        growth_record = GrowthRecord.objects.get(character_sheet=self.character)
        self.assertEqual(growth_record.scenario_name, '影の館')
        self.assertEqual(growth_record.sanity_lost, 5)
    
    def test_get_growth_records_list_api(self):
        """成長記録一覧取得APIテスト"""
        # テスト用の成長記録を作成
        GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="影の館",
            sanity_lost=5
        )
        GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 2, 20),
            scenario_name="古い屋敷",
            sanity_lost=3
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/growth-records/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # 日付順でソートされているか確認（新しい順）
        self.assertEqual(response.data[0]['scenario_name'], "古い屋敷")
        self.assertEqual(response.data[1]['scenario_name'], "影の館")
    
    def test_add_skill_growth_to_record_api(self):
        """技能成長記録追加APIテスト"""
        # 成長記録を作成
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="テストシナリオ"
        )
        
        # 技能を作成
        skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
            current_value=65
        )
        
        skill_growth_data = {
            'skill_name': '目星',
            'had_experience_check': True,
            'growth_roll_result': 85,
            'old_value': 65,
            'new_value': 70,
            'growth_amount': 5
        }
        
        response = self.client.post(
            f'/accounts/character-sheets/{self.character.id}/growth-records/{growth_record.id}/add-skill-growth/',
            skill_growth_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['skill_name'], '目星')
        self.assertEqual(response.data['growth_amount'], 5)
        
        # データベースに保存されたか確認
        skill_growth = SkillGrowthRecord.objects.get(
            growth_record=growth_record,
            skill_name='目星'
        )
        self.assertEqual(skill_growth.growth_amount, 5)
    
    def test_get_growth_summary_api(self):
        """成長サマリー取得APIテスト"""
        # 複数の成長記録を作成
        growth1 = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="影の館",
            sanity_lost=5,
            experience_gained=3
        )
        growth2 = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 2, 20),
            scenario_name="古い屋敷",
            sanity_lost=3,
            experience_gained=2
        )
        
        response = self.client.get(
            f'/accounts/character-sheets/{self.character.id}/growth-summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_sessions'], 2)
        self.assertEqual(response.data['total_sanity_lost'], 8)
        self.assertEqual(response.data['total_experience'], 5)
        self.assertIn('recent_scenarios', response.data)


class GrowthRecordIntegrationTestCase(TestCase):
    """成長記録統合テストケース"""
    
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
            occupation='私立探偵',
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
    
    def test_complete_session_growth_workflow(self):
        """完全なセッション成長ワークフローのテスト"""
        # 1. セッション前の技能値を記録
        initial_skill = CharacterSkill.objects.create(
            character_sheet=self.character,
            skill_name="目星",
            base_value=25,
            occupation_points=40,
            current_value=65
        )
        
        # 2. セッション記録を作成
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2024, 1, 15),
            scenario_name="影の館",
            gm_name="田中GM",
            sanity_gained=0,
            sanity_lost=5,
            experience_gained=3,
            special_rewards="古い日記",
            notes="恐怖体験あり、技能成長1回"
        )
        
        # 3. 技能成長記録を追加
        skill_growth = SkillGrowthRecord.objects.create(
            growth_record=growth_record,
            skill_name="目星",
            had_experience_check=True,
            growth_roll_result=85,  # 65より大きいので成功
            old_value=65,
            new_value=70,
            growth_amount=5
        )
        
        # 4. 実際の技能値を更新（ポイントを増やして70にする）
        # 65 から 70 にするには 5 ポイント必要（other_points で追加）
        initial_skill.other_points = 5
        initial_skill.save()
        
        # 5. 正気度を更新（例）
        initial_sanity = self.character.sanity_current
        self.character.sanity_current = initial_sanity - 5
        self.character.save()
        
        # 検証
        self.assertEqual(growth_record.character_sheet, self.character)
        self.assertEqual(skill_growth.growth_record, growth_record)
        self.assertTrue(skill_growth.is_growth_successful())
        self.assertEqual(skill_growth.growth_amount, 5)
        
        # 更新後の値確認
        initial_skill.refresh_from_db()
        self.assertEqual(initial_skill.current_value, 70)
        
        self.character.refresh_from_db()
        self.assertEqual(self.character.sanity_current, initial_sanity - 5)
    
    def test_multiple_sessions_progression(self):
        """複数セッションでの成長進歩テスト"""
        # 複数セッションを作成
        sessions_data = [
            {
                'date': date(2024, 1, 15),
                'scenario': '影の館',
                'sanity_lost': 5,
                'experience': 3
            },
            {
                'date': date(2024, 2, 20),
                'scenario': '古い屋敷',
                'sanity_lost': 3,
                'experience': 2
            },
            {
                'date': date(2024, 3, 10),
                'scenario': '深海の秘密',
                'sanity_lost': 8,
                'experience': 4
            }
        ]
        
        total_sanity_lost = 0
        total_experience = 0
        
        for session_data in sessions_data:
            growth_record = GrowthRecord.objects.create(
                character_sheet=self.character,
                session_date=session_data['date'],
                scenario_name=session_data['scenario'],
                sanity_lost=session_data['sanity_lost'],
                experience_gained=session_data['experience']
            )
            
            total_sanity_lost += session_data['sanity_lost']
            total_experience += session_data['experience']
        
        # 全記録の確認
        all_records = GrowthRecord.objects.filter(character_sheet=self.character)
        self.assertEqual(all_records.count(), 3)
        
        # 累計確認
        total_lost = sum(record.sanity_lost for record in all_records)
        total_exp = sum(record.experience_gained for record in all_records)
        
        self.assertEqual(total_lost, 16)  # 5 + 3 + 8
        self.assertEqual(total_exp, 9)    # 3 + 2 + 4