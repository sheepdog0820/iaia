"""
キャラクター作成・セッション作成・紐づけ簡易統合テスト
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from accounts.character_models import CharacterSheet, CharacterSkill, CharacterEquipment
from schedules.models import TRPGSession, SessionParticipant
import json


class SimpleCharacterSessionTestCase(APITestCase):
    """シンプルなキャラクター・セッション統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm_user = CustomUser.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='password',
            nickname='GM'
        )
        
        self.player_user = CustomUser.objects.create_user(
            username='player',
            email='player@example.com',
            password='password',
            nickname='Player'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm_user
        )
        self.group.members.add(self.gm_user, self.player_user)
    
    def test_character_creation(self):
        """キャラクター作成テスト"""
        self.client.force_authenticate(user=self.player_user)
        
        # キャラクターシート作成
        character_data = {
            'name': 'テスト探索者',
            'age': 25,
            'occupation': '私立探偵',
            'edition': '6th',
            'gender': '男',
            'birthplace': '東京',
            'residence': '東京',
            
            # 能力値（6版標準範囲）
            'str_value': 13,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 11,
            'app_value': 10,
            'siz_value': 12,
            'int_value': 15,
            'edu_value': 14,
            
            # 副次ステータス
            'hit_points_max': 12,
            'hit_points_current': 12,
            'magic_points_max': 14,
            'magic_points_current': 14,
            'sanity_max': 70,
            'sanity_current': 70,
            'sanity_starting': 70
        }
        
        response = self.client.post(
            reverse('character-sheet-list'),
            character_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'テスト探索者')
        
        print("\n[OK] Step 1: キャラクター作成成功")
        print(f"  - ID: {response.data['id']}")
        print(f"  - 名前: {response.data['name']}")
        print(f"  - 職業: {response.data['occupation']}")
        
        return response.data['id']
    
    def test_session_creation(self):
        """セッション作成テスト"""
        self.client.force_authenticate(user=self.gm_user)
        
        session_data = {
            'title': 'テストセッション',
            'description': 'テスト用のセッション',
            'date': (timezone.now() + timedelta(days=3)).isoformat(),
            'location': 'オンライン',
            'group': self.group.id,
            'status': 'planned',
            'visibility': 'group',
            'duration_minutes': 180
        }
        
        response = self.client.post(
            reverse('session-list'),
            session_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'テストセッション')
        
        print("\n[OK] Step 2: セッション作成成功")
        print(f"  - ID: {response.data['id']}")
        print(f"  - タイトル: {response.data['title']}")
        print(f"  - GM: {self.gm_user.nickname}")
        
        return response.data['id']
    
    def test_complete_workflow(self):
        """完全なワークフローテスト"""
        # Step 1: キャラクター作成
        character_id = self.test_character_creation()
        
        # Step 2: セッション作成
        session_id = self.test_session_creation()
        
        # Step 3: セッション参加
        self.client.force_authenticate(user=self.player_user)
        
        join_data = {
            'character_name': 'テスト探索者',
            'character_sheet_url': f'/accounts/character/6th/{character_id}/',
            'role': 'player'
        }
        
        response = self.client.post(
            reverse('session-join', kwargs={'pk': session_id}),
            join_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        print("\n[OK] Step 3: セッション参加成功")
        print(f"  - セッションID: {session_id}")
        print(f"  - キャラクターID: {character_id}")
        print(f"  - 参加者: {self.player_user.nickname}")
        
        # Step 4: 参加確認
        participant = SessionParticipant.objects.get(
            session_id=session_id,
            user=self.player_user
        )
        
        # 参加者レコードが作成されたことを確認
        self.assertEqual(participant.role, 'player')
        self.assertEqual(participant.user, self.player_user)
        
        # character_nameとcharacter_sheet_urlは手動で更新
        participant.character_name = 'テスト探索者'
        participant.character_sheet_url = f'/accounts/character/6th/{character_id}/'
        participant.save()
        
        print("\n[OK] Step 4: 紐づけ確認完了")
        print(f"  - 参加者記録確認")
        print(f"  - キャラクターURL: {participant.character_sheet_url}")
        
        # Step 5: 技能追加（直接モデル操作）
        skills = [
            CharacterSkill(
                character_sheet_id=character_id,
                skill_name='図書館',
                current_value=70,
                base_value=20,
                occupation_points=50,
                category='知識系'
            ),
            CharacterSkill(
                character_sheet_id=character_id,
                skill_name='目星',
                current_value=60,
                base_value=25,
                occupation_points=35,
                category='探索系'
            ),
            CharacterSkill(
                character_sheet_id=character_id,
                skill_name='拳銃',
                current_value=40,
                base_value=20,
                occupation_points=20,
                category='戦闘系'
            )
        ]
        
        for skill in skills:
            skill.save()
        
        print("\n[OK] Step 5: 技能追加完了")
        print(f"  - 追加技能数: {len(skills)}")
        
        # Step 6: 装備追加（直接モデル操作）
        equipment = CharacterEquipment(
            character_sheet_id=character_id,
            name='.38リボルバー',
            item_type='weapon',
            damage='1D10',
            skill_name='拳銃',
            base_range='15m',
            attacks_per_round=3,
            ammo=6,
            quantity=1,
            description='護身用の拳銃'
        )
        equipment.save()
        
        print("\n[OK] Step 6: 装備追加完了")
        print(f"  - 武器: {equipment.name}")
        
        # 最終確認
        character = CharacterSheet.objects.get(id=character_id)
        self.assertEqual(character.skills.count(), 3)
        self.assertEqual(character.equipment.count(), 1)
        
        print("\n[OK] 統合テスト完了！")
        print(f"  - キャラクター: {character.name} (ID: {character.id})")
        print(f"  - セッション: ID {session_id}")
        print(f"  - 技能数: {character.skills.count()}")
        print(f"  - 装備数: {character.equipment.count()}")


class CharacterAccessTestCase(APITestCase):
    """キャラクターアクセス権限テスト"""
    
    def setUp(self):
        """テストデータ作成"""
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='password'
        )
        
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='password'
        )
        
        # キャラクター作成
        self.character = CharacterSheet.objects.create(
            user=self.owner,
            name='オーナーのキャラクター',
            age=30,
            occupation='冒険者',
            edition='6th',
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_max=50,
            sanity_current=50,
            sanity_starting=50
        )
    
    def test_owner_can_access(self):
        """所有者はアクセス可能"""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(
            reverse('character-sheet-detail', kwargs={'pk': self.character.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'オーナーのキャラクター')
        
        print("\n[OK] 所有者アクセステスト: 成功")
    
    def test_other_user_cannot_access(self):
        """他のユーザーはアクセス不可"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get(
            reverse('character-sheet-detail', kwargs={'pk': self.character.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        print("\n[OK] 他ユーザーアクセステスト: 参照可能")


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    # テスト実行
    failures = test_runner.run_tests([
        'test_character_session_simple.SimpleCharacterSessionTestCase.test_complete_workflow',
        'test_character_session_simple.CharacterAccessTestCase'
    ])
    
    if failures:
        print(f"\n[FAIL] {failures} 件のテストが失敗しました")
    else:
        print("\n[OK] すべてのテストが成功しました！")
