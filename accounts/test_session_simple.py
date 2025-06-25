"""
簡単なセッション連携テスト
基本的なセッションとキャラクターの連携を確認
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from accounts.models import CharacterSheet, Group, GroupMembership
from schedules.models import TRPGSession, SessionParticipant
from scenarios.models import Scenario

User = get_user_model()


class SimpleSessionCharacterTest(TestCase):
    """シンプルなセッション・キャラクター連携テスト"""
    
    def setUp(self):
        """基本的なテストデータの作成"""
        # ユーザー作成
        self.gm = User.objects.create_user(
            username='gm',
            password='gmpass123',
            email='gm@test.com'
        )
        
        self.player = User.objects.create_user(
            username='player',
            password='playerpass123',
            email='player@test.com'
        )
        
        # グループ作成
        self.group = Group.objects.create(
            name='テストグループ',
            created_by=self.gm,
            visibility='private'
        )
        
        # グループメンバーシップ追加
        GroupMembership.objects.create(
            user=self.gm,
            group=self.group,
            role='admin'
        )
        
        GroupMembership.objects.create(
            user=self.player,
            group=self.group,
            role='member'
        )
        
        # キャラクター作成
        self.character = CharacterSheet.objects.create(
            user=self.player,
            edition='6th',
            name='テスト探索者',
            player_name=self.player.username,
            age=25,
            occupation='探偵',
            str_value=12,
            con_value=14,
            pow_value=16,
            dex_value=13,
            app_value=11,
            siz_value=15,
            int_value=14,
            edu_value=15,
            hit_points_current=15,
            magic_points_current=16,
            sanity_current=80
        )
        
        # シナリオ作成
        self.scenario = Scenario.objects.create(
            title='テストシナリオ',
            game_system='coc',
            created_by=self.gm
        )
    
    def test_create_session_with_character(self):
        """セッション作成とキャラクター参加の基本テスト"""
        # セッション作成
        session = TRPGSession.objects.create(
            title='テストセッション',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        self.assertIsNotNone(session.id)
        self.assertEqual(session.gm, self.gm)
        self.assertEqual(session.group, self.group)
        
        # キャラクター参加
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.player,
            character_name=self.character.name
        )
        
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.user, self.player)
        self.assertEqual(participant.character_name, 'テスト探索者')
        
        # セッションの参加者数確認
        participants = SessionParticipant.objects.filter(session=session)
        self.assertEqual(participants.count(), 1)
        
    def test_character_status_update(self):
        """キャラクターステータス更新テスト"""
        # キャラクターのHP更新
        original_hp = self.character.hit_points_current
        self.character.hit_points_current = 10
        self.character.save()
        
        # 更新確認
        self.character.refresh_from_db()
        self.assertEqual(self.character.hit_points_current, 10)
        self.assertNotEqual(self.character.hit_points_current, original_hp)
        
    def test_session_lifecycle(self):
        """セッションのライフサイクルテスト"""
        # セッション作成
        session = TRPGSession.objects.create(
            title='ライフサイクルテスト',
            date=timezone.now(),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # ステータス変更: planned -> ongoing
        session.status = 'ongoing'
        session.save()
        
        session.refresh_from_db()
        self.assertEqual(session.status, 'ongoing')
        
        # ステータス変更: ongoing -> completed
        session.status = 'completed'
        session.duration_minutes = 240  # 4時間
        session.save()
        
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.duration_minutes, 240)
        
    def test_multiple_characters_in_session(self):
        """複数キャラクターのセッション参加テスト"""
        # 追加プレイヤー作成
        player2 = User.objects.create_user(
            username='player2',
            password='pass123',
            email='player2@test.com'
        )
        
        # グループに追加
        GroupMembership.objects.create(
            user=player2,
            group=self.group,
            role='member'
        )
        
        # キャラクター2作成
        character2 = CharacterSheet.objects.create(
            user=player2,
            edition='6th',
            name='テスト探索者2',
            player_name=player2.username,
            age=30,
            occupation='医師',
            str_value=10,
            con_value=12,
            pow_value=14,
            dex_value=15,
            app_value=13,
            siz_value=11,
            int_value=16,
            edu_value=18,
            hit_points_current=12,
            magic_points_current=14,
            sanity_current=70
        )
        
        # セッション作成
        session = TRPGSession.objects.create(
            title='複数参加者セッション',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            group=self.group,
            status='planned'
        )
        
        # 両方のキャラクターが参加
        SessionParticipant.objects.create(
            session=session,
            user=self.player,
            character_name=self.character.name
        )
        
        SessionParticipant.objects.create(
            session=session,
            user=player2,
            character_name=character2.name
        )
        
        # 参加者数確認
        participants = SessionParticipant.objects.filter(session=session)
        self.assertEqual(participants.count(), 2)
        
        # 参加者のキャラクター名確認
        character_names = [p.character_name for p in participants]
        self.assertIn('テスト探索者', character_names)
        self.assertIn('テスト探索者2', character_names)