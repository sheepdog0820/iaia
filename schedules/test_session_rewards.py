from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.character_models import CharacterSheet, GrowthRecord
from accounts.models import CustomUser, Group
from schedules.models import SessionParticipant, SessionReward, TRPGSession


class SessionRewardsAPITestCase(APITestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='pass1234',
            nickname='GM',
        )
        self.co_gm = CustomUser.objects.create_user(
            username='co_gm_user',
            email='co_gm@example.com',
            password='pass1234',
            nickname='CoGM',
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
            name='Rewards Test Group',
            created_by=self.gm,
            visibility='private',
        )
        self.group.members.add(self.gm, self.co_gm, self.player1, self.player2)

        self.session = TRPGSession.objects.create(
            title='Rewards Session',
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            duration_minutes=180,
            location='Online',
            gm=self.gm,
            group=self.group,
            status='planned',
            visibility='group',
        )

        self.participant_co_gm = SessionParticipant.objects.create(
            session=self.session,
            user=self.co_gm,
            role='gm',
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

        self.character1 = CharacterSheet.objects.create(
            user=self.player1,
            edition='6th',
            name='PC1',
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
        self.participant1.character_sheet = self.character1
        self.participant1.save(update_fields=['character_sheet'])

    def test_rewards_visibility_and_permissions(self):
        self.client.force_authenticate(user=self.gm)
        create1 = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant1.id, 'experience_points': 5, 'special_rewards': 'SAN+1', 'notes': 'Good job'},
            format='json',
        )
        self.assertEqual(create1.status_code, status.HTTP_201_CREATED)

        create2 = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant2.id, 'experience_points': 3},
            format='json',
        )
        self.assertEqual(create2.status_code, status.HTTP_201_CREATED)

        # playerは自分の分のみ見える
        self.client.force_authenticate(user=self.player1)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/rewards/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['participant'], self.participant1.id)

        # outsiderは見えない（空配列）
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/rewards/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # playerは作成できない
        self.client.force_authenticate(user=self.player1)
        forbidden = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant1.id, 'experience_points': 1},
            format='json',
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # co-gm は作成できる
        other_session = TRPGSession.objects.create(
            title='Rewards Session 2',
            date=(timezone.now() + timedelta(days=2)).replace(microsecond=0),
            gm=self.gm,
            group=self.group,
            status='planned',
            visibility='group',
        )
        other_player = SessionParticipant.objects.create(session=other_session, user=self.player1, role='player')
        SessionParticipant.objects.create(session=other_session, user=self.co_gm, role='gm')

        self.client.force_authenticate(user=self.co_gm)
        ok = self.client.post(
            f'/api/schedules/sessions/{other_session.id}/rewards/',
            {'participant': other_player.id, 'experience_points': 2},
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

        # GM参加者（role=gm）へは作成できない
        bad = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant_co_gm.id, 'experience_points': 1},
            format='json',
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rewards_update_and_apply(self):
        self.client.force_authenticate(user=self.gm)
        create = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant1.id, 'experience_points': 5, 'special_rewards': 'SAN+1', 'notes': 'memo'},
            format='json',
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        reward_id = create.data['id']

        # GMは更新可能
        response = self.client.patch(
            f'/api/schedules/rewards/{reward_id}/',
            {'participant': self.participant1.id, 'experience_points': 6},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['experience_points'], 6)

        # playerは更新不可
        self.client.force_authenticate(user=self.player1)
        response = self.client.patch(
            f'/api/schedules/rewards/{reward_id}/',
            {'experience_points': 999},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # playerは反映不可
        response = self.client.post(f'/api/schedules/rewards/{reward_id}/apply/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 反映はGMのみ
        self.client.force_authenticate(user=self.gm)
        response = self.client.post(f'/api/schedules/rewards/{reward_id}/apply/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['applied_growth_record'])

        reward = SessionReward.objects.get(id=reward_id)
        self.assertIsNotNone(reward.applied_growth_record_id)
        self.assertTrue(GrowthRecord.objects.filter(id=reward.applied_growth_record_id).exists())

        growth = GrowthRecord.objects.get(id=reward.applied_growth_record_id)
        self.assertEqual(growth.character_sheet_id, self.character1.id)
        self.assertEqual(growth.experience_gained, 6)
        self.assertEqual(growth.special_rewards, 'SAN+1')
        self.assertEqual(growth.notes, 'memo')
        self.assertEqual(growth.scenario_name, self.session.title)

        # 更新して再反映すると同じレコードが更新される
        self.client.patch(
            f'/api/schedules/rewards/{reward_id}/',
            {'participant': self.participant1.id, 'experience_points': 7, 'notes': 'updated'},
            format='json',
        )
        response = self.client.post(f'/api/schedules/rewards/{reward_id}/apply/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        growth.refresh_from_db()
        self.assertEqual(growth.experience_gained, 7)
        self.assertEqual(growth.notes, 'updated')

        # キャラクター未設定の参加者は反映できない
        create2 = self.client.post(
            f'/api/schedules/sessions/{self.session.id}/rewards/',
            {'participant': self.participant2.id, 'experience_points': 1},
            format='json',
        )
        self.assertEqual(create2.status_code, status.HTTP_201_CREATED)
        reward2_id = create2.data['id']
        response = self.client.post(f'/api/schedules/rewards/{reward2_id}/apply/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SessionRewardsUITestCase(TestCase):
    def setUp(self):
        self.gm = CustomUser.objects.create_user(
            username='gm_user',
            email='gm@example.com',
            password='pass1234',
            nickname='GM',
        )
        self.viewer = CustomUser.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='pass1234',
            nickname='Viewer',
        )
        self.player = CustomUser.objects.create_user(
            username='player1',
            email='player1@example.com',
            password='pass1234',
            nickname='PL1',
        )
        self.group = Group.objects.create(
            name='UI Rewards Group',
            created_by=self.gm,
            visibility='private',
        )
        self.group.members.add(self.gm, self.viewer, self.player)

        self.session = TRPGSession.objects.create(
            title='UI Rewards Session',
            date=(timezone.now() + timedelta(days=1)).replace(microsecond=0),
            gm=self.gm,
            group=self.group,
            status='planned',
            visibility='group',
        )
        SessionParticipant.objects.create(session=self.session, user=self.player, role='player')

    def test_session_detail_reward_ui_visibility(self):
        # 参加者には表示される
        self.client.login(username='player1', password='pass1234')
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="sessionRewardsCard"')

        # グループメンバー（非参加者）には表示されない
        self.client.logout()
        self.client.login(username='viewer', password='pass1234')
        response = self.client.get(f'/api/schedules/sessions/{self.session.id}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="sessionRewardsCard"')
