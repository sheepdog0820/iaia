"""
キャラクター作成からセッション開催までの統合テスト
完全なユーザーフローを検証
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import CharacterSheet, CharacterSkill, Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant, HandoutInfo
from scenarios.models import Scenario

User = get_user_model()


class CharacterToSessionIntegrationTestCase(TestCase):
    """キャラクター作成からセッション開催までの統合テスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.client = Client()
        self.api_client = APIClient()
        
        # GMユーザー作成
        self.gm_user = User.objects.create_user(
            username='gamemaster',
            password='gmpass123',
            email='gm@example.com',
            nickname='GM太郎'
        )
        
        # プレイヤーユーザー作成（3名）
        self.player1 = User.objects.create_user(
            username='player1',
            password='pass123',
            email='player1@example.com',
            nickname='探索者A'
        )
        
        self.player2 = User.objects.create_user(
            username='player2',
            password='pass123',
            email='player2@example.com',
            nickname='探索者B'
        )
        
        self.player3 = User.objects.create_user(
            username='player3',
            password='pass123',
            email='player3@example.com',
            nickname='探索者C'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='週末TRPG部',
            visibility='private',
            description='毎週末にTRPGセッションを楽しむグループ',
            created_by=self.gm_user
        )
        
        # グループメンバーシップ
        GroupMembership.objects.create(
            user=self.gm_user,
            group=self.group,
            role='admin'
        )
        GroupMembership.objects.create(
            user=self.player1,
            group=self.group,
            role='member'
        )
        GroupMembership.objects.create(
            user=self.player2,
            group=self.group,
            role='member'
        )
        GroupMembership.objects.create(
            user=self.player3,
            group=self.group,
            role='member'
        )
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='悪霊の家',
            game_system='coc',
            summary='廃屋に潜む恐怖を探る探索シナリオ',
            recommended_players='3-4人',
            estimated_duration='medium',
            difficulty='beginner',
            created_by=self.gm_user
        )
    
    def test_complete_flow_from_character_creation_to_session(self):
        """キャラクター作成からセッション開催までの完全なフロー"""
        
        # === Step 1: プレイヤー1がキャラクターを作成 ===
        self.client.login(username='player1', password='pass123')
        
        character_data = {
            'name': '田中太郎',
            'player_name': '探索者A',
            'age': 28,
            'gender': '男性',
            'occupation': '私立探偵',
            'birthplace': '東京',
            'residence': '横浜',
            'str_value': 13,
            'con_value': 14,
            'pow_value': 16,
            'dex_value': 12,
            'app_value': 11,
            'siz_value': 15,
            'int_value': 14,
            'edu_value': 16,
            'notes': '元警察官の探偵',
            # 最大値
            'hit_points_max': 15,
            'magic_points_max': 16,
            'sanity_starting': 80,
            # 現在値（セッション開始時点）
            'hit_points_current': 15,
            'magic_points_current': 16,
            'sanity_current': 80,
        }
        
        response = self.client.post(reverse('character_create_6th'), character_data)
        self.assertEqual(response.status_code, 302)
        
        # キャラクターが作成されたことを確認
        char1 = CharacterSheet.objects.get(name='田中太郎')
        self.assertEqual(char1.user, self.player1)
        self.assertEqual(char1.hit_points_current, 15)
        self.assertEqual(char1.sanity_current, 80)
        
        # === Step 2: プレイヤー2がキャラクターを作成 ===
        self.client.logout()
        self.client.login(username='player2', password='pass123')
        
        character_data2 = {
            'name': '山田花子',
            'player_name': '探索者B',
            'age': 25,
            'gender': '女性',
            'occupation': '医師',
            'birthplace': '大阪',
            'residence': '東京',
            'str_value': 10,
            'con_value': 12,
            'pow_value': 14,
            'dex_value': 15,
            'app_value': 13,
            'siz_value': 11,
            'int_value': 16,
            'edu_value': 18,
            'notes': '若手の救急医',
            # 最大値
            'hit_points_max': 12,
            'magic_points_max': 14,
            'sanity_starting': 70,
            # 現在値
            'hit_points_current': 12,
            'magic_points_current': 14,
            'sanity_current': 70,
        }
        
        response = self.client.post(reverse('character_create_6th'), character_data2)
        self.assertEqual(response.status_code, 302)
        
        char2 = CharacterSheet.objects.get(name='山田花子')
        self.assertEqual(char2.user, self.player2)
        
        # === Step 3: プレイヤー3がキャラクターを作成（負傷状態） ===
        self.client.logout()
        self.client.login(username='player3', password='pass123')
        
        character_data3 = {
            'name': '佐藤次郎',
            'player_name': '探索者C',
            'age': 35,
            'gender': '男性',
            'occupation': 'ジャーナリスト',
            'birthplace': '福岡',
            'residence': '東京',
            'str_value': 12,
            'con_value': 13,
            'pow_value': 15,
            'dex_value': 14,
            'app_value': 12,
            'siz_value': 14,
            'int_value': 15,
            'edu_value': 17,
            'notes': 'オカルト専門のフリーライター',
            # 最大値
            'hit_points_max': 14,
            'magic_points_max': 15,
            'sanity_starting': 75,
            # 現在値（既に負傷・精神的ダメージあり）
            'hit_points_current': 8,  # 負傷状態
            'magic_points_current': 10,  # MP消費済み
            'sanity_current': 65,  # SAN値減少済み
        }
        
        response = self.client.post(reverse('character_create_6th'), character_data3)
        self.assertEqual(response.status_code, 302)
        
        char3 = CharacterSheet.objects.get(name='佐藤次郎')
        self.assertEqual(char3.hit_points_current, 8)  # 負傷状態が保存される
        self.assertEqual(char3.sanity_current, 65)  # SAN値減少が保存される
        
        # === Step 4: GMがセッションを作成 ===
        self.api_client.force_authenticate(user=self.gm_user)
        
        session_date = timezone.now() + timedelta(days=7)
        session_data = {
            'title': '悪霊の家 - 恐怖の一夜',
            'description': '廃屋に一晩泊まることになった探索者たち。果たして朝まで生き残れるか？',
            'date': session_date.isoformat(),
            'location': 'オンライン（Discord）',
            'status': 'planned',
            'visibility': 'group',
            'group': self.group.id
        }
        
        response = self.api_client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        session = TRPGSession.objects.get(title='悪霊の家 - 恐怖の一夜')
        self.assertEqual(session.gm, self.gm_user)
        self.assertEqual(session.group, self.group)
        
        # === Step 5: プレイヤーがセッションに参加登録 ===
        # プレイヤー1が参加
        participant1 = SessionParticipant.objects.create(
            session=session,
            user=self.player1,
            role='player',
            character_name=char1.name,
            character_sheet=char1
        )
        
        # プレイヤー2が参加
        participant2 = SessionParticipant.objects.create(
            session=session,
            user=self.player2,
            role='player',
            character_name=char2.name,
            character_sheet=char2
        )
        
        # プレイヤー3が参加（負傷状態で）
        participant3 = SessionParticipant.objects.create(
            session=session,
            user=self.player3,
            role='player',
            character_name=char3.name,
            character_sheet=char3
        )
        
        # 参加状況の確認
        participants = SessionParticipant.objects.filter(session=session)
        self.assertEqual(participants.count(), 3)
        
        # キャラクターシートとの連携確認
        p1 = participants.get(user=self.player1)
        self.assertEqual(p1.character_sheet, char1)
        self.assertEqual(p1.character_name, '田中太郎')
        
        p3 = participants.get(user=self.player3)
        self.assertEqual(p3.character_sheet, char3)
        # 負傷状態のキャラクターも参加可能
        self.assertEqual(p3.character_sheet.hit_points_current, 8)
        
        # === Step 6: GMがハンドアウトを配布 ===
        # プレイヤー1へのハンドアウト
        handout1 = HandoutInfo.objects.create(
            session=session,
            participant=participant1,
            title='HO1: 探偵の過去',
            content='あなたはこの廃屋で起きた事件を以前から調査していた...',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1
        )
        
        # プレイヤー2へのハンドアウト
        handout2 = HandoutInfo.objects.create(
            session=session,
            participant=participant2,
            title='HO2: 医師の使命',
            content='あなたは最近、奇妙な症状の患者を診察した...',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2
        )
        
        # 全体公開ハンドアウト
        handout_public = HandoutInfo.objects.create(
            session=session,
            participant=participant1,  # 代表で設定
            title='廃屋の歴史',
            content='この屋敷は50年前に一家心中があった場所として知られている...',
            is_secret=False
        )
        
        # ハンドアウト配布の確認
        handouts = HandoutInfo.objects.filter(session=session)
        self.assertEqual(handouts.count(), 3)
        secret_handouts = handouts.filter(is_secret=True)
        self.assertEqual(secret_handouts.count(), 2)
        
        # === Step 7: セッション情報の総合確認 ===
        # データベースから直接確認
        session.refresh_from_db()
        self.assertEqual(session.title, '悪霊の家 - 恐怖の一夜')
        self.assertEqual(session.participants.count(), 3)
        
        # キャラクターの現在状態確認
        char3.refresh_from_db()
        self.assertEqual(char3.hit_points_current, 8)
        self.assertEqual(char3.sanity_current, 65)
        
        # === Step 8: セッション開始（ステータス変更） ===
        session.status = 'ongoing'
        session.save()
        
        session.refresh_from_db()
        self.assertEqual(session.status, 'ongoing')
        
        # === Step 9: セッション中のキャラクターステータス更新 ===
        # プレイヤー1がダメージを受ける
        self.api_client.force_authenticate(user=self.player1)
        char1.hit_points_current = 10  # 5ダメージ
        char1.sanity_current = 75  # 5SAN減少
        char1.save()
        
        # プレイヤー3が回復
        self.api_client.force_authenticate(user=self.player3)
        char3.hit_points_current = 12  # 4回復
        char3.magic_points_current = 5  # MP消費
        char3.save()
        
        # === Step 10: セッション終了 ===
        session.status = 'completed'
        session.duration_minutes = 240  # 4時間のセッション
        session.save()
        
        # 最終状態の確認
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.duration_minutes, 240)
        
        # キャラクターの最終状態
        char1.refresh_from_db()
        self.assertEqual(char1.hit_points_current, 10)  # ダメージが残っている
        self.assertEqual(char1.sanity_current, 75)  # SAN減少が残っている
        
        char3.refresh_from_db()
        self.assertEqual(char3.hit_points_current, 12)  # 回復した
        self.assertEqual(char3.magic_points_current, 5)  # MP消費
        
        # セッション参加履歴の確認
        self.assertTrue(
            SessionParticipant.objects.filter(
                session=session,
                user=self.player1,
                character_sheet=char1
            ).exists()
        )
    
    def test_character_death_during_session(self):
        """セッション中のキャラクター死亡処理"""
        # プレイヤーがキャラクター作成
        self.client.login(username='player1', password='pass123')
        
        character_data = {
            'name': '運命の探索者',
            'player_name': '探索者A',
            'age': 30,
            'gender': '男性',
            'occupation': '考古学者',
            'birthplace': '京都',
            'residence': '東京',
            'str_value': 11,
            'con_value': 10,
            'pow_value': 13,
            'dex_value': 14,
            'app_value': 12,
            'siz_value': 12,
            'int_value': 16,
            'edu_value': 18,
            'notes': '古代遺跡の専門家',
            'hit_points_max': 11,
            'magic_points_max': 13,
            'sanity_starting': 65,
            'hit_points_current': 11,
            'magic_points_current': 13,
            'sanity_current': 65,
        }
        
        response = self.client.post(reverse('character_create_6th'), character_data)
        self.assertEqual(response.status_code, 302)
        
        character = CharacterSheet.objects.get(name='運命の探索者')
        
        # GMがセッション作成
        self.api_client.force_authenticate(user=self.gm_user)
        session_data = {
            'title': '死の迷宮',
            'description': '古代遺跡での危険な探索',
            'date': (timezone.now() + timedelta(days=1)).isoformat(),
            'location': 'オンライン',
            'status': 'planned',
            'visibility': 'group',
            'group': self.group.id
        }
        
        response = self.api_client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(title='死の迷宮')
        
        # プレイヤーが参加
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.player1,
            role='player',
            character_name=character.name,
            character_sheet=character
        )
        
        # セッション中にキャラクターが死亡
        character.hit_points_current = 0  # HP0で死亡
        character.status = 'dead'
        character.save()
        
        # 死亡状態の確認
        character.refresh_from_db()
        self.assertEqual(character.hit_points_current, 0)
        self.assertEqual(character.status, 'dead')
        
        # 死亡キャラクターでも履歴は残る
        participant.refresh_from_db()
        self.assertEqual(participant.character_sheet.status, 'dead')
    
    def test_insane_character_participation(self):
        """発狂状態のキャラクターのセッション参加"""
        # プレイヤーがキャラクター作成（発狂状態）
        self.client.login(username='player2', password='pass123')
        
        character_data = {
            'name': '狂気の研究者',
            'player_name': '探索者B',
            'age': 45,
            'gender': '女性',
            'occupation': '大学教授',
            'birthplace': '仙台',
            'residence': '東京',
            'str_value': 9,
            'con_value': 11,
            'pow_value': 16,
            'dex_value': 10,
            'app_value': 11,
            'siz_value': 10,
            'int_value': 18,
            'edu_value': 20,
            'notes': '禁断の知識を求めすぎた',
            'hit_points_max': 11,
            'magic_points_max': 16,
            'sanity_starting': 80,
            'hit_points_current': 11,
            'magic_points_current': 16,
            'sanity_current': 0,  # 完全発狂
        }
        
        response = self.client.post(reverse('character_create_6th'), character_data)
        self.assertEqual(response.status_code, 302)
        
        character = CharacterSheet.objects.get(name='狂気の研究者')
        character.status = 'insane'
        character.save()
        
        # セッション作成と参加（発狂キャラクターでも参加可能）
        self.api_client.force_authenticate(user=self.gm_user)
        session_data = {
            'title': '狂気の宴',
            'description': '正気を失った者たちの集い',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': '精神病院',
            'status': 'planned',
            'visibility': 'group',
            'group': self.group.id
        }
        
        response = self.api_client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = TRPGSession.objects.get(title='狂気の宴')
        
        # 発狂キャラクターでも参加可能
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.player2,
            role='player',
            character_name=character.name,
            character_sheet=character
        )
        self.assertEqual(participant.character_sheet.sanity_current, 0)
        self.assertEqual(participant.character_sheet.status, 'insane')