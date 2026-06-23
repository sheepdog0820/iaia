from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from schedules.models import HandoutAttachment, HandoutInfo, HandoutNotification, SessionParticipant, TRPGSession
from schedules.serializers import HandoutNotificationSerializer
from schedules.notification_serializers import HandoutNotificationSerializer as LegacyHandoutNotificationSerializer


User = get_user_model()


class HandoutPermissionTestCase(APITestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            username='handout_gm',
            email='handout_gm@example.com',
            password='pass1234',
        )
        self.player = User.objects.create_user(
            username='handout_player',
            email='handout_player@example.com',
            password='pass1234',
        )
        self.other_player = User.objects.create_user(
            username='handout_other',
            email='handout_other@example.com',
            password='pass1234',
        )

        self.session_a = TRPGSession.objects.create(
            title='Session A',
            date=timezone.now() + timedelta(days=1),
            gm=self.gm,
            visibility='private',
        )
        self.session_b = TRPGSession.objects.create(
            title='Session B',
            date=timezone.now() + timedelta(days=2),
            gm=self.gm,
            visibility='private',
        )

        self.player_a_slot1 = SessionParticipant.objects.create(
            session=self.session_a,
            user=self.player,
            role='player',
            player_slot=1,
        )
        self.player_b_slot2 = SessionParticipant.objects.create(
            session=self.session_b,
            user=self.player,
            role='player',
            player_slot=2,
        )
        self.other_a_slot2 = SessionParticipant.objects.create(
            session=self.session_a,
            user=self.other_player,
            role='player',
            player_slot=2,
        )

    def test_secret_slot_handout_does_not_leak_across_sessions(self):
        leaked_if_slot_and_session_are_matched_independently = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Other player secret',
            content='This must not leak to the player in slot 1.',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )

        self.client.force_authenticate(user=self.player)

        list_response = self.client.get('/api/schedules/handouts/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        handouts = list_response.data.get('results', list_response.data)
        self.assertNotIn(
            leaked_if_slot_and_session_are_matched_independently.id,
            [handout['id'] for handout in handouts],
        )

        detail_response = self.client.get(
            f'/api/schedules/handouts/{leaked_if_slot_and_session_are_matched_independently.id}/'
        )
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_handout_is_visible_to_all_session_participants(self):
        public_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Shared clue',
            content='Everyone in the session can read this.',
            is_secret=False,
        )

        self.client.force_authenticate(user=self.player)

        list_response = self.client.get('/api/schedules/handouts/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        handouts = list_response.data.get('results', list_response.data)
        self.assertIn(public_handout.id, [handout['id'] for handout in handouts])

        detail_response = self.client.get(f'/api/schedules/handouts/{public_handout.id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

    def test_secret_handout_attachments_follow_handout_visibility(self):
        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Attachment secret',
            content='Only the assigned player and GM can see attachments.',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        HandoutAttachment.objects.create(
            handout=secret_handout,
            file='handout_attachments/secret.txt',
            original_filename='secret.txt',
            file_type='document',
            file_size=10,
            content_type='text/plain',
            uploaded_by=self.gm,
        )

        self.client.force_authenticate(user=self.player)

        response = self.client.get(f'/api/schedules/handouts/{secret_handout.id}/attachments/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_secret_handout_attachment_delete_hides_existence_from_unauthorized_user(self):
        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Delete endpoint secret',
            content='The attachment id must not be enumerable.',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        attachment = HandoutAttachment.objects.create(
            handout=secret_handout,
            file='handout_attachments/delete-secret.txt',
            original_filename='delete-secret.txt',
            file_type='document',
            file_size=10,
            content_type='text/plain',
            uploaded_by=self.gm,
        )

        self.client.force_authenticate(user=self.player)

        response = self.client.delete(f'/api/schedules/attachments/{attachment.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(HandoutAttachment.objects.filter(id=attachment.id).exists())

    def test_visible_handout_attachment_delete_forbidden_for_non_uploader_participant(self):
        public_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Shared attachment',
            content='Visible handout attachment cannot be deleted by participants.',
            is_secret=False,
        )
        attachment = HandoutAttachment.objects.create(
            handout=public_handout,
            file='handout_attachments/shared.txt',
            original_filename='shared.txt',
            file_type='document',
            file_size=10,
            content_type='text/plain',
            uploaded_by=self.gm,
        )

        self.client.force_authenticate(user=self.player)

        response = self.client.delete(f'/api/schedules/attachments/{attachment.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(HandoutAttachment.objects.filter(id=attachment.id).exists())

    def test_secret_handout_notification_is_hidden_from_unauthorized_recipient(self):
        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Notification secret title',
            content='Notification secret content',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        notification = HandoutNotification.objects.create(
            handout_id=secret_handout.id,
            recipient=self.player,
            sender=self.gm,
            notification_type='handout_updated',
            message='Notification secret title was updated',
        )

        self.client.force_authenticate(user=self.player)

        list_response = self.client.get('/api/schedules/notifications/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        notifications = list_response.data.get('results', list_response.data)
        self.assertNotIn(notification.id, [item['id'] for item in notifications])
        self.assertNotIn('Notification secret title', list_response.rendered_content.decode())

        detail_response = self.client.get(f'/api/schedules/notifications/{notification.id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

        mark_read_response = self.client.patch(f'/api/schedules/notifications/{notification.id}/mark_read/')
        self.assertEqual(mark_read_response.status_code, status.HTTP_404_NOT_FOUND)

        unread_response = self.client.get('/api/schedules/notifications/unread_count/')
        self.assertEqual(unread_response.status_code, status.HTTP_200_OK)
        self.assertEqual(unread_response.data['unread_count'], 0)

        mark_all_response = self.client.patch('/api/schedules/notifications/mark_all_read/')
        self.assertEqual(mark_all_response.status_code, status.HTTP_200_OK)
        self.assertEqual(mark_all_response.data['updated_count'], 0)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_secret_handout_notification_serializer_omits_hidden_handout_info(self):
        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Serializer secret title',
            content='Serializer secret content',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        notification = HandoutNotification.objects.create(
            handout_id=secret_handout.id,
            recipient=self.player,
            sender=self.gm,
            notification_type='handout_updated',
            message='Serializer secret title was updated',
        )
        request = APIRequestFactory().get('/api/schedules/notifications/')
        request.user = self.player

        serializer = HandoutNotificationSerializer(notification, context={'request': request})

        self.assertIsNone(serializer.data['handout_info'])

    def test_legacy_notification_serializer_omits_hidden_handout_info(self):
        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Legacy serializer secret title',
            content='Legacy serializer secret content',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        notification = HandoutNotification.objects.create(
            handout_id=secret_handout.id,
            recipient=self.player,
            sender=self.gm,
            notification_type='handout_updated',
            message='Legacy serializer secret title was updated',
        )
        request = APIRequestFactory().get('/api/schedules/notifications/')
        request.user = self.player

        serializer = LegacyHandoutNotificationSerializer(notification, context={'request': request})

        self.assertIsNone(serializer.data['handout_info'])

    def test_public_session_share_url_does_not_render_secret_handouts(self):
        self.session_a.visibility = 'public'
        self.session_a.save(update_fields=['visibility'])

        secret_handout = HandoutInfo.objects.create(
            session=self.session_a,
            participant=self.other_a_slot2,
            title='Never render this secret title',
            content='Never render this secret content',
            is_secret=True,
            handout_number=2,
            assigned_player_slot=2,
        )
        url = reverse(
            'session_public_view',
            kwargs={'share_token': self.session_a.share_token},
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, secret_handout.title)
        self.assertNotContains(response, secret_handout.content)
