import base64
import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from support.models import LineWebhookEvent, SupportMessage, SupportTicket
from support.services import resolve_ticket_and_notify


@override_settings(
    LINE_CHANNEL_SECRET="test-secret",
    LINE_CHANNEL_ACCESS_TOKEN="test-token",
    LINE_SUPPORT_ADMIN_EMAIL="admin@example.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class LineWebhookTests(TestCase):
    def _signature(self, body):
        digest = hmac.new(b"test-secret", body, hashlib.sha256).digest()
        return base64.b64encode(digest).decode("ascii")

    def _post(self, payload, signature=None):
        body = json.dumps(payload).encode("utf-8")
        return self.client.post(
            reverse("line-support-webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_LINE_SIGNATURE=signature or self._signature(body),
        )

    def test_rejects_invalid_signature(self):
        response = self._post({"events": []}, signature="invalid")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(LineWebhookEvent.objects.exists())

    @patch("support.services.reply_to_line")
    def test_text_message_creates_ticket_replies_and_emails_admin(self, reply_mock):
        response = self._post(
            {
                "events": [
                    {
                        "type": "message",
                        "webhookEventId": "evt-001",
                        "timestamp": 1783760400000,
                        "replyToken": "reply-token",
                        "source": {"type": "user", "userId": "U123"},
                        "message": {
                            "id": "msg-001",
                            "type": "text",
                            "text": "保存するとエラーになります",
                        },
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, 200)
        event = LineWebhookEvent.objects.get(event_id="evt-001")
        self.assertEqual(event.status, LineWebhookEvent.Status.PROCESSED)
        ticket = SupportTicket.objects.get()
        self.assertEqual(ticket.source, SupportTicket.Source.LINE)
        self.assertEqual(ticket.line_user_id, "U123")
        self.assertEqual(ticket.status, SupportTicket.Status.NEW)
        self.assertEqual(ticket.messages.get().body, "保存するとエラーになります")
        reply_mock.assert_called_once()
        self.assertIn(ticket.reference, reply_mock.call_args.args[1])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(ticket.reference, mail.outbox[0].subject)

    @patch("support.services.reply_to_line")
    def test_duplicate_webhook_event_is_idempotent(self, reply_mock):
        payload = {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": "evt-duplicate",
                    "timestamp": 1783760400000,
                    "replyToken": "reply-token",
                    "source": {"type": "user", "userId": "U123"},
                    "message": {"id": "msg-duplicate", "type": "text", "text": "障害です"},
                }
            ]
        }

        self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(self._post(payload).status_code, 200)

        self.assertEqual(LineWebhookEvent.objects.count(), 1)
        self.assertEqual(SupportTicket.objects.count(), 1)
        self.assertEqual(SupportMessage.objects.count(), 1)
        reply_mock.assert_called_once()
        self.assertEqual(len(mail.outbox), 1)

    def test_non_message_event_is_recorded_without_ticket(self):
        response = self._post(
            {
                "events": [
                    {
                        "type": "follow",
                        "webhookEventId": "evt-follow",
                        "timestamp": 1783760400000,
                        "replyToken": "reply-token",
                        "source": {"type": "user", "userId": "U123"},
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(LineWebhookEvent.objects.get().status, LineWebhookEvent.Status.IGNORED)
        self.assertFalse(SupportTicket.objects.exists())

    @override_settings(LINE_WEBHOOK_USE_CELERY=True)
    @patch("support.tasks.process_line_event_task.delay")
    def test_celery_mode_persists_event_before_queueing(self, delay_mock):
        response = self._post(
            {
                "events": [
                    {
                        "type": "message",
                        "webhookEventId": "evt-async",
                        "timestamp": 1783760400000,
                        "replyToken": "reply-token",
                        "source": {"type": "user", "userId": "U-async"},
                        "message": {"id": "msg-async", "type": "text", "text": "障害です"},
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, 200)
        event = LineWebhookEvent.objects.get(event_id="evt-async")
        self.assertEqual(event.status, LineWebhookEvent.Status.RECEIVED)
        delay_mock.assert_called_once_with(event.pk)
        self.assertFalse(SupportTicket.objects.exists())

    @patch("support.services.reply_to_line")
    def test_follow_up_message_is_added_to_existing_open_ticket(self, reply_mock):
        first = {
            "type": "message",
            "webhookEventId": "evt-first",
            "timestamp": 1783760400000,
            "replyToken": "reply-first",
            "source": {"type": "user", "userId": "U-follow-up"},
            "message": {"id": "msg-first", "type": "text", "text": "保存に失敗します"},
        }
        second = {
            "type": "message",
            "webhookEventId": "evt-second",
            "timestamp": 1783760460000,
            "replyToken": "reply-second",
            "source": {"type": "user", "userId": "U-follow-up"},
            "message": {"id": "msg-second", "type": "text", "text": "キャラクター画面です"},
        }

        self.assertEqual(self._post({"events": [first]}).status_code, 200)
        self.assertEqual(self._post({"events": [second]}).status_code, 200)

        ticket = SupportTicket.objects.get()
        self.assertEqual(
            list(ticket.messages.values_list("body", flat=True)), ["保存に失敗します", "キャラクター画面です"]
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("追記", mail.outbox[1].subject)
        self.assertIn(ticket.reference, reply_mock.call_args.args[1])

    @patch("support.services.fetch_line_content", return_value=(b"image-bytes", "image/jpeg"))
    @patch("support.services.reply_to_line")
    def test_image_message_is_stored_on_existing_ticket(self, reply_mock, fetch_mock):
        ticket = SupportTicket.objects.create(subject="既存障害", line_user_id="U-image")
        response = self._post(
            {
                "events": [
                    {
                        "type": "message",
                        "webhookEventId": "evt-image",
                        "timestamp": 1783760400000,
                        "replyToken": "reply-image",
                        "source": {"type": "user", "userId": "U-image"},
                        "message": {"id": "msg-image", "type": "image"},
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, 200)
        message = ticket.messages.get()
        self.assertEqual(message.kind, SupportMessage.Kind.IMAGE)
        self.assertTrue(Path(message.attachment.name).name.startswith("msg-image"))
        self.assertTrue(message.attachment.name.endswith(".jpg"))
        self.addCleanup(message.attachment.delete, save=False)
        fetch_mock.assert_called_once_with("msg-image")
        reply_mock.assert_called_once()

    @patch("support.services.fetch_line_content", side_effect=RuntimeError("LINE unavailable"))
    def test_processing_failure_is_recorded_for_retry(self, fetch_mock):
        self.client.raise_request_exception = False
        response = self._post(
            {
                "events": [
                    {
                        "type": "message",
                        "webhookEventId": "evt-failed-image",
                        "timestamp": 1783760400000,
                        "replyToken": "reply-image",
                        "source": {"type": "user", "userId": "U-failed-image"},
                        "message": {"id": "msg-failed-image", "type": "image"},
                    }
                ]
            }
        )

        self.assertEqual(response.status_code, 500)
        event = LineWebhookEvent.objects.get(event_id="evt-failed-image")
        self.assertEqual(event.status, LineWebhookEvent.Status.FAILED)
        self.assertIn("LINE unavailable", event.last_error)
        self.assertFalse(SupportTicket.objects.exists())

    @patch("support.services.reply_to_line")
    @patch("support.services.fetch_line_content", side_effect=[RuntimeError("temporary"), (b"ok", "image/jpeg")])
    def test_failed_event_is_reprocessed_on_line_redelivery(self, fetch_mock, reply_mock):
        self.client.raise_request_exception = False
        payload = {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": "evt-redelivery",
                    "timestamp": 1783760400000,
                    "replyToken": "reply-image",
                    "source": {"type": "user", "userId": "U-redelivery"},
                    "message": {"id": "msg-redelivery", "type": "image"},
                }
            ]
        }

        self.assertEqual(self._post(payload).status_code, 500)
        self.assertEqual(self._post(payload).status_code, 200)

        event = LineWebhookEvent.objects.get(event_id="evt-redelivery")
        self.assertEqual(event.status, LineWebhookEvent.Status.PROCESSED)
        message = SupportMessage.objects.get()
        self.addCleanup(message.attachment.delete, save=False)

    @patch("support.services.push_to_line")
    def test_resolve_ticket_notifies_line_user(self, push_mock):
        ticket = SupportTicket.objects.create(subject="解決対象", line_user_id="U-resolve")

        resolve_ticket_and_notify(ticket)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)
        self.assertIsNotNone(ticket.resolved_at)
        push_mock.assert_called_once()
        self.assertIn(ticket.reference, push_mock.call_args.args[1])
