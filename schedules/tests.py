from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import TRPGSession, SessionParticipant, HandoutInfo
from accounts.models import Group

User = get_user_model()


class BasicScheduleTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='gmuser',
            email='gm@example.com',
            password='pass123',
            nickname='GM User'
        )
        self.user2 = User.objects.create_user(
            username='playeruser',
            email='player@example.com',
            password='pass123',
            nickname='Player User'
        )
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user1
        )

    def test_trpg_session_creation(self):
        """TRPGセッション作成のテスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        self.assertEqual(session.title, 'Test Session')
        self.assertEqual(session.gm, self.user1)
        self.assertEqual(session.group, self.group)
        self.assertEqual(session.status, 'planned')

    def test_session_str_representation(self):
        """セッション文字列表現のテスト"""
        test_date = timezone.now() + timedelta(days=1)
        session = TRPGSession.objects.create(
            title='Test Session',
            date=test_date,
            gm=self.user1,
            group=self.group
        )
        expected_str = f'Test Session ({test_date.strftime("%Y-%m-%d")})'
        self.assertEqual(str(session), expected_str)

    def test_session_participant_creation(self):
        """セッション参加者作成のテスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player'
        )
        
        self.assertEqual(participant.session, session)
        self.assertEqual(participant.user, self.user2)
        self.assertEqual(participant.role, 'player')

    def test_session_coc_edition_default(self):
        """セッションのCoC版デフォルト値のテスト"""
        session = TRPGSession.objects.create(
            title='Edition Default Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        self.assertEqual(session.coc_edition, '6th')

    def test_session_coc_edition_can_set(self):
        """セッションのCoC版を指定できることのテスト"""
        session = TRPGSession.objects.create(
            title='Edition 7th Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group,
            coc_edition='7th',
        )
        self.assertEqual(session.coc_edition, '7th')

    def test_handout_creation(self):
        """ハンドアウト作成のテスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player'
        )
        
        handout = HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title='Test Handout',
            content='Handout content'
        )
        
        self.assertEqual(handout.title, 'Test Handout')
        self.assertEqual(handout.participant, participant)
        self.assertTrue(handout.is_secret)  # デフォルトはTrue

    def test_secret_handout(self):
        """秘匿ハンドアウトのテスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player'
        )
        
        secret_handout = HandoutInfo.objects.create(
            session=session,
            participant=participant,
            title='Secret Handout',
            content='Secret content',
            is_secret=True
        )
        
        self.assertTrue(secret_handout.is_secret)
