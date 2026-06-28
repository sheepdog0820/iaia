import uuid
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from .models import TRPGSession, SessionParticipant, HandoutInfo, SessionInvitation
from accounts.models import CharacterSheet, Group as CustomGroup
from scenarios.models import Scenario, ScenarioHandout, ScenarioHandoutRecommendedSkill

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
        self.assertEqual(session.effective_duration_minutes, 180)
        session.actual_duration_minutes = 210
        self.assertEqual(session.effective_duration_minutes, 210)
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

    def test_sessions_list_period_filter_defaults_to_future(self):
        self.client.force_authenticate(user=self.user1)
        past_session = TRPGSession.objects.create(
            title='Past Session',
            date=timezone.now() - timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )

        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        session_ids = [session['id'] for session in data['results']]
        self.assertEqual(data['period'], 'future')
        self.assertIn(self.session.id, session_ids)
        self.assertNotIn(past_session.id, session_ids)

    def test_sessions_list_period_filter_can_show_past_and_all(self):
        self.client.force_authenticate(user=self.user1)
        past_session = TRPGSession.objects.create(
            title='Past Session',
            date=timezone.now() - timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )

        past_response = self.client.get(
            '/api/schedules/sessions/view/?period=past',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(past_response.status_code, status.HTTP_200_OK)
        past_ids = [session['id'] for session in past_response.json()['results']]
        self.assertEqual(past_ids, [past_session.id])

        all_response = self.client.get(
            '/api/schedules/sessions/view/?period=all',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        all_ids = [session['id'] for session in all_response.json()['results']]
        self.assertEqual(all_ids, [self.session.id, past_session.id])

    def test_sessions_list_includes_guest_count(self):
        """セッション一覧JSONにguest_countが含まれる"""
        self.client.force_authenticate(user=self.user1)

        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=None,
            guest_name='ゲスト参加者',
            role='player',
        )

        response = self.client.get('/api/schedules/sessions/view/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        session_data = data['results'][0]
        self.assertEqual(session_data['participant_count'], 1)
        self.assertEqual(session_data['guest_count'], 1)

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

    def test_session_viewset_list_period_filter(self):
        self.client.force_authenticate(user=self.user1)
        past_session = TRPGSession.objects.create(
            title='Past Session',
            date=timezone.now() - timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )

        default_response = self.client.get('/api/schedules/sessions/')
        self.assertEqual(default_response.status_code, status.HTTP_200_OK)
        default_payload = default_response.json()
        default_sessions = (
            default_payload.get('results', default_payload)
            if isinstance(default_payload, dict)
            else default_payload
        )
        default_ids = [session['id'] for session in default_sessions]
        self.assertIn(self.session.id, default_ids)
        self.assertNotIn(past_session.id, default_ids)

        past_response = self.client.get('/api/schedules/sessions/?period=past')
        self.assertEqual(past_response.status_code, status.HTTP_200_OK)
        past_payload = past_response.json()
        past_sessions = (
            past_payload.get('results', past_payload)
            if isinstance(past_payload, dict)
            else past_payload
        )
        past_ids = [session['id'] for session in past_sessions]
        self.assertEqual(past_ids, [past_session.id])

    def test_session_viewset_detail(self):
        """セッションViewSet詳細テスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['title'], 'Test Session')
        self.assertEqual(data['gm'], self.user1.id)

    def test_session_viewset_detail_includes_guest_count(self):
        """セッション詳細JSONにguest_countが含まれる"""
        self.client.force_authenticate(user=self.user1)

        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=None,
            guest_name='ゲスト参加者',
            role='player',
        )

        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['participant_count'], 1)
        self.assertEqual(data['guest_count'], 1)

    def test_upcoming_sessions_includes_guest_count(self):
        """次回セッションAPIにguest_countが含まれ、participant_countは従来通り"""
        self.client.force_authenticate(user=self.user1)

        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=None,
            guest_name='ゲスト参加者',
            role='player',
        )

        response = self.client.get('/api/schedules/sessions/upcoming/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        session_data = next((s for s in data if s.get('id') == self.session.id), data[0])
        self.assertEqual(session_data['participant_count'], 1)
        self.assertEqual(session_data['guest_count'], 1)

    def test_upcoming_sessions_include_participating_sessions_after_seven_days(self):
        self.client.force_authenticate(user=self.user2)
        far_gm_session = TRPGSession.objects.create(
            title='Far GM Session',
            date=timezone.now() + timedelta(days=9),
            gm=self.user2,
            group=self.group,
        )
        far_session = TRPGSession.objects.create(
            title='Far Participating Session',
            date=timezone.now() + timedelta(days=8),
            gm=self.user1,
            group=self.group,
        )
        SessionParticipant.objects.create(
            session=far_session,
            user=self.user2,
            role='player',
        )

        response = self.client.get('/api/schedules/sessions/upcoming/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session_ids = [session['id'] for session in response.json()]
        self.assertIn(far_gm_session.id, session_ids)
        self.assertIn(far_session.id, session_ids)

    def test_upcoming_sessions_exclude_group_sessions_without_role(self):
        self.client.force_authenticate(user=self.user2)

        response = self.client.get('/api/schedules/sessions/upcoming/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session_ids = [session['id'] for session in response.json()]
        self.assertNotIn(self.session.id, session_ids)

    def test_my_sessions_default_future_period(self):
        """参加予定セッション一覧: period未指定はfuture扱い"""
        self.client.force_authenticate(user=self.user2)

        now = timezone.now()
        future_soon = TRPGSession.objects.create(
            title='Future Soon Session',
            date=now + timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )
        future_far = TRPGSession.objects.create(
            title='Future Far Session',
            date=now + timedelta(days=10),
            gm=self.user1,
            group=self.group,
        )
        past_recent = TRPGSession.objects.create(
            title='Past Recent Session',
            date=now - timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )
        past_old = TRPGSession.objects.create(
            title='Past Old Session',
            date=now - timedelta(days=10),
            gm=self.user1,
            group=self.group,
        )

        for session in [future_soon, future_far, past_recent, past_old]:
            SessionParticipant.objects.create(
                session=session,
                user=self.user2,
                role='player',
            )

        response = self.client.get('/api/schedules/sessions/my-sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual([s['id'] for s in data['results']], [future_soon.id, future_far.id])
        self.assertEqual(data['results'][0]['my_role'], 'player')

    def test_my_sessions_all_period_sorting_and_invalid_pagination(self):
        """参加予定セッション一覧: all(空)は未来→過去、page系は安全に解釈"""
        self.client.force_authenticate(user=self.user2)

        now = timezone.now()
        future_soon = TRPGSession.objects.create(
            title='Future Soon Session',
            date=now + timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )
        future_far = TRPGSession.objects.create(
            title='Future Far Session',
            date=now + timedelta(days=10),
            gm=self.user1,
            group=self.group,
        )
        past_recent = TRPGSession.objects.create(
            title='Past Recent Session',
            date=now - timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )
        past_old = TRPGSession.objects.create(
            title='Past Old Session',
            date=now - timedelta(days=10),
            gm=self.user1,
            group=self.group,
        )

        for session in [future_soon, future_far, past_recent, past_old]:
            SessionParticipant.objects.create(
                session=session,
                user=self.user2,
                role='player',
            )

        response = self.client.get(
            '/api/schedules/sessions/my-sessions/',
            {'period': '', 'page': 'abc', 'page_size': '9999'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 100)
        self.assertEqual(data['count'], 4)
        self.assertEqual(
            [s['id'] for s in data['results']],
            [future_soon.id, future_far.id, past_recent.id, past_old.id],
        )

    def test_my_sessions_past_period_includes_all_past_sessions(self):
        self.client.force_authenticate(user=self.user2)

        now = timezone.now()
        future_session = TRPGSession.objects.create(
            title='Future Session',
            date=now + timedelta(days=1),
            gm=self.user1,
            group=self.group,
        )
        past_recent = TRPGSession.objects.create(
            title='Past Recent Session',
            date=now - timedelta(days=1),
            gm=self.user1,
            group=self.group,
            status='completed',
        )
        past_old = TRPGSession.objects.create(
            title='Past Old Session',
            date=now - timedelta(days=120),
            gm=self.user1,
            group=self.group,
            status='completed',
        )

        for session in [future_session, past_recent, past_old]:
            SessionParticipant.objects.create(
                session=session,
                user=self.user2,
                role='player',
            )

        response = self.client.get('/api/schedules/sessions/my-sessions/?period=past')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(
            [s['id'] for s in data['results']],
            [past_recent.id, past_old.id],
        )

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

    def test_session_creation_copies_scenario_handouts(self):
        self.client.force_authenticate(user=self.user1)
        ScenarioHandout.objects.create(
            scenario=self.scenario,
            title='HO1',
            content='Secret setup',
            recommended_skills='図書館',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1,
        )
        ScenarioHandout.objects.create(
            scenario=self.scenario,
            title='探索者共通',
            content='Common setup',
            recommended_skills='目星',
            is_secret=False,
            handout_number=None,
            assigned_player_slot=None,
        )

        response = self.client.post('/api/schedules/sessions/', {
            'title': 'Scenario Handout Session',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 240,
            'scenario': self.scenario.id,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_session = TRPGSession.objects.get(title='Scenario Handout Session')
        handout = HandoutInfo.objects.get(session=created_session, handout_number=1)
        self.assertEqual(handout.title, 'HO1')
        self.assertEqual(handout.content, 'Secret setup')
        self.assertEqual(handout.recommended_skills, '図書館')
        self.assertEqual(handout.assigned_player_slot, 1)
        self.assertTrue(handout.participant.guest_name.startswith('[template] player-1'))
        common_handout = HandoutInfo.objects.get(
            session=created_session,
            handout_number__isnull=True,
            assigned_player_slot__isnull=True,
        )
        self.assertEqual(common_handout.title, '探索者共通')
        self.assertEqual(common_handout.recommended_skills, '目星')

        SessionParticipant.objects.create(
            session=created_session,
            user=self.user2,
            role='player',
        )
        self.client.force_authenticate(user=self.user2)
        context_response = self.client.get(
            f'/api/schedules/sessions/next-context/?session_id={created_session.id}'
        )
        self.assertEqual(context_response.status_code, status.HTTP_200_OK)
        self.assertIn('目星', context_response.json()['handout_recommended_skills'])

    def test_session_creation_copies_flexible_scenario_handouts(self):
        self.client.force_authenticate(user=self.user1)
        primary = ScenarioHandout.objects.create(
            scenario=self.scenario,
            code='HO1',
            name='Detective',
            title='Legacy Detective',
            content='Primary investigator',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=1,
            order=2,
        )
        extra = ScenarioHandout.objects.create(
            scenario=self.scenario,
            code='HO1-B',
            name='Assistant',
            title='Legacy Assistant',
            content='Additional role',
            is_secret=True,
            handout_number=1,
            assigned_player_slot=None,
            order=1,
        )
        ScenarioHandoutRecommendedSkill.objects.create(
            handout=primary,
            name='Law',
            level='required',
            description='Needed for records',
            order=1,
        )
        ScenarioHandoutRecommendedSkill.objects.create(
            handout=extra,
            name='Library Use',
            level='semi_recommended',
            description='Helpful for research',
            order=1,
        )

        response = self.client.post('/api/schedules/sessions/', {
            'title': 'Flexible Scenario Handout Session',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 240,
            'scenario': self.scenario.id,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_session = TRPGSession.objects.get(title='Flexible Scenario Handout Session')
        self.assertEqual(HandoutInfo.objects.filter(session=created_session, handout_number=1).count(), 2)
        copied_extra = HandoutInfo.objects.get(session=created_session, code='HO1-B')
        self.assertEqual(copied_extra.name, 'Assistant')
        self.assertEqual(copied_extra.title, 'Assistant')
        self.assertEqual(copied_extra.order, 1)
        self.assertEqual(copied_extra.recommended_skills, 'Library Use')

    def test_session_creation_accepts_actual_duration_via_api(self):
        self.client.force_authenticate(user=self.user1)

        session_data = {
            'title': 'Actual Duration Session',
            'description': 'Actual duration is recorded after play',
            'date': (timezone.now() + timedelta(days=2)).isoformat(),
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 240,
            'actual_duration_minutes': 270,
        }

        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_session = TRPGSession.objects.get(title='Actual Duration Session')
        self.assertEqual(created_session.duration_minutes, 240)
        self.assertEqual(created_session.actual_duration_minutes, 270)
        self.assertEqual(response.json()['effective_duration_minutes'], 270)

    def test_session_creation_without_date_via_api(self):
        self.client.force_authenticate(user=self.user1)

        session_data = {
            'title': 'Undated Session',
            'description': 'No date yet',
            'location': 'Online',
            'group': self.group.id,
            'duration_minutes': 0
        }

        response = self.client.post('/api/schedules/sessions/', session_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_data = response.json()
        self.assertIsNone(response_data.get('date'))

        created_session = TRPGSession.objects.get(id=response_data['id'])
        self.assertIsNone(created_session.date)
        self.assertEqual(created_session.occurrences.count(), 0)

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

    def test_non_premium_manager_cannot_change_session_scenario(self):
        other_scenario = Scenario.objects.create(
            title='Other Scenario',
            game_system='coc',
            created_by=self.user1,
        )
        self.client.force_authenticate(user=self.user1)

        response = self.client.patch(
            f'/api/schedules/sessions/{self.session.id}/',
            {'scenario': other_scenario.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.scenario)

    def test_premium_manager_can_change_session_scenario(self):
        self.user1.is_premium = True
        self.user1.save(update_fields=['is_premium'])
        other_scenario = Scenario.objects.create(
            title='Other Scenario',
            game_system='coc',
            created_by=self.user1,
        )
        self.client.force_authenticate(user=self.user1)

        response = self.client.patch(
            f'/api/schedules/sessions/{self.session.id}/',
            {'scenario': other_scenario.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertEqual(self.session.scenario, other_scenario)

    def test_manager_can_update_registered_participant_character_fields(self):
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
        )
        self.client.force_authenticate(user=self.user1)

        response = self.client.patch(
            f'/api/schedules/participants/{participant.id}/',
            {
                'player_slot': 3,
                'character_name': 'Updated Character',
                'character_sheet_url': 'https://example.com/updated-sheet',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        self.assertEqual(participant.player_slot, 3)
        self.assertEqual(participant.character_name, 'Updated Character')
        self.assertEqual(participant.character_sheet_url, 'https://example.com/updated-sheet')

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

    def test_main_gm_participant_cannot_be_deleted(self):
        participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user1,
            role='player'
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/schedules/participants/{participant.id}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SessionParticipant.objects.filter(id=participant.id).exists())

    def test_session_detail_does_not_show_remove_button_for_main_gm(self):
        main_gm_participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user1,
            role='player'
        )
        removable_participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player'
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/detail/',
            HTTP_ACCEPT='text/html',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, f'removeParticipant({main_gm_participant.id})')
        self.assertContains(response, f'removeParticipant({removable_participant.id})')

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

    def test_gm_can_create_guest_participant(self):
        """GMはゲスト参加者（ログイン不要）を作成できる"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            '/api/schedules/participants/',
            {
                'session': self.session.id,
                'guest_name': 'Guest Player',
                'player_slot': 1,
                'character_name': 'Guest Character',
                'character_sheet_url': 'https://example.com/sheet',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get('user'))
        self.assertEqual(response.data.get('guest_name'), 'Guest Player')
        self.assertEqual(response.data.get('player_slot'), 1)

        self.assertTrue(
            SessionParticipant.objects.filter(
                session=self.session,
                user__isnull=True,
                guest_name='Guest Player',
            ).exists()
        )

    def test_non_gm_cannot_create_guest_participant(self):
        """GM以外はゲスト参加者を作成できない"""
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            '/api/schedules/participants/',
            {
                'session': self.session.id,
                'guest_name': 'Guest Player',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_complete_with_guest_participant(self):
        """ゲスト参加者がいてもセッション完了処理が落ちない"""
        SessionParticipant.objects.create(
            session=self.session,
            guest_name='Guest Player',
            role='player',
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f'/api/schedules/sessions/{self.session.id}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    def test_session_detail_marks_invited_users_as_pending(self):
        """招待済みユーザーをセッション詳細で招待済み（pending）として扱えるようにする"""
        SessionInvitation.objects.create(
            session=self.session,
            inviter=self.user1,
            invitee=self.user2,
            status='pending',
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/detail/',
            HTTP_ACCEPT='text/html',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, f'\"{self.user2.id}\": \"pending\"')

    def test_session_detail_uses_fixed_share_url_for_shareable_character_sheet(self):
        character = CharacterSheet.objects.create(
            user=self.user2,
            edition='7th',
            name='Linked Investigator',
            age=30,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=50,
            access_scope='link',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
            character_sheet=character,
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/detail/',
            HTTP_ACCEPT='text/html',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(
            response,
            reverse('fixed-shared-character-view', kwargs={'share_token': character.share_token}),
        )
        self.assertNotContains(response, reverse('character_public_view', kwargs={'character_id': character.id}))

    def test_session_detail_character_copy_does_not_render_legacy_public_url(self):
        character = CharacterSheet.objects.create(
            user=self.user2,
            edition='7th',
            name='Private Linked Investigator',
            age=30,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=50,
            access_scope='private',
        )
        SessionParticipant.objects.create(
            session=self.session,
            user=self.user2,
            role='player',
            character_sheet=character,
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f'/api/schedules/sessions/{self.session.id}/detail/',
            HTTP_ACCEPT='text/html',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, f'copyParticipantCharacterShareUrl({character.id})')
        self.assertNotContains(response, reverse('character_public_view', kwargs={'character_id': character.id}))

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
        self.session.visibility = 'public'
        self.session.save(update_fields=['visibility'])

        url = reverse('public_session_detail', kwargs={'share_token': self.session.share_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.session.title)
        self.assertContains(response, self.group.name)
        self.assertNotContains(response, self.group.description)
        self.assertContains(response, self.player.nickname)
        self.assertContains(response, f'/share/sessions/{self.session.share_token}/view/')
        self.assertNotContains(response, f'http://testserver/sessions/{self.session.share_token}/view/')

    def test_public_session_detail_hides_private_character_internal_links(self):
        character = CharacterSheet.objects.create(
            user=self.player,
            edition='7th',
            name='Private Session PC',
            age=30,
            str_value=50,
            con_value=50,
            pow_value=50,
            dex_value=50,
            app_value=50,
            siz_value=50,
            int_value=50,
            edu_value=50,
            access_scope='private',
        )
        SessionParticipant.objects.filter(
            session=self.session,
            user=self.player,
        ).update(character_sheet=character)
        self.session.visibility = 'public'
        self.session.save(update_fields=['visibility'])

        response = self.client.get(reverse('public_session_detail', kwargs={'share_token': self.session.share_token}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.player.nickname)
        self.assertNotContains(response, f'/accounts/character/{character.id}/')
        self.assertNotContains(response, f'copyParticipantCharacterShareUrl({character.id})')
        self.assertNotContains(response, reverse('character_public_view', kwargs={'character_id': character.id}))

    def test_public_session_detail_invalid_token_404(self):
        url = reverse('public_session_detail', kwargs={'share_token': uuid.uuid4()})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_detail_requires_login(self):
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_private_session_detail_shows_copy_link_button_without_prefilled_url(self):
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="copyPublicSessionLinkBtn"')
        self.assertContains(response, 'data-share-url=""')
        self.assertNotContains(response, f"/share/sessions/{self.session.share_token}/view/")

    def test_public_session_detail_has_copy_link_button(self):
        self.session.visibility = 'public'
        self.session.save(update_fields=['visibility'])

        self.client.force_authenticate(user=self.gm)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="copyPublicSessionLinkBtn"')
        self.assertContains(response, f"/share/sessions/{self.session.share_token}/view/")
