"""
成長記録システムの統合テスト
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from datetime import date
from accounts.character_models import (
    CharacterSheet, CharacterSheet6th, CharacterSkill,
    GrowthRecord, SkillGrowthRecord
)

User = get_user_model()


class GrowthRecordIntegrationTest(TestCase):
    """成長記録の統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # テストユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # APIクライアント設定
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # テスト用キャラクターシート作成
        # 副次ステータスを計算
        import math
        hp_max = math.ceil((14 + 10) / 2)  # (CON + SIZ) / 2
        mp_max = 15  # POW
        san_start = 15 * 5  # POW * 5
        san_max = 99  # 6版のデフォルト
        
        self.character = CharacterSheet.objects.create(
            user=self.user,
            edition='6th',
            name='テスト探索者',
            player_name=self.user.username,
            age=25,
            str_value=12,
            con_value=14,
            pow_value=15,
            dex_value=13,
            app_value=11,
            siz_value=10,
            int_value=16,
            edu_value=17,
            hit_points_max=hp_max,
            hit_points_current=hp_max,
            magic_points_max=mp_max,
            magic_points_current=mp_max,
            sanity_starting=san_start,
            sanity_max=san_max,
            sanity_current=san_start,
        )
        
        # 6版データ作成
        CharacterSheet6th.objects.create(
            character_sheet=self.character,
            mental_disorder=''
        )
        
        # テスト用スキル作成
        self.skills = [
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='図書館',
                base_value=20,
                occupation_points=40,
                interest_points=10,
                other_points=0,
                current_value=70
            ),
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='目星',
                base_value=25,
                occupation_points=20,
                interest_points=5,
                other_points=0,
                current_value=50
            ),
            CharacterSkill.objects.create(
                character_sheet=self.character,
                skill_name='回避',
                base_value=self.character.dex_value * 2,
                occupation_points=0,
                interest_points=10,
                other_points=0,
                current_value=self.character.dex_value * 2 + 10
            )
        ]
    
    def test_create_growth_record(self):
        """成長記録の作成テスト"""
        url = reverse('growth-records-list', kwargs={
            'character_sheet_id': self.character.id
        })
        
        data = {
            'session_date': '2025-01-13',
            'scenario_name': 'クトゥルフの呼び声',
            'gm_name': 'テストGM',
            'sanity_gained': 5,
            'sanity_lost': 10,
            'experience_gained': 3,
            'special_rewards': '魔道書「無名祭祀書」',
            'notes': 'ニャルラトホテプとの遭遇'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # データベースに保存されたか確認
        growth_record = GrowthRecord.objects.get(
            character_sheet=self.character,
            scenario_name='クトゥルフの呼び声'
        )
        self.assertEqual(growth_record.gm_name, 'テストGM')
        self.assertEqual(growth_record.calculate_net_sanity_change(), -5)
    
    def test_create_growth_record_with_skill_growths(self):
        """スキル成長付き成長記録の作成テスト"""
        url = reverse('growth-records-list', kwargs={
            'character_sheet_id': self.character.id
        })
        
        data = {
            'session_date': '2025-01-13',
            'scenario_name': 'ダンウィッチの怪',
            'gm_name': 'テストGM',
            'sanity_gained': 3,
            'sanity_lost': 8,
            'experience_gained': 5,
            'skill_growths': [
                {
                    'skill_name': '図書館',
                    'old_value': 70,
                    'new_value': 73,
                    'growth_roll_result': 85,
                    'had_experience_check': True,
                    'notes': '成功ロールで成長'
                },
                {
                    'skill_name': '目星',
                    'old_value': 50,
                    'new_value': 51,
                    'growth_roll_result': 92,
                    'had_experience_check': True,
                    'notes': '成功ロールで成長'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # スキル成長が保存されたか確認
        growth_record = GrowthRecord.objects.get(
            character_sheet=self.character,
            scenario_name='ダンウィッチの怪'
        )
        skill_growths = growth_record.skill_growths.all()
        self.assertEqual(skill_growths.count(), 2)
        
        # 図書館の成長確認
        library_growth = skill_growths.get(skill_name='図書館')
        self.assertEqual(library_growth.growth_amount, 3)
        self.assertTrue(library_growth.is_growth_successful())
    
    def test_list_growth_records(self):
        """成長記録一覧取得テスト"""
        # テストデータ作成
        for i in range(3):
            growth_record = GrowthRecord.objects.create(
                character_sheet=self.character,
                session_date=date(2025, 1, i+1),
                scenario_name=f'シナリオ{i+1}',
                gm_name='テストGM',
                sanity_gained=i,
                sanity_lost=i*2,
                experience_gained=i+1
            )
        
        url = reverse('growth-records-list', kwargs={
            'character_sheet_id': self.character.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # 日付降順でソートされているか確認
        dates = [record['session_date'] for record in response.data]
        self.assertEqual(dates, ['2025-01-03', '2025-01-02', '2025-01-01'])
    
    def test_add_skill_growth_to_existing_record(self):
        """既存の成長記録にスキル成長を追加するテスト"""
        # 成長記録作成
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2025, 1, 13),
            scenario_name='狂気山脈',
            gm_name='テストGM',
            sanity_gained=0,
            sanity_lost=15,
            experience_gained=4
        )
        
        url = reverse('growth-records-add-skill', kwargs={
            'character_sheet_id': self.character.id,
            'pk': growth_record.id
        })
        
        data = {
            'skill_name': '回避',
            'old_value': 36,
            'new_value': 38,
            'growth_roll_result': 95,
            'had_experience_check': True,
            'notes': '古のものから逃げ切った'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # スキル成長が追加されたか確認
        skill_growth = SkillGrowthRecord.objects.get(
            growth_record=growth_record,
            skill_name='回避'
        )
        self.assertEqual(skill_growth.growth_amount, 2)
    
    def test_growth_summary(self):
        """成長サマリー取得テスト"""
        # 複数の成長記録を作成
        for i in range(5):
            growth_record = GrowthRecord.objects.create(
                character_sheet=self.character,
                session_date=date(2025, 1, i+1),
                scenario_name=f'シナリオ{i+1}',
                gm_name='テストGM',
                sanity_gained=i*2,
                sanity_lost=i*3,
                experience_gained=i+1
            )
            
            # スキル成長も追加
            if i % 2 == 0:
                SkillGrowthRecord.objects.create(
                    growth_record=growth_record,
                    skill_name='図書館',
                    old_value=70+i,
                    new_value=70+i+2,
                    growth_amount=2,
                    growth_roll_result=90+i,
                    had_experience_check=True
                )
        
        url = reverse('growth-records-summary', kwargs={
            'character_sheet_id': self.character.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data
        self.assertEqual(summary['total_sessions'], 5)
        self.assertEqual(summary['total_san_gained'], 20)  # 0+2+4+6+8
        self.assertEqual(summary['total_san_lost'], 30)    # 0+3+6+9+12
        self.assertEqual(summary['net_san_change'], -10)
        self.assertEqual(summary['total_experience'], 15)   # 1+2+3+4+5
        
        # スキル成長統計確認
        self.assertIn('図書館', summary['skill_growth_stats'])
        library_stats = summary['skill_growth_stats']['図書館']
        self.assertEqual(library_stats['total_growth'], 6)  # 3回×2
        self.assertEqual(library_stats['growth_count'], 3)
    
    def test_delete_growth_record(self):
        """成長記録の削除テスト"""
        growth_record = GrowthRecord.objects.create(
            character_sheet=self.character,
            session_date=date(2025, 1, 13),
            scenario_name='削除テスト',
            gm_name='テストGM',
            sanity_gained=0,
            sanity_lost=5,
            experience_gained=2
        )
        
        url = reverse('growth-records-detail', kwargs={
            'character_sheet_id': self.character.id,
            'pk': growth_record.id
        })
        
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 削除されたか確認
        self.assertFalse(
            GrowthRecord.objects.filter(id=growth_record.id).exists()
        )
    
    def test_unauthorized_access(self):
        """他のユーザーのキャラクターシートへのアクセステスト"""
        # 別のユーザーを作成
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        # 別ユーザーのキャラクター作成
        import math
        other_hp_max = math.ceil((10 + 10) / 2)
        other_mp_max = 10
        other_san_start = 10 * 5
        
        other_character = CharacterSheet.objects.create(
            user=other_user,
            edition='6th',
            name='他人の探索者',
            player_name=other_user.username,
            age=30,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=other_hp_max,
            hit_points_current=other_hp_max,
            magic_points_max=other_mp_max,
            magic_points_current=other_mp_max,
            sanity_starting=other_san_start,
            sanity_max=99,
            sanity_current=other_san_start,
        )
        
        # 他人のキャラクターの成長記録にアクセス
        url = reverse('growth-records-list', kwargs={
            'character_sheet_id': other_character.id
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_validation_errors(self):
        """バリデーションエラーのテスト"""
        url = reverse('growth-records-list', kwargs={
            'character_sheet_id': self.character.id
        })
        
        # 無効なSAN値
        data = {
            'session_date': '2025-01-13',
            'scenario_name': 'バリデーションテスト',
            'sanity_gained': 100,  # 無効（0-99の範囲外）
            'sanity_lost': -5,     # 無効（負の値）
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sanity_gained', response.data)
        self.assertIn('sanity_lost', response.data)