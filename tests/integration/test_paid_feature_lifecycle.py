"""Signed local webhook fixtures through ordinary-user feature authorization.

These tests do not prove Stripe Checkout or delivery from the real service.
"""

import hashlib
import hmac
import json
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import CharacterSheet, PremiumAuditLog, PremiumSubscription, StripeWebhookEvent
from scenarios.models import Scenario


@override_settings(
    STRIPE_SECRET_KEY="sk_test_local_fixture_only",
    STRIPE_WEBHOOK_SECRET="whsec_local_fixture_only",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PaidFeatureLifecycleTests(TestCase):
    def setUp(self):
        self.period_end = int(time.time()) + 86400
        self.user = get_user_model().objects.create_user(username="ordinary-subscriber")
        self.other = get_user_model().objects.create_user(username="other-owner")
        self.private_scenario = Scenario.objects.create(
            title="他人の秘匿シナリオ", created_by=self.other, visibility="private"
        )
        self.client = APIClient()
        self.client.force_login(self.user)
        PremiumSubscription.objects.create(user=self.user, stripe_customer_id="cus_local_fixture")

    def send_subscription(self, event_id, status, interval, cancel_at_period_end=False, valid_signature=True):
        event = {
            "id": event_id,
            "object": "event",
            "type": "customer.subscription.deleted" if status == "canceled" else "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_local_fixture",
                    "object": "subscription",
                    "customer": "cus_local_fixture",
                    "status": status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "items": {
                        "data": [
                            {
                                "current_period_end": self.period_end,
                                "price": {"id": f"price_local_{interval}", "recurring": {"interval": interval}},
                            }
                        ]
                    },
                }
            },
        }
        payload = json.dumps(event).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b"whsec_local_fixture_only", timestamp.encode() + b"." + payload, hashlib.sha256
        ).hexdigest()
        if not valid_signature:
            signature = "0" * 64
        return self.client.post(
            reverse("billing-webhook"),
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}",
        )

    def import_character(self, edition):
        payload = {
            "kind": "character",
            "sourceVersion": edition,
            "data": {
                "name": "契約検証の探索者",
                "commands": "CCB<=50 【目星】",
                "status": [
                    {"label": label, "value": value, "max": value}
                    for label, value in [("HP", 10), ("MP", 10), ("SAN", 50)]
                ],
                "params": [
                    {"label": label, "value": "10" if edition == "6th" else "50"}
                    for label in ["STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU"]
                ],
            },
        }
        return self.client.post(
            reverse("character-sheet-import-ccfolia-json"),
            {"ccfolia": payload, "edition": edition, "age": 20},
            format="json",
        )

    def assert_access(self, allowed):
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.is_premium, allowed)
        self.assertEqual(self.client.get(reverse("archive_view")).status_code, 200)
        # Premium access governs background processing, not KP preparation features.
        self.assertEqual(
            self.client.post(reverse("character-image-remove-background"), {}, format="multipart").status_code,
            400 if allowed else 403,
        )
        self.assertEqual(
            self.client.get(reverse("scenario-detail", kwargs={"pk": self.private_scenario.pk})).status_code, 404
        )

    def check_lifecycle(self, interval, edition):
        self.assert_access(False)
        self.assertEqual(self.import_character(edition).status_code, 201)
        self.assertEqual(CharacterSheet.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            self.send_subscription("evt_forged", "active", interval, valid_signature=False).status_code, 400
        )
        self.assertFalse(StripeWebhookEvent.objects.filter(event_id="evt_forged").exists())
        self.assert_access(False)

        self.assertEqual(self.send_subscription("evt_active", "active", interval).status_code, 200)
        self.assert_access(True)
        imported = self.import_character(edition)
        self.assertEqual(imported.status_code, 201, imported.data)
        character_id = imported.data["id"]
        self.assertEqual(CharacterSheet.objects.get(pk=character_id).edition, edition)
        duplicate = self.send_subscription("evt_active", "active", interval)
        self.assertTrue(duplicate.json()["duplicate"])
        self.assertEqual(PremiumAuditLog.objects.filter(user=self.user, action="granted").count(), 1)

        character_count = 2
        for event_id, status, cancel, allowed in [
            ("evt_cancel_scheduled", "active", True, True),
            ("evt_past_due", "past_due", True, False),
            ("evt_recovered", "active", False, True),
            ("evt_canceled", "canceled", False, False),
        ]:
            with self.subTest(status=status, event=event_id):
                self.assertEqual(self.send_subscription(event_id, status, interval, cancel).status_code, 200)
                self.assert_access(allowed)
                record = PremiumSubscription.objects.get(user=self.user)
                self.assertEqual(record.billing_interval, interval)
                self.assertIsNotNone(record.current_period_end)
                self.assertEqual(int(record.current_period_end.timestamp()), self.period_end)
                self.assertEqual(record.cancel_at_period_end, cancel)
                self.assertEqual(record.last_webhook_event_id, event_id)
                self.assertEqual(StripeWebhookEvent.objects.get(event_id=event_id).processing_status, "succeeded")
                self.assertEqual(self.import_character(edition).status_code, 201)
                character_count += 1
                self.assertEqual(CharacterSheet.objects.filter(user=self.user).count(), character_count)
                self.assertEqual(
                    self.client.get(reverse("character-sheet-detail", kwargs={"pk": character_id})).status_code, 200
                )
        self.assertEqual(PremiumAuditLog.objects.filter(user=self.user, action="granted").count(), 2)
        self.assertEqual(PremiumAuditLog.objects.filter(user=self.user, action="revoked").count(), 2)

    def test_monthly_subscription_and_sixth_edition(self):
        self.check_lifecycle("month", "6th")

    def test_yearly_subscription_and_seventh_edition(self):
        self.check_lifecycle("year", "7th")
