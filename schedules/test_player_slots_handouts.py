"""
プレイヤー枠とハンドアウト管理のテスト
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from accounts.character_models import CharacterSheet
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
import json


class PlayerSlotHandoutTestCase(APITestCase):
    """プレイヤー枠とハンドアウト機能のテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.gm = CustomUser.objects.create_user(
            username='gm',
            email='gm@example.com',
            password='password',
            nickname='GM'
        )
        
        self.players = []
        for i in range(5):  # 5人作成（4人+予備1人）
            player = CustomUser.objects.create_user(
                username=f'player{i+1}',
                email=f'player{i+1}@example.com',
                password='password',
                nickname=f'プレイヤー{i+1}'
            )
            self.players.append(player)
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm
        )
        self.group.members.add(self.gm)
        for player in self.players:
            self.group.members.add(player)
        
        # セッション作成
        self.session = TRPGSession.objects.create(
            title='プレイヤー枠テストセッション',
            description='4人用セッション',
            date=timezone.now() + timedelta(days=7),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # GMは自動的に参加者となる
        SessionParticipant.objects.create(
            session=self.session,
            user=self.gm,
            role='gm'
        )
        
        # キャラクター作成（各プレイヤー用）
        self.characters = []
        for i, player in enumerate(self.players[:4]):
            character = CharacterSheet.objects.create(
                user=player,
                name=f'探索者{i+1}',
                age=25 + i,
                occupation='探偵',
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
            self.characters.append(character)
    
    def test_assign_player_to_slot(self):
        """GMがプレイヤーを枠に割り当てる"""
        self.client.force_authenticate(user=self.gm)
        
        # プレイヤー1を枠1に割り当て
        url = reverse('session-assign-player', kwargs={'pk': self.session.id})
        data = {
            'player_slot': 1,
            'user_id': self.players[0].id,
            'character_sheet_id': self.characters[0].id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['player_slot'], 1)
        self.assertEqual(response.data['user'], self.players[0].id)
        self.assertEqual(response.data['character_sheet'], self.characters[0].id)
        
        # 同じ枠に別のプレイヤーを割り当てようとするとエラー
        data['user_id'] = self.players[1].id
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already taken', response.data['error'])
    
    def test_player_join_with_slot(self):
        """プレイヤーが枠を指定して参加"""
        self.client.force_authenticate(user=self.players[0])
        
        url = reverse('session-join', kwargs={'pk': self.session.id})
        data = {
            'player_slot': 2,
            'character_sheet_id': self.characters[0].id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['player_slot'], 2)
        
        # 既に取られた枠に参加しようとするとエラー
        self.client.force_authenticate(user=self.players[1])
        data['player_slot'] = 2
        data['character_sheet_id'] = self.characters[1].id
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already taken', response.data['error'])
    
    def test_create_handouts_with_numbers(self):
        """GMがHO1〜HO4を作成"""
        self.client.force_authenticate(user=self.gm)
        
        # プレイヤーを枠に割り当て
        for i in range(4):
            participant = SessionParticipant.objects.create(
                session=self.session,
                user=self.players[i],
                role='player',
                player_slot=i+1,
                character_sheet=self.characters[i]
            )
        
        # HO1〜HO4を作成
        handouts = []
        for i in range(4):
            participant = SessionParticipant.objects.get(
                session=self.session,
                player_slot=i+1
            )
            
            url = reverse('handout-list')
            data = {
                'session': self.session.id,
                'participant': participant.id,
                'title': f'HO{i+1}: 秘密の情報',
                'content': f'プレイヤー{i+1}への秘匿情報',
                'is_secret': True,
                'handout_number': i+1,
                'assigned_player_slot': i+1
            }
            
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['handout_number'], i+1)
            self.assertEqual(response.data['assigned_player_slot'], i+1)
            handouts.append(response.data)
        
        # 各プレイヤーは自分のHOのみ見える
        for i in range(4):
            self.client.force_authenticate(user=self.players[i])
            
            response = self.client.get(reverse('handout-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # 自分のHOのみ表示される
            # response.dataがリストかdictかを確認
            if isinstance(response.data, dict) and 'results' in response.data:
                handout_list = response.data['results']
            else:
                handout_list = response.data
            
            visible_handouts = [
                h for h in handout_list 
                if h['session'] == self.session.id and h['is_secret']
            ]
            
            self.assertEqual(len(visible_handouts), 1)
            self.assertEqual(visible_handouts[0]['handout_number'], i+1)
            self.assertEqual(visible_handouts[0]['assigned_player_slot'], i+1)
    
    def test_handout_visibility_by_slot(self):
        """プレイヤー枠に基づくハンドアウトの可視性"""
        # プレイヤー1を枠2に割り当て
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.players[0],
            role='player',
            player_slot=2
        )
        
        # HO2を作成（枠2に割り当て）
        self.client.force_authenticate(user=self.gm)
        
        handout = HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='HO2: 特別な情報',
            content='プレイヤー枠2への情報',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2
        )
        
        # プレイヤー1（枠2）はHO2を見れる
        self.client.force_authenticate(user=self.players[0])
        response = self.client.get(reverse('handout-list'))
        
        if isinstance(response.data, dict) and 'results' in response.data:
            handout_list = response.data['results']
        else:
            handout_list = response.data
            
        visible_handouts = [
            h for h in handout_list
            if h['id'] == handout.id
        ]
        self.assertEqual(len(visible_handouts), 1)
        
        # プレイヤー2（枠なし）はHO2を見れない
        self.client.force_authenticate(user=self.players[1])
        response = self.client.get(reverse('handout-list'))
        
        if isinstance(response.data, dict) and 'results' in response.data:
            handout_list = response.data['results']
        else:
            handout_list = response.data
            
        visible_handouts = [
            h for h in handout_list
            if h['id'] == handout.id
        ]
        self.assertEqual(len(visible_handouts), 0)
    
    def test_gm_can_see_all_handouts(self):
        """GMは全てのハンドアウトを閲覧可能"""
        # 4つのハンドアウトを作成
        for i in range(4):
            participant = SessionParticipant.objects.create(
                session=self.session,
                user=self.players[i],
                role='player',
                player_slot=i+1
            )
            
            HandoutInfo.objects.create(
                session=self.session,
                participant=participant,
                title=f'HO{i+1}',
                content=f'秘匿情報{i+1}',
                is_secret=True,
                handout_number=i+1,
                assigned_player_slot=i+1
            )
        
        # GMは全て見える
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(reverse('handout-list'))
        
        if isinstance(response.data, dict) and 'results' in response.data:
            handout_list = response.data['results']
        else:
            handout_list = response.data
            
        session_handouts = [
            h for h in handout_list
            if h['session'] == self.session.id
        ]
        self.assertEqual(len(session_handouts), 4)
        
        # HO番号順にソートされているか確認
        handout_numbers = [h['handout_number'] for h in session_handouts]
        self.assertEqual(handout_numbers, [1, 2, 3, 4])


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    failures = test_runner.run_tests([
        'schedules.test_player_slots_handouts.PlayerSlotHandoutTestCase'
    ])
    
    if failures:
        print(f"\n❌ {failures} 件のテストが失敗しました")
    else:
        print("\n✅ すべてのテストが成功しました！")