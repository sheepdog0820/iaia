from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet
from accounts.models import CustomUser, Group
from schedules.models import TRPGSession, SessionParticipant


class SessionNotesLogsAPITestCase(APITestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='pass1234',
            nickname='GM',
        )
        self.player1 = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass1234',
            nickname='PL1',
        )
        self.player2 = CustomUser.objects.create_user(
            username='player2',
            email='player2@example.com',
            password='pass1234',
            nickname='PL2',
        )
        self.outsider = CustomUser.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='pass1234',
            nickname='Outsider',
        )

        self.group = Group.objects.create(
            name='Test Group',
            description='Group for notes/log tests',
            created_by=self.gm,
            visibility='private',
        )
        self.group.members.add(self.gm, self.player1, self.player2)

        self.session = TRPGSession.objects.create(
            title='Notes Logs Session',
            description='',
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            duration_minutes=180,
            location='Online',
            gm=self.gm,
            group=self.group,
            status='planned',
            visibility='group',
        )

        self.participant1 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player1,
            role='player',
        )
        self.participant2 = SessionParticipant.objects.create(
            session=self.session,
            user=self.player2,
            role='player',
        )

    def test_notes_visibility_and_permissions(self):
        self.client.force_authenticate(user=self.gm)
        gm_private = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/notes/',
            {'note_type': 'gm_private', 'title': 'GM秘密', 'content': 'secret', 'is_pinned': True},
            format='json',
        )
        self.assertEqual(gm_private.status_code, status.HTTP_201_CREATED)

        public_summary = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/notes/',
            {'note_type': 'public_summary', 'title': '公開', 'content': 'summary'},
            format='json',
        )
        self.assertEqual(public_summary.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.player1)

        # 非GMはplayer_note以外の作成不可
        forbidden = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/notes/',
            {'note_type': 'gm_private', 'title': 'NG', 'content': 'x'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # 非GMはピン留め不可
        forbidden_pin = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/notes/',
            {'title': '自分メモ', 'content': 'note', 'is_pinned': True},
            format='json',
        )
        self.assertEqual(forbidden_pin.status_code, status.HTTP_403_FORBIDDEN)

        player_note = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/notes/',
            {'title': '自分メモ', 'content': 'note'},
            format='json',
        )
        self.assertEqual(player_note.status_code, status.HTTP_201_CREATED)

        # playerは公開サマリー+引き継ぎ+自分のノートのみ見える（gm_privateは見えない）
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/notes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_types = {note['note_type'] for note in response.data}
        self.assertIn('public_summary', returned_types)
        self.assertIn('player_note', returned_types)
        self.assertNotIn('gm_private', returned_types)

        # playerは自分のplayer_noteのみ編集可能
        own_note_id = player_note.data['id']
        response = self.client.patch(
            f'/api/schedules/notes/{own_note_id}/',
            {'title': '更新', 'content': 'updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        public_note_id = public_summary.data['id']
        response = self.client.patch(
            f'/api/schedules/notes/{public_note_id}/',
            {'title': '更新', 'content': 'updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logs_visibility_and_permissions(self):
        character1 = CharacterSheet.objects.create(
            user=self.player1,
            edition='6th',
            name='Investigator 1',
            age=25,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
        )
        self.participant1.character_sheet = character1
        self.participant1.save(update_fields=['character_sheet'])

        unrelated_character = CharacterSheet.objects.create(
            user=self.gm,
            edition='6th',
            name='Unrelated',
            age=25,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
        )

        self.client.force_authenticate(user=self.player1)

        # 関連キャラクターがセッション参加者に紐づいていない場合は拒否
        response = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/logs/',
            {
                'timestamp': timezone.now().isoformat(),
                'event_type': 'general',
                'description': 'bad',
                'related_character': unrelated_character.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        ok = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/logs/',
            {
                'timestamp': timezone.now().isoformat(),
                'event_type': 'clue',
                'description': 'Found a clue',
                'related_character': character1.id,
            },
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

        log_id = ok.data['id']

        # 自分のログは編集可能
        response = self.client.patch(
            f'/api/schedules/logs/{log_id}/',
            {'description': 'Updated', 'event_type': 'general'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 他参加者は編集不可
        self.client.force_authenticate(user=self.player2)
        response = self.client.patch(
            f'/api/schedules/logs/{log_id}/',
            {'description': 'Hacked'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # GMは編集可能
        self.client.force_authenticate(user=self.gm)
        response = self.client.patch(
            f'/api/schedules/logs/{log_id}/',
            {'description': 'GM edit'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 一覧取得（参加者は閲覧可能）
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], log_id)

        # outsiderはアクセスできない（空配列になる）
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class SessionNotesLogsUITestCase(TestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='pass1234',
            nickname='GM',
        )
        self.player = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass1234',
            nickname='PL1',
        )
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.gm,
            visibility='private',
        )
        self.group.members.add(self.gm, self.player)
        self.session = TRPGSession.objects.create(
            title='UI Notes Logs Session',
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            gm=self.gm,
            group=self.group,
            status='planned',
            visibility='group',
        )
        SessionParticipant.objects.create(session=self.session, user=self.player, role='player')

    def test_session_detail_contains_notes_logs_ui_for_participant(self):
        self.client.login(username='player1', password='pass1234')
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'セッションノート / ログ')
        self.assertContains(response, 'sessionNotesLogsCard')
