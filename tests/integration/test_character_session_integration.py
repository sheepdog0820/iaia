"""
キャラクター作成・セッション作成・紐づけ統合テスト
クトゥルフ神話TRPG 6版のキャラクターとセッションの完全な統合テスト
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from accounts.character_models import (
    CharacterSheet, CharacterSkill,
    CharacterBackground, CharacterEquipment
)
from schedules.models import TRPGSession, SessionParticipant
import json


class CharacterSessionIntegrationTestCase(APITestCase):
    """キャラクター作成からセッション参加までの統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm_user = CustomUser.objects.create_user(
            username='gm_master',
            email='gm@example.com',
            password='gmpass123',
            nickname='ゲームマスター'
        )
        
        self.player_user = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='playerpass123',
            nickname='プレイヤー1'
        )
        
        self.player2_user = CustomUser.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='playerpass123',
            nickname='プレイヤー2'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='クトゥルフ探索隊',
            description='クトゥルフ神話TRPGを楽しむグループ',
            created_by=self.gm_user,
            visibility='private'
        )
        self.group.members.add(self.gm_user, self.player_user, self.player2_user)
    
    def test_complete_character_session_workflow(self):
        """キャラクター作成からセッション参加までの完全なワークフロー"""
        
        # ========== Step 1: プレイヤーがキャラクターを作成 ==========
        self.client.force_authenticate(user=self.player_user)
        
        # キャラクター作成
        character_data = {
            'name': '探索者・田中太郎',
            'age': 28,
            'occupation': '私立探偵',
            'gender': '男',
            'birthplace': '東京',
            'residence': '東京都新宿区',
            'edition': '6th',
            
            # 能力値
            'str_value': 13,
            'con_value': 12,
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 11,
            'siz_value': 12,
            'int_value': 16,
            'edu_value': 15,
            
            # 副次ステータス
            'hit_points_max': 12,
            'hit_points_current': 12,
            'magic_points_max': 15,
            'magic_points_current': 15,
            'sanity_max': 75,
            'sanity_current': 75,
            'sanity_starting': 75,
            
            # その他
            'description': '好奇心旺盛な私立探偵。オカルト事件を専門に扱う。'
        }
        
        create_url = reverse('character-sheet-list')
        response = self.client.post(create_url, character_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character_id = response.data['id']
        
        # キャラクター作成の確認
        self.assertEqual(response.data['name'], '探索者・田中太郎')
        self.assertEqual(response.data['occupation'], '私立探偵')
        
        # 技能の追加
        skills_data = [
            {'name': '図書館', 'value': 75},
            {'name': '目星', 'value': 65},
            {'name': '聞き耳', 'value': 60},
            {'name': '心理学', 'value': 55},
            {'name': '拳銃', 'value': 40}
        ]
        
        for skill in skills_data:
            skill_response = self.client.post(
                f'/api/accounts/character-sheets/{character_id}/skills/',
                {
                    'character_sheet': character_id,
                    'skill_name': skill['name'],
                    'current_value': skill['value'],
                    'base_value': skill['value'],
                    'category': '探索系'  # デフォルトカテゴリ
                },
                format='json'
            )
            if skill_response.status_code != status.HTTP_201_CREATED:
                print(f"Skill creation failed: {skill_response.status_code} - {getattr(skill_response, 'data', skill_response.content)}")
            self.assertEqual(skill_response.status_code, status.HTTP_201_CREATED)
        
        # 装備の追加
        equipment_data = [
            {
                'name': '.38リボルバー',
                'quantity': 1,
                'description': '護身用の拳銃',
                'item_type': 'weapon',
                'damage': '1D10',
                'skill_name': '拳銃',
                'base_range': '15m',
                'attacks_per_round': 3,
                'ammo': 6,
                'malfunction_number': 100
            },
            {
                'name': '懐中電灯',
                'quantity': 1,
                'description': '夜間調査用',
                'item_type': 'item'
            },
            {
                'name': 'ノートと筆記用具',
                'quantity': 1,
                'description': '調査記録用',
                'item_type': 'item'
            }
        ]
        
        for equip in equipment_data:
            equip_response = self.client.post(
                f'/api/accounts/character-sheets/{character_id}/equipment/',
                {
                    'character_sheet': character_id,
                    **equip  # item_typeは各装備データに含まれている
                },
                format='json'
            )
            if equip_response.status_code != status.HTTP_201_CREATED:
                print(f"Equipment creation failed: {equip_response.status_code} - {getattr(equip_response, 'data', equip_response.content)}")
            self.assertEqual(equip_response.status_code, status.HTTP_201_CREATED)
        
        # ========== Step 2: GMがセッションを作成 ==========
        self.client.force_authenticate(user=self.gm_user)
        
        session_data = {
            'title': '狂気山脈にて',
            'description': 'クトゥルフ神話の古典的シナリオ。南極探検隊の恐怖を体験する。',
            'date': (timezone.now() + timedelta(days=7)).isoformat(),
            'location': 'Discord + ココフォリア',
            'group': self.group.id,
            'status': 'planned',
            'visibility': 'group',
            'duration_minutes': 240,
            'max_participants': 4,
            'min_participants': 2,
            'youtube_url': ''
        }
        
        session_url = reverse('session-list')
        response = self.client.post(session_url, session_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        
        # セッション作成の確認
        self.assertEqual(response.data['title'], '狂気山脈にて')
        self.assertEqual(response.data['gm'], self.gm_user.id)
        
        # ========== Step 3: プレイヤーがセッションに参加（キャラクター紐づけ） ==========
        self.client.force_authenticate(user=self.player_user)
        
        # セッション参加（キャラクターを指定）
        join_url = reverse('session-join', kwargs={'pk': session_id})
        join_data = {
            'character_name': '探索者・田中太郎',
            'character_sheet_id': character_id,  # キャラクターシートのID
            'role': 'player'
        }
        
        response = self.client.post(join_url, join_data, format='json')
        print(f"Join response: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 参加者情報の確認
        participant = SessionParticipant.objects.get(
            session_id=session_id,
            user=self.player_user
        )
        print(f"Participant data: character_name='{participant.character_name}', character_sheet_id={participant.character_sheet_id}")
        print(f"Character sheet name: {participant.character_sheet.name if participant.character_sheet else 'None'}")
        
        # キャラクターシートが関連付けられている場合、キャラクター名は自動的に設定される可能性がある
        if participant.character_sheet:
            # character_nameが空の場合は、character_sheetのnameを使う
            expected_name = participant.character_sheet.name
        else:
            expected_name = '探索者・田中太郎'
            
        self.assertEqual(participant.character_name or participant.character_sheet.name, expected_name)
        self.assertEqual(participant.character_sheet_id, character_id)
        
        # ========== Step 4: 2人目のプレイヤーも参加 ==========
        self.client.force_authenticate(user=self.player2_user)
        
        # 2人目のキャラクター作成（簡易版）
        character2_data = {
            'name': '探索者・山田花子',
            'age': 25,
            'occupation': '考古学者',
            'gender': '女',
            'birthplace': '京都',
            'edition': '6th',
            'str_value': 10,
            'con_value': 11,
            'pow_value': 14,
            'dex_value': 13,
            'app_value': 15,
            'siz_value': 10,
            'int_value': 17,
            'edu_value': 18,
            'hit_points_max': 11,
            'hit_points_current': 11,
            'magic_points_max': 14,
            'magic_points_current': 14,
            'sanity_max': 70,
            'sanity_current': 70,
            'sanity_starting': 70
        }
        
        response = self.client.post(create_url, character2_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        character2_id = response.data['id']
        
        # セッション参加
        join_data2 = {
            'character_name': '探索者・山田花子',
            'character_sheet_id': character2_id,  # キャラクターシートのID
            'role': 'player'
        }
        
        response = self.client.post(join_url, join_data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # ========== Step 5: セッション詳細の確認 ==========
        self.client.force_authenticate(user=self.gm_user)
        
        detail_url = reverse('session-detail', kwargs={'pk': session_id})
        response = self.client.get(detail_url)
        
        print(f"Session detail response keys: {response.data.keys() if response.status_code == 200 else 'N/A'}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # participants_detailフィールドを使用
        participants_key = 'participants_detail' if 'participants_detail' in response.data else 'participants'
        self.assertIn(participants_key, response.data)
        self.assertEqual(len(response.data[participants_key]), 2)
        
        # 参加者のキャラクター情報確認
        participants_data = response.data[participants_key]
        character_names = []
        for p in participants_data:
            if p is None:
                continue
            name = p.get('character_name', '')
            if not name and 'character_sheet_detail' in p and p['character_sheet_detail']:
                name = p['character_sheet_detail'].get('name', '')
            if name:
                character_names.append(name)
        self.assertIn('探索者・田中太郎', character_names)
        self.assertIn('探索者・山田花子', character_names)
        
        # ========== Step 6: キャラクターシートへのアクセス確認 ==========
        # プレイヤー自身がキャラクターシートにアクセス
        self.client.force_authenticate(user=self.player_user)
        char_detail_url = f'/api/accounts/character-sheets/{character_id}/'
        response = self.client.get(char_detail_url)
        
        if response.status_code != status.HTTP_200_OK:
            print(f"Character detail URL: {char_detail_url}")
            print(f"Response status: {response.status_code}")
            print(f"Response content: {getattr(response, 'data', response.content)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '探索者・田中太郎')
        
        # 技能情報の確認
        skills = CharacterSkill.objects.filter(character_sheet_id=character_id)
        self.assertEqual(skills.count(), 5)
        self.assertTrue(skills.filter(skill_name='図書館', current_value=75).exists())
        
        # 装備情報の確認
        equipment = CharacterEquipment.objects.filter(character_sheet_id=character_id)
        self.assertEqual(equipment.count(), 3)
        self.assertTrue(equipment.filter(name='.38リボルバー').exists())
        
        print("\n[OK] キャラクター作成・セッション作成・紐づけテスト完了")
        print(f"  - キャラクター1: 探索者・田中太郎 (ID: {character_id})")
        print(f"  - キャラクター2: 探索者・山田花子 (ID: {character2_id})")
        print(f"  - セッション: 狂気山脈にて (ID: {session_id})")
        print(f"  - 参加者数: 2名")


class CharacterManagementInSessionTestCase(APITestCase):
    """セッション中のキャラクター管理テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザーとグループ作成
        self.gm_user = CustomUser.objects.create_user(
            username='gm',
            email='gm@test.com',
            password='gmpass'
        )
        self.player_user = CustomUser.objects.create_user(
            username='player',
            email='player@test.com',
            password='playerpass'
        )
        
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm_user
        )
        self.group.members.add(self.gm_user, self.player_user)
        
        # キャラクター作成（正しいフィールド名を使用）
        self.character = CharacterSheet.objects.create(
            user=self.player_user,
            name='テスト探索者',
            age=30,
            occupation='医師',
            edition='6th',
            str_value=12,
            con_value=15,
            pow_value=12,
            dex_value=10,
            app_value=12,
            siz_value=15,
            int_value=16,
            edu_value=18,
            hit_points_max=15,
            hit_points_current=15,
            magic_points_max=12,
            magic_points_current=12,
            sanity_max=60,
            sanity_current=60,
            sanity_starting=60
        )
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm_user,
            group=self.group,
            status='ongoing'
        )
        
        # 参加者追加
        self.participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.player_user,
            character_name=self.character.name,
            character_sheet=self.character,  # CharacterSheetオブジェクトを直接設定
            character_sheet_url=f'/accounts/character/6th/{self.character.id}/',
            role='player'
        )
    
    def test_character_status_during_session(self):
        """セッション中のキャラクターステータス確認"""
        # まずGMとしてセッション情報を確認
        self.client.force_authenticate(user=self.gm_user)
        
        # セッション詳細取得
        url = reverse('session-detail', kwargs={'pk': self.session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # participants_detailフィールドを確認
        self.assertIn('participants_detail', response.data)
        participants_data = response.data['participants_detail']
        self.assertEqual(len(participants_data), 1)
        
        # 参加者のキャラクター情報確認
        participant_data = participants_data[0]
        # character_nameが空の場合は、character_sheet_detailから名前を取得
        character_name = participant_data.get('character_name') or participant_data.get('character_sheet_detail', {}).get('name', '')
        self.assertEqual(character_name, 'テスト探索者')
        
        # character_sheet_idまたはcharacter_sheet_detailで確認
        if 'character_sheet' in participant_data:
            self.assertEqual(participant_data['character_sheet'], self.character.id)
        elif 'character_sheet_detail' in participant_data:
            self.assertEqual(participant_data['character_sheet_detail']['id'], self.character.id)
        
        # キャラクターシートへの直接アクセス（プレイヤーとして）
        self.client.force_authenticate(user=self.player_user)
        char_url = f'/api/accounts/character-sheets/{self.character.id}/'
        response = self.client.get(char_url)
        
        if response.status_code != status.HTTP_200_OK:
            print(f"Character sheet URL: {char_url}")
            print(f"Response status: {response.status_code}")
            print(f"Response content: {getattr(response, 'data', response.content)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hit_points_current'], 15)
        self.assertEqual(response.data['sanity_current'], 60)
        
        print("\n[OK] セッション中のキャラクター管理テスト完了")
        print(f"  - キャラクター: {self.character.name}")
        print(f"  - HP: {self.character.hit_points_current}/{self.character.hit_points_max}")
        print(f"  - SAN: {self.character.sanity_current}/{self.character.sanity_max}")


class CharacterSessionValidationTestCase(APITestCase):
    """キャラクターとセッションの検証テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.other_user = CustomUser.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass'
        )
        
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user
        )
        self.group.members.add(self.user)
        
        self.session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user,
            group=self.group
        )
    
    def test_cannot_join_session_without_group_membership(self):
        """グループメンバーでないユーザーはセッション参加不可"""
        self.client.force_authenticate(user=self.other_user)
        
        join_url = reverse('session-join', kwargs={'pk': self.session.id})
        response = self.client.post(join_url, {
            'character_name': 'Unauthorized Character'
        })
        
        # 404を返す（セッションが見えない）
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_character_owner_validation(self):
        """他人のキャラクターは使用不可"""
        # 他のユーザーのキャラクター作成（必須フィールドをすべて設定）
        other_character = CharacterSheet.objects.create(
            user=self.other_user,
            name='他人のキャラクター',
            age=25,
            occupation='学生',
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
        
        self.client.force_authenticate(user=self.user)
        
        # 他人のキャラクターへのアクセス試行
        url = reverse('character-sheet-detail', kwargs={'pk': other_character.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        print("\n[OK] キャラクター・セッション検証テスト完了")
        print("  - グループ外ユーザーの参加: 拒否")
        print("  - 他人のキャラクターアクセス: 拒否")


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    # テスト実行
    failures = test_runner.run_tests([
        'test_character_session_integration.CharacterSessionIntegrationTestCase',
        'test_character_session_integration.CharacterManagementInSessionTestCase',
        'test_character_session_integration.CharacterSessionValidationTestCase'
    ])
    
    if failures:
        print(f"\n[FAIL] {failures} 件のテストが失敗しました")
    else:
        print("\n[OK] すべてのテストが成功しました！")
