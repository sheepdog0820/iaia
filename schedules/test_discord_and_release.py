from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import DiscordDelivery, Group, GroupDiscordSettings, GroupMembership
from schedules.handout_release import evaluate_release_conditions
from schedules.models import HandoutInfo, HandoutView, SessionParticipant, TRPGSession
from schedules.serializers import HandoutInfoSerializer
from schedules.tasks import publish_scheduled_handouts, send_discord_webhook


class DiscordSettingsTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="discord-admin",
            email="discord-admin@example.com",
            password="pass123",
        )
        self.member = user_model.objects.create_user(
            username="discord-member",
            email="discord-member@example.com",
            password="pass123",
        )
        self.group = Group.objects.create(name="Discord Group", created_by=self.admin)
        GroupMembership.objects.create(group=self.group, user=self.member, role="member")
        self.url = f"/api/groups/{self.group.pk}/discord-settings/"

    def test_admin_can_store_encrypted_webhook_without_exposing_it(self):
        self.client.force_authenticate(self.admin)
        webhook_url = "https://discord.com/api/webhooks/123/secret"

        response = self.client.put(
            self.url,
            {
                "enabled": True,
                "event_types": ["session_updated"],
                "webhook_url": webhook_url,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["configured"])
        self.assertNotIn("webhook_url", response.data)
        settings_obj = GroupDiscordSettings.objects.get(group=self.group)
        self.assertNotIn(webhook_url, settings_obj.encrypted_webhook_url)
        self.assertEqual(settings_obj.get_webhook_url(), webhook_url)

    def test_non_admin_cannot_read_or_change_settings(self):
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.put(self.url, {"enabled": False}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @patch("schedules.tasks.requests.post")
    def test_delivery_is_idempotent(self, post):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.save()
        post.return_value = Mock(status_code=204)
        post.return_value.raise_for_status.return_value = None

        args = (
            self.group.pk,
            "session_updated",
            {"content": "updated"},
            "session-updated:1:revision-1",
        )
        self.assertEqual(send_discord_webhook.run(*args), "sent")
        self.assertEqual(send_discord_webhook.run(*args), "already-sent")

        self.assertEqual(post.call_count, 1)
        self.assertEqual(
            DiscordDelivery.objects.get().status,
            DiscordDelivery.Status.SENT,
        )

    def test_admin_can_list_discord_delivery_failures(self):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        failed = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:failed",
            payload={"content": "failed"},
            status=DiscordDelivery.Status.FAILED,
            last_error="Discord returned 500",
        )
        DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_created",
            idempotency_key="session-created:sent",
            payload={"content": "sent"},
            status=DiscordDelivery.Status.SENT,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(f"/api/groups/{self.group.pk}/discord-deliveries/?status=failed")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], failed.pk)
        self.assertEqual(response.data[0]["last_error"], "Discord returned 500")
        self.assertEqual(response.data[0]["payload"], {"content": "failed"})

    def test_delivery_list_without_settings_has_no_side_effect(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(f"/api/groups/{self.group.pk}/discord-deliveries/?status=failed")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
        self.assertFalse(GroupDiscordSettings.objects.filter(group=self.group).exists())

    def test_non_admin_cannot_list_or_retry_discord_deliveries(self):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.save()
        delivery = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:failed",
            payload={"content": "failed"},
            status=DiscordDelivery.Status.FAILED,
        )
        self.client.force_authenticate(self.member)

        list_response = self.client.get(f"/api/groups/{self.group.pk}/discord-deliveries/")
        retry_response = self.client.post(f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/")

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(retry_response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("accounts.discord_views._broker_available", return_value=True)
    @patch("accounts.discord_views.send_discord_webhook.delay")
    def test_failed_delivery_retry_reuses_same_record(self, delay, broker_available):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.save()
        delivery = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:failed",
            payload={"content": "failed"},
            status=DiscordDelivery.Status.FAILED,
            attempts=2,
            last_error="Discord returned 500",
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["queued"])
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DiscordDelivery.Status.PENDING)
        self.assertEqual(delivery.last_error, "")
        self.assertEqual(delivery.attempts, 2)
        delay.assert_called_once_with(
            self.group.pk,
            "session_updated",
            {"content": "failed"},
            "session-updated:failed",
        )

    def test_retry_rejects_non_failed_delivery(self):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.save()
        delivery = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:pending",
            payload={"content": "pending"},
            status=DiscordDelivery.Status.PENDING,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retry_requires_enabled_configured_event_type(self):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=False,
            event_types=["session_updated"],
        )
        delivery = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:failed",
            payload={"content": "failed"},
            status=DiscordDelivery.Status.FAILED,
        )
        self.client.force_authenticate(self.admin)

        disabled_response = self.client.post(f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/")
        settings_obj.enabled = True
        settings_obj.save(update_fields=["enabled"])
        missing_webhook_response = self.client.post(
            f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/"
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.event_types = []
        settings_obj.save()
        disabled_event_response = self.client.post(
            f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/"
        )

        self.assertEqual(disabled_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_webhook_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(disabled_event_response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.discord_views._broker_available", return_value=False)
    def test_retry_reports_broker_unavailable(self, broker_available):
        settings_obj = GroupDiscordSettings.objects.create(
            group=self.group,
            enabled=True,
            event_types=["session_updated"],
        )
        settings_obj.set_webhook_url("https://discord.com/api/webhooks/123/secret")
        settings_obj.save()
        delivery = DiscordDelivery.objects.create(
            settings=settings_obj,
            event_type="session_updated",
            idempotency_key="session-updated:failed",
            payload={"content": "failed"},
            status=DiscordDelivery.Status.FAILED,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/groups/{self.group.pk}/discord-deliveries/{delivery.pk}/retry/")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertFalse(response.data["queued"])
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DiscordDelivery.Status.FAILED)
        self.assertEqual(
            delivery.last_error,
            "Background task broker is unavailable.",
        )


class HandoutReleaseTestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.gm = user_model.objects.create_user(
            username="release-gm",
            email="release-gm@example.com",
            password="pass123",
        )
        self.player = user_model.objects.create_user(
            username="release-player",
            email="release-player@example.com",
            password="pass123",
        )
        self.group = Group.objects.create(name="Release Group", created_by=self.gm)
        self.session = TRPGSession.objects.create(
            title="Release Session",
            gm=self.gm,
            group=self.group,
            date=timezone.now() + timedelta(days=1),
            status="planned",
        )
        self.participant = SessionParticipant.objects.create(
            session=self.session,
            user=self.player,
            role="player",
            player_slot=1,
        )

    def create_handout(self, title="Handout", **kwargs):
        return HandoutInfo.objects.create(
            session=self.session,
            participant=self.participant,
            title=title,
            content="content",
            **kwargs,
        )

    def test_all_condition_requires_every_leaf(self):
        handout = self.create_handout(
            release_conditions={
                "operator": "all",
                "conditions": [
                    {"type": "session_status", "value": "planned"},
                    {"type": "player_slot", "value": 1},
                    {
                        "type": "datetime_reached",
                        "value": (timezone.now() - timedelta(minutes=1)).isoformat(),
                    },
                ],
            }
        )
        self.assertTrue(evaluate_release_conditions(handout))
        handout.participant.player_slot = 2
        handout.participant.save(update_fields=["player_slot"])
        self.assertFalse(evaluate_release_conditions(handout))

    def test_handout_view_dependency_uses_assigned_participant(self):
        prerequisite = self.create_handout("Prerequisite")
        handout = self.create_handout(
            "Dependent",
            release_conditions={
                "type": "handout_viewed",
                "value": prerequisite.pk,
            },
        )
        self.assertFalse(evaluate_release_conditions(handout))
        HandoutView.objects.create(handout=prerequisite, user=self.player)
        self.assertTrue(evaluate_release_conditions(handout))

    def test_serializer_rejects_circular_dependencies(self):
        first = self.create_handout("First")
        second = self.create_handout("Second")
        first_serializer = HandoutInfoSerializer(
            first,
            data={
                "release_conditions": {
                    "type": "handout_viewed",
                    "value": second.pk,
                },
            },
            partial=True,
        )
        self.assertTrue(first_serializer.is_valid(), first_serializer.errors)
        first_serializer.save()

        second_serializer = HandoutInfoSerializer(
            second,
            data={
                "release_conditions": {
                    "type": "handout_viewed",
                    "value": first.pk,
                },
            },
            partial=True,
        )
        self.assertFalse(second_serializer.is_valid())
        self.assertIn("release_conditions", second_serializer.errors)

    @patch("schedules.tasks.queue_discord_event")
    @patch("schedules.notifications.HandoutNotificationService.send_handout_published_notification")
    def test_periodic_task_publishes_eligible_handout(self, notify, queue):
        handout = self.create_handout(
            release_status=HandoutInfo.ReleaseStatus.WAITING,
            release_conditions={
                "type": "datetime_reached",
                "value": (timezone.now() - timedelta(minutes=1)).isoformat(),
            },
        )

        self.assertEqual(publish_scheduled_handouts(), 1)
        handout.refresh_from_db()
        self.assertFalse(handout.is_secret)
        self.assertEqual(
            handout.release_status,
            HandoutInfo.ReleaseStatus.RELEASED,
        )
        notify.assert_called_once()
        queue.assert_called_once()
