import uuid
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from .models import TRPGSession, SessionParticipant, HandoutInfo, SessionInvitation
from accounts.models import Group as CustomGroup
from scenarios.models import Scenario

User = get_user_model()


class ScheduleModelsTestCase(TestCase):
    def setUp(self):
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
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        self.group.members.add(self.user1, self.user2)

    def test_trpg_session_creation(self):
        """TRPGセッション作成テスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            description='Test Description',
            date=timezone.now() + timedelta(days=1),
            location='Online',
            gm=self.user1,
            group=self.group,
            duration_minutes=180
        )
        
        self.assertEqual(session.title, 'Test Session')
        self.assertEqual(session.gm, self.user1)
        self.assertEqual(session.group, self.group)
        self.assertEqual(session.duration_minutes, 180)
        self.assertEqual(session.status, 'planned')  # デフォルト値

    def test_session_participant_creation(self):
        """セッション参加者作成テスト"""
        session = TRPGSession.objects.create(
            title='Test Session',
            date=timezone.now() + timedelta(days=1),
            gm=self.user1,
            group=self.group
        )
        
        participant = SessionParticipant.objects.create(
            session=session,
            user=self.user2,
            role='player',
            character_name='Test Character'
        )
        
        self.assertEqual(participant.session, session)
        self.assertEqual(participant.user, self.user2)
        self.assertEqual(participant.role, 'player')
        self.assertEqual(participant.character_name, 'Test Character')

    def test_handout_creation(self):
        """ハンドアウト作成テスト"""
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
            content='Secret information...',
            is_secret=True
        )
        
        self.assertEqual(handout.title, 'Test Handout')
        self.assertEqual(handout.participant, participant)
        self.assertTrue(handout.is_secret)


class ScheduleAPITestCase(APITestCase):
    def setUp(self):
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
        self.group = CustomGroup.objects.create(
            name='Test Group',
            created_by=self.user1
        )
        self.group.members.add(self.user1, self.user2)
        
        # テスト用セッション作成
        self.session = TRPGSession.objects.create(
            title='Test Session',
            description='Test Description',
            date=timezone.now() + timedelta(days=1),
            location='Online',
            gm=self.user1,
            group=self.group,
            duration_minutes=180
        )
        self.scenario = Scenario.objects.create(
            title='Linked Scenario',
            game_system='coc',
            created_by=self.user1
        )

    def test_sessions_list_unauthenticated(self):
        """未認証セッション一覧アクセステスト"""
        response = self.client.get('/api/schedules/sessions/view/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sessions_list_authenticated(self):
        """認証済みセッション一覧アクセステスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)
        
        session_data = data['results'][0]
        self.assertEqual(session_data['title'], 'Test Session')
        self.assertEqual(session_data['gm_name'], 'GM User')

    def test_sessions_list_pagination(self):
        """セッション一覧ページネーションテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # パラメータ付きリクエスト
        response = self.client.get('/api/schedules/sessions/view/?limit=5&offset=0', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['limit'], 5)
        self.assertEqual(data['offset'], 0)
        self.assertIn('has_next', data)
        self.assertIn('has_previous', data)

    def test_session_viewset_list(self):
        """セッションViewSetリストテスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_viewset_detail(self):
        """セッションViewSet詳細テスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['title'], 'Test Session')
        self.assertEqual(data['gm'], self.user1.id)

    def test_session_creation_via_api(self):
        """API経由セッション作成テスト"""
        self.client.force_authenticate(user=self.user1)
        
        session_data = {
            'title': 'New Session',
            'description': 'New Description',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 240
        }
        
        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        created_session = TRPGSession.objects.get(title='New Session')
        self.assertEqual(created_session.gm, self.user1)
        self.assertEqual(created_session.duration_minutes, 240)

    def test_session_creation_with_scenario(self):
        """シナリオ連携付きセッション作成テスト"""
        self.client.force_authenticate(user=self.user1)

        session_data = {
            'title': 'Scenario Session',
            'description': 'Scenario Linked',
            'date': (timezone.now() + timedelta(days=3)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 180,
            'scenario': self.scenario.id
        }

        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_session = TRPGSession.objects.get(title='Scenario Session')
        self.assertEqual(created_session.scenario, self.scenario)
        response_data = response.json()
        self.assertEqual(response_data['scenario'], self.scenario.id)
        self.assertEqual(response_data['scenario_detail']['title'], self.scenario.title)

    def test_session_join_functionality(self):
        """セッション参加機能テスト"""
        self.client.force_authenticate(user=self.user2)
        
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 参加者が作成されたことを確認
        participant = SessionParticipant.objects.get(
            session=self.session,
            user=self.user2
        )
        self.assertEqual(participant.role, 'player')

    def test_session_join_duplicate(self):
        """重複セッション参加テスト"""
        self.client.force_authenticate(user=self.user2)
        
        # 最初の参加
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 重複参加試行
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_join_group_non_member_forbidden(self):
        """グループ外メンバーの参加拒否テスト"""
        outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass123',
            nickname='Outsider'
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_join_private_forbidden(self):
        """プライベートセッション参加拒否テスト"""
        self.session.visibility = 'private'
        self.session.save(update_fields=['visibility'])
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f'/api/schedules/sessions/{self.session.id}/join/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_participant_create_role_gm_forbidden(self):
        """一般ユーザーが参加者作成でGM権限を指定できない"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            '/api/schedules/participants/',
            {'session': self.session.id, 'role': 'gm'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_update_role_gm_forbidden(self):
        """一般ユーザーが自分の参加情報をGMに昇格できない"""
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )

        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(
            f'/api/schedules/participants/{participant.id}/',
            {'role': 'gm'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_delete_other_forbidden(self):
        """GM以外が他人の参加情報を削除できない"""
        user3 = User.objects.create_user(
            username='member3',
            email='member3@example.com',
            password='pass123',
            nickname='Member3'
        )
        self.group.members.add(user3)

        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )

        self.client.force_authenticate(user=user3)
        response = self.client.delete(f'/api/schedules/participants/{participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_gm_can_delete_other_participant(self):
        """GMは参加者を除名できる"""
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/schedules/participants/{participant.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_player_slot_conflict_on_update(self):
        """プレイヤー枠の重複は更新時も拒否される"""
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user1,
            role='gm',
            player_slot=1
        )
        p2 = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
            player_slot=2
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f'/api/schedules/participants/{p2.id}/',
            {'player_slot': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calendar_api(self):
        """カレンダーAPIテスト"""
        self.client.force_authenticate(user=self.user1)
        
        start_date = timezone.now().date()
        end_date = (timezone.now() + timedelta(days=30)).date()
        
        response = self.client.get(
            f'/api/schedules/calendar/?start={start_date}&end={end_date}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calendar_api_missing_params(self):
        """カレンダーAPI必須パラメータ不足テスト"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/schedules/calendar/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)

    def test_participants_viewset(self):
        """参加者ViewSetテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 参加者作成
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )
        
        response = self.client.get('/api/schedules/participants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_handouts_viewset(self):
        """ハンドアウトViewSetテスト"""
        self.client.force_authenticate(user=self.user1)
        
        # 参加者とハンドアウト作成
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )
        
        HandoutInfo.objects.create(
            session=self.session,
            participant=participant,
            title='Test Handout',
            content='Secret info'
        )
        
        response = self.client.get('/api/schedules/handouts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_invitation_accept_creates_participant(self):
        """セッション招待の受諾で参加者が作成される"""
        self.client.force_authenticate(user=self.user1)
        invite_res = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/invite/',
            {'user_id': self.user2.id},
            format='json'
        )
        self.assertEqual(invite_res.status_code, status.HTTP_200_OK)
        invitation_id = invite_res.data['invitation_id']

        self.client.force_authenticate(user=self.user2)
        accept_res = self.client.post(f'/api/schedules/session-invitations/{invitation_id}/accept/')
        self.assertEqual(accept_res.status_code, status.HTTP_200_OK)

        self.assertTrue(SessionParticipant.objects.filter(session=self.session, user=self.user2).exists())

        inv = SessionInvitation.objects.get(id=invitation_id)
        self.assertEqual(inv.status, 'accepted')
        self.assertIsNotNone(inv.responded_at)

    def test_session_invitation_decline_does_not_create_participant(self):
        """セッション招待の辞退では参加者が作成されない"""
        self.client.force_authenticate(user=self.user1)
        invite_res = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/invite/',
            {'user_id': self.user2.id},
            format='json'
        )
        invitation_id = invite_res.data['invitation_id']

        self.client.force_authenticate(user=self.user2)
        decline_res = self.client.post(f'/api/schedules/session-invitations/{invitation_id}/decline/')
        self.assertEqual(decline_res.status_code, status.HTTP_200_OK)

        self.assertFalse(SessionParticipant.objects.filter(session=self.session, user=self.user2).exists())

        inv = SessionInvitation.objects.get(id=invitation_id)
        self.assertEqual(inv.status, 'declined')
        self.assertIsNotNone(inv.responded_at)

    def test_session_invitation_accept_expired_rejected(self):
        """期限切れの招待は受諾できない"""
        invitation = SessionInvitation.objects.create(
            session=self.session,
            inviter=self.user1,
            invitee=self.user2,
            status='pending',
        )
        invitation.created_at = timezone.now() - timedelta(days=invitation.INVITATION_EXPIRY_DAYS + 1)
        invitation.save(update_fields=['created_at'])

        self.client.force_authenticate(user=self.user2)
        res = self.client.post(f'/api/schedules/session-invitations/{invitation.id}/accept/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'expired')

    def test_session_invitation_only_invitee_can_accept(self):
        """招待は被招待者のみ受諾できる"""
        self.client.force_authenticate(user=self.user1)
        invite_res = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/invite/',
            {'user_id': self.user2.id},
            format='json'
        )
        invitation_id = invite_res.data['invitation_id']

        user3 = User.objects.create_user(
            username='member3',
            email='member3@example.com',
            password='pass123',
            nickname='Member3'
        )
        self.client.force_authenticate(user=user3)
        res = self.client.post(f'/api/schedules/session-invitations/{invitation_id}/accept/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_session_invitation_accept_allowed(self):
        """プライベートセッションは招待受諾で参加できる"""
        self.session.visibility = 'private'
        self.session.save(update_fields=['visibility'])

        self.client.force_authenticate(user=self.user1)
        invite_res = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/invite/',
            {'user_id': self.user2.id},
            format='json'
        )
        invitation_id = invite_res.data['invitation_id']

        self.client.force_authenticate(user=self.user2)
        accept_res = self.client.post(f'/api/schedules/session-invitations/{invitation_id}/accept/')
        self.assertEqual(accept_res.status_code, status.HTTP_200_OK)
        self.assertTrue(SessionParticipant.objects.filter(session=self.session, user=self.user2).exists())


class PublicSessionLinkTestCase(APITestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username='gm_share',
            email='gm_share@example.com',
            password='pass123',
            nickname='GM Share'
        )
        self.player = User.objects.create_user(
            username='player_share',
            email='player_share@example.com',
            password='pass123',
            nickname='Player Share'
        )
        self.group = CustomGroup.objects.create(
            name='Share Test Group',
            created_by=self.gm
        )
        self.group.description = 'PUBLIC_VIEW_SHOULD_NOT_SHOW_THIS'
        self.group.save(update_fields=['description'])
        self.group.members.add(self.gm, self.player)

        self.session = TRPGSession.objects.create(
            title='Share Session',
            description='Share Description',
            date=timezone.now() + timedelta(days=1),
            location='Online',
            gm=self.gm,
            group=self.group,
            visibility='private',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role='player',
        )

    def test_public_session_detail_accessible_without_login(self):
        url = reverse('public_session_detail', kwargs={'share_token': self.session.share_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.session.title)
        self.assertContains(response, self.group.name)
        self.assertNotContains(response, self.group.description)
        self.assertContains(response, self.player.nickname)
        self.assertNotContains(response, 'alt="プロフィール"')

    def test_public_session_detail_invalid_token_404(self):
        url = reverse('public_session_detail', kwargs={'share_token': uuid.uuid4()})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_detail_requires_login(self):
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_detail_has_copy_link_button(self):
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, f"/s/{self.session.share_token}/")
