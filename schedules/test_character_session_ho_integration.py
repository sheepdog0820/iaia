"""
キャラクター作成、セッション作成、HOごとのキャラクター設定の統合テスト
"""

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from accounts.models import CustomUser, Group
from accounts.character_models import CharacterSheet, CharacterSkill
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
import json


class CharacterSessionHOIntegrationTestCase(APITestCase):
    """キャラクター作成からHO設定までの統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # GM作成
        self.gm = CustomUser.objects.create_user(
            username='gamemaster',
            email='gm@example.com',
            password='gmpassword',
            nickname='ゲームマスター'
        )
        
        # プレイヤー4人作成
        self.players = []
        for i in range(4):
            player = CustomUser.objects.create_user(
                username=f'player{i+1}',
                email=f'player{i+1}@example.com',
                password='playerpassword',
                nickname=f'プレイヤー{i+1}'
            )
            self.players.append(player)
        
        # グループ作成
        self.group = Group.objects.create(
            name='クトゥルフ神話TRPGグループ',
            created_by=self.gm,
            visibility='private'
        )
        self.group.members.add(self.gm)
        for player in self.players:
            self.group.members.add(player)
    
    def test_full_integration_flow(self):
        """完全な統合フロー: キャラクター作成 → セッション作成 → HO割り当て → キャラクター紐付け"""
        
        # ===== STEP 1: 各プレイヤーがキャラクターを作成 =====
        characters = []
        occupations = ['探偵', '医師', 'ジャーナリスト', '考古学者']
        
        for i, player in enumerate(self.players):
            self.client.force_authenticate(user=player)
            
            # キャラクター作成
            character_data = {
                'name': f'{occupations[i]}の{player.nickname}',
                'age': 25 + i * 2,
                'occupation': occupations[i],
                'edition': '6th',
                'str_value': 10 + i,
                'con_value': 11 + i,
                'pow_value': 12 + i,
                'dex_value': 13 + i,
                'app_value': 10,
                'siz_value': 11,
                'int_value': 14 + i,
                'edu_value': 15 + i,
                'hit_points_max': 11,
                'hit_points_current': 11,
                'magic_points_max': 12,
                'magic_points_current': 12,
                'sanity_max': 60 + i * 5,
                'sanity_current': 60 + i * 5,
                'sanity_starting': 60 + i * 5
            }
            
            response = self.client.post(
                reverse('character-sheet-list'),
                character_data,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['name'], character_data['name'])
            self.assertEqual(response.data['occupation'], character_data['occupation'])
            
            # 作成されたキャラクターを保存
            character = CharacterSheet.objects.get(id=response.data['id'])
            characters.append(character)
            
            # 基本技能を追加
            basic_skills = [
                ('目星', 25 + i * 5),
                ('聞き耳', 20 + i * 5),
                ('図書館', 25 + i * 3),
                ('回避', int(character.dex_value * 2))
            ]
            
            for skill_name, value in basic_skills:
                CharacterSkill.objects.create(
                    character_sheet=character,
                    skill_name=skill_name,
                    current_value=value
                )
        
        # ===== STEP 2: GMがセッションを作成 =====
        self.client.force_authenticate(user=self.gm)
        
        session_data = {
            'title': '深淵の呼び声 - 4人用シナリオ',
            'description': '港町で起きた失踪事件を調査する探索者たち',
            'date': (timezone.now() + timedelta(days=7)).isoformat(),
            'location': 'オンライン（Discord）',
            'group': self.group.id,
            'status': 'planned',
            'visibility': 'private',
            'duration_minutes': 240
        }
        
        response = self.client.post(
            reverse('session-list'),
            session_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(id=response.data['id'])
        self.assertEqual(session.title, session_data['title'])
        
        # ===== STEP 3: GMが各プレイヤーを枠に割り当て =====
        for i, (player, character) in enumerate(zip(self.players, characters)):
            assign_data = {
                'player_slot': i + 1,  # 1-4の枠
                'user_id': player.id,
                'character_sheet_id': character.id
            }
            
            response = self.client.post(
                reverse('session-assign-player', kwargs={'pk': session.id}),
                assign_data,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['player_slot'], i + 1)
            self.assertEqual(response.data['character_sheet'], character.id)
        
        # ===== STEP 4: GMが各プレイヤー用のHOを作成 =====
        handout_contents = [
            {
                'title': 'HO1: 失踪した友人',
                'content': 'あなたの幼馴染が1週間前から行方不明になっている。最後に目撃されたのは港の倉庫街だった。'
            },
            {
                'title': 'HO2: 奇妙な夢',
                'content': 'ここ数日、海底から響く不気味な歌声の夢を見る。目覚めた後も耳鳴りが止まらない。'
            },
            {
                'title': 'HO3: 古い地図',
                'content': 'あなたの祖父が残した古い地図に、港の沖合に謎の印がつけられている。'
            },
            {
                'title': 'HO4: 調査依頼',
                'content': '港湾組合から密かに調査を依頼された。最近、漁師たちが奇妙な病気にかかっているという。'
            }
        ]
        
        handouts = []
        for i in range(4):
            participant = SessionParticipant.objects.get(
                session=session,
                player_slot=i+1
            )
            
            handout_data = {
                'session': session.id,
                'participant': participant.id,
                'title': handout_contents[i]['title'],
                'content': handout_contents[i]['content'],
                'is_secret': True,
                'handout_number': i + 1,
                'assigned_player_slot': i + 1
            }
            
            response = self.client.post(
                reverse('handout-list'),
                handout_data,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['handout_number'], i + 1)
            handouts.append(response.data)
        
        # ===== STEP 5: 各プレイヤーが自分のHOを確認 =====
        for i, player in enumerate(self.players):
            self.client.force_authenticate(user=player)
            
            # ハンドアウト一覧を取得
            response = self.client.get(reverse('handout-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # response.dataの形式を確認
            if isinstance(response.data, dict) and 'results' in response.data:
                handout_list = response.data['results']
            else:
                handout_list = response.data
            
            # 自分のHOのみが見えることを確認
            my_handouts = [
                h for h in handout_list
                if h['session'] == session.id and h['is_secret']
            ]
            
            self.assertEqual(len(my_handouts), 1)
            self.assertEqual(my_handouts[0]['handout_number'], i + 1)
            self.assertEqual(my_handouts[0]['title'], handout_contents[i]['title'])
            self.assertEqual(my_handouts[0]['content'], handout_contents[i]['content'])
            
            # 自分のキャラクターが紐付いていることを確認
            participant = SessionParticipant.objects.get(
                session=session,
                user=player
            )
            self.assertEqual(participant.character_sheet.id, characters[i].id)
            self.assertEqual(participant.player_slot, i + 1)
        
        # ===== STEP 6: セッション詳細の確認 =====
        self.client.force_authenticate(user=self.gm)
        
        response = self.client.get(
            reverse('session-detail', kwargs={'pk': session.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4人の参加者が正しく登録されているか確認
        participants = response.data['participants_detail']
        self.assertEqual(len(participants), 4)  # 4プレイヤーのみ（GMは別管理）
        
        # プレイヤーの情報を確認
        player_participants = [p for p in participants if p['role'] == 'player']
        self.assertEqual(len(player_participants), 4)
        
        for i, participant in enumerate(sorted(player_participants, key=lambda x: x['player_slot'])):
            self.assertEqual(participant['player_slot'], i + 1)
            self.assertIsNotNone(participant['character_sheet'])
            self.assertEqual(participant['character_sheet'], characters[i].id)
            self.assertIsNotNone(participant['character_sheet_detail'])
            self.assertEqual(participant['character_sheet_detail']['name'], characters[i].name)
            self.assertEqual(participant['character_sheet_detail']['occupation'], characters[i].occupation)
        
        # ===== STEP 7: 統計情報の確認 =====
        # GMの視点から全体を確認
        self.assertEqual(HandoutInfo.objects.filter(session=session).count(), 4)
        self.assertEqual(SessionParticipant.objects.filter(session=session, role='player').count(), 4)
        
        # 各ハンドアウトが正しいプレイヤー枠に割り当てられているか
        for i in range(4):
            handout = HandoutInfo.objects.get(session=session, handout_number=i+1)
            self.assertEqual(handout.assigned_player_slot, i+1)
            participant = handout.participant
            self.assertEqual(participant.player_slot, i+1)
            self.assertEqual(participant.character_sheet.occupation, occupations[i])
    
    def test_player_cannot_see_other_handouts(self):
        """プレイヤーは他のプレイヤーのHOを見ることができない"""
        # 簡易セットアップ
        self.client.force_authenticate(user=self.gm)
        
        # セッション作成
        session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            group=self.group
        )
        
        # 2人のプレイヤーを割り当て
        for i in range(2):
            character = CharacterSheet.objects.create(
                user=self.players[i],
                name=f'キャラ{i+1}',
                age=25,
                occupation='探偵',
                edition='6th',
                str_value=10, con_value=10, pow_value=10,
                dex_value=10, app_value=10, siz_value=10,
                int_value=10, edu_value=10,
                hit_points_max=10, hit_points_current=10,
                magic_points_max=10, magic_points_current=10,
                sanity_max=50, sanity_current=50, sanity_starting=50
            )
            
            SessionParticipant.objects.create(
                session=session,
                user=self.players[i],
                role='player',
                player_slot=i+1,
                character_sheet=character
            )
        
        # 各プレイヤー用のHO作成
        for i in range(2):
            participant = SessionParticipant.objects.get(
                session=session,
                player_slot=i+1
            )
            
            HandoutInfo.objects.create(
                session=session,
                participant=participant,
                title=f'HO{i+1}: 秘密情報',
                content=f'プレイヤー{i+1}だけの情報',
                is_secret=True,
                handout_number=i+1,
                assigned_player_slot=i+1
            )
        
        # プレイヤー1として確認
        self.client.force_authenticate(user=self.players[0])
        response = self.client.get(reverse('handout-list'))
        
        if isinstance(response.data, dict) and 'results' in response.data:
            handout_list = response.data['results']
        else:
            handout_list = response.data
        
        session_handouts = [h for h in handout_list if h['session'] == session.id]
        self.assertEqual(len(session_handouts), 1)
        self.assertEqual(session_handouts[0]['handout_number'], 1)
        
        # プレイヤー2として確認
        self.client.force_authenticate(user=self.players[1])
        response = self.client.get(reverse('handout-list'))
        
        if isinstance(response.data, dict) and 'results' in response.data:
            handout_list = response.data['results']
        else:
            handout_list = response.data
        
        session_handouts = [h for h in handout_list if h['session'] == session.id]
        self.assertEqual(len(session_handouts), 1)
        self.assertEqual(session_handouts[0]['handout_number'], 2)


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True, keepdb=True)
    
    failures = test_runner.run_tests([
        'schedules.test_character_session_ho_integration.CharacterSessionHOIntegrationTestCase'
    ])
    
    if failures:
        print(f"\n❌ {failures} 件のテストが失敗しました")
    else:
        print("\n✅ すべてのテストが成功しました！")