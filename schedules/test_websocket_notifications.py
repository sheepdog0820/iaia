import importlib

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase, override_settings

from schedules.models import HandoutNotification
from tableno.asgi import application


class NotificationWebSocketTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.application = application
        self.default_origin_settings = override_settings(
            CSRF_TRUSTED_ORIGINS=["https://localhost", "http://localhost:8000"],
            PUBLIC_SITE_URL="https://localhost",
        )
        self.default_origin_settings.enable()
        self.addCleanup(self.default_origin_settings.disable)
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="socket-user",
            email="socket-user@example.com",
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass123",  # nosec B106
        )
        self.other = user_model.objects.create_user(
            username="socket-other",
            email="socket-other@example.com",
            # Isolated test fixture or mocked credential; never a production secret.
            password="pass123",  # nosec B106
        )

    def test_anonymous_connection_is_rejected(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                self.application,
                "/ws/notifications/",
                headers=[(b"origin", b"https://localhost")],
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(scenario)()

    def test_authenticated_user_receives_only_own_notifications(self):
        client = Client()
        client.force_login(self.user)
        session_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value

        async def create_notification(recipient_id, message):
            recipient = await database_sync_to_async(get_user_model().objects.get)(pk=recipient_id)
            sender = await database_sync_to_async(get_user_model().objects.get)(pk=self.other.pk)
            return await database_sync_to_async(HandoutNotification.objects.create)(
                handout_id=0,
                recipient=recipient,
                sender=sender,
                notification_type="session_reminder",
                message=message,
            )

        async def scenario():
            communicator = WebsocketCommunicator(
                self.application,
                "/ws/notifications/",
                headers=[
                    (b"origin", b"https://localhost"),
                    (
                        b"cookie",
                        f"{settings.SESSION_COOKIE_NAME}={session_cookie}".encode(),
                    ),
                ],
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await create_notification(self.other.pk, "not for socket user")
            self.assertTrue(await communicator.receive_nothing(timeout=0.1))

            await create_notification(self.user.pk, "socket notification")
            payload = await communicator.receive_json_from(timeout=1)
            self.assertEqual(payload["type"], "notification.created")
            self.assertEqual(
                payload["notification"]["message"],
                "socket notification",
            )
            self.assertEqual(payload["unread_count"], 1)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_authenticated_connection_rejects_untrusted_or_missing_origin(self):
        client = Client()
        client.force_login(self.user)
        cookie = f"{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}".encode()

        async def scenario(origin):
            headers = [(b"cookie", cookie)]
            if origin is not None:
                headers.append((b"origin", origin))
            communicator = WebsocketCommunicator(self.application, "/ws/notifications/", headers=headers)
            try:
                connected, _ = await communicator.connect()
                self.assertFalse(connected)
            finally:
                await communicator.disconnect()

        for origin in (
            None,
            b"null",
            b"not-an-origin",
            b"https://untrusted.example.invalid",
            b"https://localhost.attacker.invalid",
        ):
            with self.subTest(origin=origin):
                async_to_sync(scenario)(origin)

    def test_authenticated_connection_accepts_allowed_origin_with_port(self):
        client = Client()
        client.force_login(self.user)
        cookie = f"{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}".encode()

        async def scenario(origin):
            communicator = WebsocketCommunicator(
                self.application, "/ws/notifications/", headers=[(b"cookie", cookie), (b"origin", origin)]
            )
            try:
                connected, _ = await communicator.connect()
                self.assertTrue(connected)
            finally:
                await communicator.disconnect()

        for origin in (b"http://LOCALHOST:8000", b"https://localhost:443"):
            with self.subTest(origin=origin):
                async_to_sync(scenario)(origin)


class WildcardHostOriginPolicyTestCase(NotificationWebSocketTestCase):
    def setUp(self):
        super().setUp()
        self.origin_settings = override_settings(
            ALLOWED_HOSTS=["*"],
            CSRF_TRUSTED_ORIGINS=["https://localhost", "http://localhost:8000"],
            PUBLIC_SITE_URL="https://localhost",
        )
        self.origin_settings.enable()
        self.addCleanup(self.restore_origin_settings)
        self.application = importlib.reload(importlib.import_module("tableno.asgi")).application

    def restore_origin_settings(self):
        self.origin_settings.disable()
        importlib.reload(importlib.import_module("tableno.asgi"))

    def assert_origin_policy(self, cases):
        client = Client()
        client.force_login(self.user)
        cookie = f"{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}".encode()

        async def scenario(origin, expected):
            communicator = WebsocketCommunicator(
                self.application, "/ws/notifications/", headers=[(b"cookie", cookie), (b"origin", origin)]
            )
            try:
                connected, _ = await communicator.connect()
                self.assertEqual(connected, expected)
            finally:
                await communicator.disconnect()

        for origin, expected in cases:
            with self.subTest(origin=origin):
                async_to_sync(scenario)(origin, expected)

    @override_settings(CSRF_TRUSTED_ORIGINS=["*"], PUBLIC_SITE_URL="*")
    def test_global_wildcards_do_not_allow_socket_origins(self):
        self.assert_origin_policy(((b"https://localhost", False), (b"https://untrusted.example.invalid", False)))

    @override_settings(ALLOWED_HOSTS=["untrusted.example.invalid"])
    def test_http_host_allowance_does_not_grant_socket_origin(self):
        self.assert_origin_policy(((b"https://localhost", True), (b"https://untrusted.example.invalid", False)))

    @override_settings(CSRF_TRUSTED_ORIGINS=[], PUBLIC_SITE_URL="https://public.example.test")
    def test_public_site_origin_is_allowed_without_csrf_origins(self):
        self.assert_origin_policy(
            ((b"https://public.example.test", True), (b"https://untrusted.example.invalid", False))
        )

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://*.trusted.example.test"], PUBLIC_SITE_URL="")
    def test_explicit_trusted_subdomains_keep_their_boundary(self):
        self.assert_origin_policy(
            (
                (b"https://app.trusted.example.test", True),
                (b"https://trusted.example.test", True),
                (b"https://trusted.example.test.attacker.invalid", False),
                (b"https://untrusted.example.invalid", False),
            )
        )
