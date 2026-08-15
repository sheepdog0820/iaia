from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Friend, FriendRequest
from schedules.models import HandoutNotification, UserNotificationPreferences

User = get_user_model()


def public_profile():
    return {"visibility": "public"}


class FriendCandidateAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="searcher", password="pass123")
        self.public_user = User.objects.create_user(
            username="public_target",
            nickname="公開ユーザー",
            email="private@example.com",
            trpg_history="非公開の履歴",
            trpg_introduction_sheet=public_profile(),
        )
        self.participants_user = User.objects.create_user(
            username="participants_target",
            nickname="参加者限定",
            trpg_introduction_sheet={"visibility": "participants"},
        )
        self.kp_user = User.objects.create_user(
            username="kp_target",
            nickname="KP限定",
            trpg_introduction_sheet={"visibility": "kp_only"},
        )
        self.unset_user = User.objects.create_user(username="unset_target", nickname="未設定")
        self.inactive_user = User.objects.create_user(
            username="inactive_target",
            nickname="無効ユーザー",
            is_active=False,
            trpg_introduction_sheet=public_profile(),
        )
        self.client.force_authenticate(user=self.user)

    def test_search_returns_only_explicitly_public_active_users(self):
        response = self.client.get("/api/accounts/friend-candidates/", {"q": "target"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.public_user.id])
        self.assertEqual(
            set(response.data["results"][0]),
            {"id", "username", "nickname", "profile_image"},
        )

    def test_search_matches_public_nickname_and_short_query_is_empty(self):
        response = self.client.get("/api/accounts/friend-candidates/", {"q": "公開"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], self.public_user.id)

        short_response = self.client.get("/api/accounts/friend-candidates/", {"q": "公"})
        self.assertEqual(short_response.status_code, status.HTTP_200_OK)
        self.assertEqual(short_response.data["results"], [])

    def test_search_prioritizes_exact_username_and_returns_at_most_twenty(self):
        for index in range(21):
            User.objects.create_user(
                username=f"candidate_{index:02d}",
                trpg_introduction_sheet=public_profile(),
            )
        exact = User.objects.create_user(
            username="candidate",
            trpg_introduction_sheet=public_profile(),
        )

        response = self.client.get("/api/accounts/friend-candidates/", {"q": "candidate"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertEqual(response.data["results"][0]["id"], exact.id)

    def test_search_excludes_self_friends_pending_and_cooldown_users(self):
        self.user.trpg_introduction_sheet = public_profile()
        self.user.save(update_fields=["trpg_introduction_sheet"])
        friend = User.objects.create_user(
            username="target_friend",
            trpg_introduction_sheet=public_profile(),
        )
        pending = User.objects.create_user(
            username="target_pending",
            trpg_introduction_sheet=public_profile(),
        )
        cooldown = User.objects.create_user(
            username="target_cooldown",
            trpg_introduction_sheet=public_profile(),
        )
        Friend.objects.create(user=self.user, friend=friend)
        FriendRequest.objects.create(sender=self.user, recipient=pending)
        FriendRequest.objects.create(
            sender=self.user,
            recipient=cooldown,
            status=FriendRequest.Status.DECLINED,
            responded_at=timezone.now(),
        )

        response = self.client.get("/api/accounts/friend-candidates/", {"q": "target"})
        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertNotIn(self.user.id, returned_ids)
        self.assertNotIn(friend.id, returned_ids)
        self.assertNotIn(pending.id, returned_ids)
        self.assertNotIn(cooldown.id, returned_ids)
        self.assertIn(self.public_user.id, returned_ids)


class FriendRequestAPITestCase(APITestCase):
    def setUp(self):
        self.sender = User.objects.create_user(username="sender", password="pass123")
        self.recipient = User.objects.create_user(
            username="recipient",
            password="pass123",
            nickname="受信者",
            trpg_introduction_sheet=public_profile(),
        )
        self.other = User.objects.create_user(username="other", password="pass123")
        self.client.force_authenticate(user=self.sender)

    def create_request(self):
        return self.client.post(
            "/api/accounts/friend-requests/",
            {"recipient_id": self.recipient.id},
            format="json",
        )

    def test_request_does_not_create_friend_and_creates_actionable_notification(self):
        response = self.create_request()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        friend_request = FriendRequest.objects.get(sender=self.sender, recipient=self.recipient)
        self.assertEqual(friend_request.status, FriendRequest.Status.PENDING)
        self.assertFalse(Friend.objects.filter(user=self.sender, friend=self.recipient).exists())
        notification = HandoutNotification.objects.get(
            recipient=self.recipient,
            notification_type="friend_request",
        )
        self.assertEqual(notification.metadata["friend_request_id"], friend_request.id)

        self.client.force_authenticate(user=self.recipient)
        notification_response = self.client.get("/api/schedules/notifications/")
        notification_data = notification_response.data["results"][0]
        self.assertEqual(notification_data["friend_request"]["id"], friend_request.id)
        self.assertEqual(notification_data["friend_request"]["status"], FriendRequest.Status.PENDING)

    def test_private_and_missing_recipients_have_the_same_response(self):
        private_user = User.objects.create_user(username="private", trpg_introduction_sheet={})

        private_response = self.client.post(
            "/api/accounts/friend-requests/",
            {"recipient_id": private_user.id},
            format="json",
        )
        missing_response = self.client.post(
            "/api/accounts/friend-requests/",
            {"recipient_id": 999999},
            format="json",
        )

        self.assertEqual(private_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(missing_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(private_response.data, missing_response.data)

    def test_visibility_is_rechecked_when_request_is_created(self):
        search_response = self.client.get("/api/accounts/friend-candidates/", {"q": "recipient"})
        self.assertEqual(search_response.data["results"][0]["id"], self.recipient.id)
        self.recipient.trpg_introduction_sheet = {"visibility": "participants"}
        self.recipient.save(update_fields=["trpg_introduction_sheet"])

        response = self.create_request()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(FriendRequest.objects.exists())

    def test_existing_request_can_be_accepted_after_recipient_becomes_private(self):
        request_id = self.create_request().data["id"]
        self.recipient.trpg_introduction_sheet = {"visibility": "participants"}
        self.recipient.save(update_fields=["trpg_introduction_sheet"])
        self.client.force_authenticate(user=self.recipient)

        response = self.client.post(f"/api/accounts/friend-requests/{request_id}/accept/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Friend.objects.filter(user=self.sender, friend=self.recipient).exists())
        self.assertTrue(Friend.objects.filter(user=self.recipient, friend=self.sender).exists())

    def test_accept_creates_mutual_friendship_and_acceptance_notification(self):
        request_response = self.create_request()
        request_id = request_response.data["id"]
        self.client.force_authenticate(user=self.recipient)

        response = self.client.post(f"/api/accounts/friend-requests/{request_id}/accept/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Friend.objects.filter(user=self.sender, friend=self.recipient).exists())
        self.assertTrue(Friend.objects.filter(user=self.recipient, friend=self.sender).exists())
        self.assertTrue(
            HandoutNotification.objects.filter(
                recipient=self.sender,
                notification_type="friend_request_accepted",
            ).exists()
        )
        request_notification = HandoutNotification.objects.get(
            recipient=self.recipient,
            notification_type="friend_request",
        )
        self.assertTrue(request_notification.is_read)

    def test_decline_and_cancel_do_not_send_notifications_and_enforce_cooldown(self):
        request_id = self.create_request().data["id"]
        self.client.force_authenticate(user=self.recipient)
        decline_response = self.client.post(f"/api/accounts/friend-requests/{request_id}/decline/")
        self.assertEqual(decline_response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            HandoutNotification.objects.filter(
                recipient=self.sender,
                notification_type="friend_request_declined",
            ).exists()
        )

        self.client.force_authenticate(user=self.sender)
        cooldown_response = self.create_request()
        self.assertEqual(cooldown_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("retry_after", cooldown_response.data)

        declined = FriendRequest.objects.get(pk=request_id)
        declined.responded_at = timezone.now() - timedelta(hours=25)
        declined.save(update_fields=["responded_at"])
        second_request = self.create_request()
        self.assertEqual(second_request.status_code, status.HTTP_201_CREATED)
        cancel_response = self.client.post(f"/api/accounts/friend-requests/{second_request.data['id']}/cancel/")
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        cancelled_cooldown_response = self.create_request()
        self.assertEqual(cancelled_cooldown_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reverse_request_auto_accepts(self):
        self.sender.trpg_introduction_sheet = public_profile()
        self.sender.save(update_fields=["trpg_introduction_sheet"])
        original_id = self.create_request().data["id"]
        self.client.force_authenticate(user=self.recipient)

        response = self.client.post(
            "/api/accounts/friend-requests/",
            {"recipient_id": self.sender.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], original_id)
        self.assertEqual(response.data["status"], FriendRequest.Status.ACCEPTED)
        self.assertTrue(Friend.objects.filter(user=self.sender, friend=self.recipient).exists())
        self.assertTrue(Friend.objects.filter(user=self.recipient, friend=self.sender).exists())

    def test_database_constraint_blocks_a_second_pending_request_for_the_same_pair(self):
        FriendRequest.objects.create(sender=self.sender, recipient=self.recipient)

        with self.assertRaises(IntegrityError), transaction.atomic():
            FriendRequest.objects.create(sender=self.recipient, recipient=self.sender)

        self.assertEqual(FriendRequest.objects.filter(status=FriendRequest.Status.PENDING).count(), 1)

    def test_only_recipient_can_accept_and_only_sender_can_cancel(self):
        request_id = self.create_request().data["id"]
        self.client.force_authenticate(user=self.other)

        accept_response = self.client.post(f"/api/accounts/friend-requests/{request_id}/accept/")
        cancel_response = self.client.post(f"/api/accounts/friend-requests/{request_id}/cancel/")

        self.assertEqual(accept_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(cancel_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_request_lists_are_limited_by_direction(self):
        outgoing_id = self.create_request().data["id"]
        self.sender.trpg_introduction_sheet = public_profile()
        self.sender.save(update_fields=["trpg_introduction_sheet"])
        incoming_sender = User.objects.create_user(username="incoming_sender")
        incoming = FriendRequest.objects.create(sender=incoming_sender, recipient=self.sender)

        incoming_response = self.client.get("/api/accounts/friend-requests/", {"direction": "incoming"})
        outgoing_response = self.client.get("/api/accounts/friend-requests/", {"direction": "outgoing"})

        self.assertEqual([item["id"] for item in incoming_response.data], [incoming.id])
        self.assertEqual([item["id"] for item in outgoing_response.data], [outgoing_id])

    def test_disabled_notifications_do_not_prevent_request_creation(self):
        UserNotificationPreferences.objects.create(
            user=self.recipient,
            friend_notifications_enabled=False,
        )

        response = self.create_request()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FriendRequest.objects.filter(sender=self.sender, recipient=self.recipient).exists())
        self.assertFalse(
            HandoutNotification.objects.filter(
                recipient=self.recipient,
                notification_type="friend_request",
            ).exists()
        )

    def test_legacy_add_endpoint_creates_request_and_rejects_private_user(self):
        response = self.client.post(
            "/api/accounts/friends/add/",
            {"username": self.recipient.username},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FriendRequest.objects.filter(sender=self.sender, recipient=self.recipient).exists())
        self.assertFalse(Friend.objects.filter(user=self.sender, friend=self.recipient).exists())

        private_user = User.objects.create_user(username="private-legacy")
        private_response = self.client.post(
            "/api/accounts/friends/add/",
            {"username": private_user.username},
            format="json",
        )
        self.assertEqual(private_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_direct_friend_creation_endpoint_is_disabled(self):
        response = self.client.post(
            "/api/accounts/friends/",
            {"friend": self.recipient.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(Friend.objects.exists())

    def test_repeated_accept_keeps_exactly_two_friend_rows(self):
        request_id = self.create_request().data["id"]
        self.client.force_authenticate(user=self.recipient)

        first_response = self.client.post(f"/api/accounts/friend-requests/{request_id}/accept/")
        second_response = self.client.post(f"/api/accounts/friend-requests/{request_id}/accept/")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Friend.objects.count(), 2)

    def test_unfriend_removes_both_directions(self):
        forward = Friend.objects.create(user=self.sender, friend=self.recipient)
        Friend.objects.create(user=self.recipient, friend=self.sender)

        response = self.client.delete(f"/api/accounts/friends/{forward.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Friend.objects.filter(
                user__in=[self.sender, self.recipient],
                friend__in=[self.sender, self.recipient],
            ).exists()
        )

    def test_friend_management_view_contains_request_controls(self):
        self.client.force_login(self.sender)
        response = self.client.get("/api/accounts/groups/view/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "friendSearchInput")
        self.assertContains(response, "incomingFriendRequests")
        self.assertContains(response, "outgoingFriendRequests")
        self.assertContains(response, "リクエストを送る")
