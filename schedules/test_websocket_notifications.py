from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase

from schedules.models import HandoutNotification
from tableno.asgi import application


class NotificationWebSocketTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='socket-user',
            email='socket-user@example.com',
            password='pass123',
        )
        self.other = user_model.objects.create_user(
            username='socket-other',
            email='socket-other@example.com',
            password='pass123',
        )

    def test_anonymous_connection_is_rejected(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application, '/ws/notifications/'
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(scenario)()

    def test_authenticated_user_receives_only_own_notifications(self):
        client = Client()
        client.force_login(self.user)
        session_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value

        async def create_notification(recipient_id, message):
            recipient = await database_sync_to_async(
                get_user_model().objects.get
            )(pk=recipient_id)
            sender = await database_sync_to_async(
                get_user_model().objects.get
            )(pk=self.other.pk)
            return await database_sync_to_async(HandoutNotification.objects.create)(
                handout_id=0,
                recipient=recipient,
                sender=sender,
                notification_type='session_reminder',
                message=message,
            )

        async def scenario():
            communicator = WebsocketCommunicator(
                application,
                '/ws/notifications/',
                headers=[
                    (
                        b'cookie',
                        f'{settings.SESSION_COOKIE_NAME}={session_cookie}'.encode(),
                    ),
                ],
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await create_notification(self.other.pk, 'not for socket user')
            self.assertTrue(await communicator.receive_nothing(timeout=0.1))

            await create_notification(self.user.pk, 'socket notification')
            payload = await communicator.receive_json_from(timeout=1)
            self.assertEqual(payload['type'], 'notification.created')
            self.assertEqual(
                payload['notification']['message'],
                'socket notification',
            )
            self.assertEqual(payload['unread_count'], 1)
            await communicator.disconnect()

        async_to_sync(scenario)()
