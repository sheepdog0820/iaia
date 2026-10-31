"""Public F02 API contract with synthetic ordinary accounts."""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.billing_deletion import BillingDeletionBlocked, delete_account_after_billing_check
from accounts.group_ownership import accept_transfer, start_transfer
from accounts.models import Group, GroupMembership, PremiumSubscription
from schedules.models import TRPGSession
from schedules.serializers import SessionSeriesCreateSerializer

User = get_user_model()


class GroupOwnershipAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="ownership_api_owner", nickname="所有者")
        self.target = User.objects.create_user(username="ownership_api_target", nickname="移譲先")
        self.admin = User.objects.create_user(username="ownership_api_admin")
        self.outsider = User.objects.create_user(username="ownership_api_outsider")
        self.group = Group.objects.create(name="合成の非公開グループ", created_by=self.owner)
        for user, role in ((self.owner, "admin"), (self.target, "member"), (self.admin, "admin")):
            GroupMembership.objects.create(group=self.group, user=user, role=role)
        self.path = f"/api/accounts/groups/{self.group.pk}/"
        self.client.force_authenticate(self.owner)

    def test_start_accept_and_group_owner_are_separate_from_creator_history(self):
        response = self.client.post(
            self.path + "ownership-transfer/", {"target_user_id": self.target.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        transfer_id = response.data["transfer"]["id"]
        self.client.force_authenticate(self.target)
        response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["transfer"]["id"], transfer_id)
        response = self.client.post(
            self.path + "ownership-transfer/accept/", {"request_id": transfer_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(self.path)
        self.assertEqual(detail.data["owner"], self.target.pk)
        self.assertEqual(detail.data["created_by"], self.owner.pk)
        self.assertEqual(detail.data["owner_name"], "移譲先")

    def test_only_owner_and_target_see_pending_request_and_consent(self):
        transfer = start_transfer(self.group.pk, self.owner, self.target.pk)
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["transfer"])
        for action in ("accept", "cancel", "decline"):
            response = self.client.post(
                self.path + f"ownership-transfer/{action}/", {"request_id": transfer.pk}, format="json"
            )
            self.assertEqual(response.status_code, 403 if action == "cancel" else 404)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.path + "ownership-transfer/").status_code, 404)

    def test_unrelated_member_and_public_visitor_cannot_probe_request_existence(self):
        transfer = start_transfer(self.group.pk, self.owner, self.target.pk)
        self.group.visibility = "public"
        self.group.save(update_fields=["visibility"])
        for user in (self.admin, self.outsider):
            self.client.force_authenticate(user)
            for action in ("accept", "decline", "cancel"):
                responses = [
                    self.client.post(self.path + f"ownership-transfer/{action}/", {"request_id": value}, format="json")
                    for value in (transfer.pk, transfer.pk + 1000)
                ]
                with self.subTest(user=user.pk, action=action):
                    self.assertEqual(responses[0].status_code, responses[1].status_code)
                    self.assertEqual(responses[0].data, responses[1].data)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_invalid_json_and_ids_are_rejected_without_creating_request(self):
        for body in (
            [],
            True,
            {},
            {"target_user_id": True},
            {"target_user_id": 0},
            {"target_user_id": 1.2},
            {"target_user_id": "１"},
        ):
            with self.subTest(body=body):
                self.assertEqual(
                    self.client.post(self.path + "ownership-transfer/", body, format="json").status_code, 400
                )

    def test_decline_and_cancel_use_request_id_and_never_change_owner(self):
        transfer = start_transfer(self.group.pk, self.owner, self.target.pk)
        response = self.client.post(
            self.path + "ownership-transfer/cancel/", {"request_id": transfer.pk}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        transfer = start_transfer(self.group.pk, self.owner, self.target.pk)
        self.client.force_authenticate(self.target)
        response = self.client.post(
            self.path + "ownership-transfer/decline/", {"request_id": transfer.pk}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_owner_is_read_only_and_former_creator_display_handles_deleted_user(self):
        response = self.client.patch(
            self.path, {"owner": self.outsider.pk, "created_by": self.outsider.pk}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)
        accept_transfer(self.group.pk, self.target, start_transfer(self.group.pk, self.owner, self.target.pk).pk)
        self.owner.delete()
        self.client.force_authenticate(self.target)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["created_by"])
        self.assertEqual(response.data["created_by_name"], "退会済みユーザー")

    def test_former_creator_can_leave_but_current_owner_cannot_leave_demote_or_be_removed(self):
        accept_transfer(self.group.pk, self.target, start_transfer(self.group.pk, self.owner, self.target.pk).pk)
        self.assertEqual(self.client.post(self.path + "leave/").status_code, 200)
        self.client.force_authenticate(self.target)
        self.assertEqual(self.client.post(self.path + "leave/").status_code, 400)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.path + "set_member_role/", {"user_id": self.target.pk, "role": "member"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.delete(self.path + "remove_member/", {"user_id": self.target.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_owned_group_blocks_account_deletion_before_any_stripe_call(self):
        PremiumSubscription.objects.create(
            user=self.owner, stripe_customer_id="cus_synthetic_owner", subscription_status="canceled"
        )
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            with self.assertRaises(BillingDeletionBlocked) as caught:
                delete_account_after_billing_check(self.owner)
        self.assertIn("所有", str(caught.exception))
        stripe.assert_not_called()
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())

    def test_owner_account_delete_page_redirects_to_group_resolution_before_stripe(self):
        self.client.force_authenticate(user=None)
        self.client.force_login(self.owner)
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            response = self.client.post(reverse("account_delete"), {"confirm": "DELETE"})
        self.assertRedirects(response, reverse("groups_view"), fetch_redirect_response=False)
        stripe.assert_not_called()
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())
        self.assertFalse(PremiumSubscription.objects.filter(user=self.owner).exists())

    def test_stale_deleted_account_identity_is_refused_without_billing_side_effects(self):
        stale = User.objects.get(pk=self.outsider.pk)
        self.outsider.delete()
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            with self.assertRaises(BillingDeletionBlocked):
                delete_account_after_billing_check(stale)
        stripe.assert_not_called()
        self.assertFalse(PremiumSubscription.objects.filter(user_id=stale.pk).exists())

    def test_request_get_refreshes_inactive_actor_authorization(self):
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "not_found")
        self.assertNotIn("candidates", response.data)

    def test_former_creator_cannot_create_a_session_for_group_after_leaving(self):
        accept_transfer(self.group.pk, self.target, start_transfer(self.group.pk, self.owner, self.target.pk).pk)
        GroupMembership.objects.filter(group=self.group, user=self.owner).delete()
        response = self.client.post(
            "/api/schedules/sessions/", {"title": "権限のない合成セッション", "group": self.group.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        series = SessionSeriesCreateSerializer(
            data={
                "title": "退出後のシリーズ",
                "group": self.group.pk,
                "recurrence": "none",
                "start_date": "2026-11-01",
                "start_time": "12:00:00",
            },
            context={"request": SimpleNamespace(user=self.owner)},
        )
        self.assertFalse(series.is_valid())
        self.assertIn("group", series.errors)

    def test_only_owner_sees_active_member_candidates_without_private_fields(self):
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])
        response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["candidates"],
            [{"id": self.admin.pk, "name": self.admin.username, "username": self.admin.username}],
        )
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.path + "ownership-transfer/").data["candidates"], [])

    def test_database_failures_have_safe_japanese_responses_without_mutation_retry(self):
        sentinel = "synthetic-private-database-error"
        with patch("accounts.views.group_views.group_ownership.pending_transfer", side_effect=DatabaseError(sentinel)):
            response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(sentinel, str(response.data))
        self.assertIn("取得できません", response.data["error"])
        with patch(
            "accounts.views.group_views.group_ownership.start_transfer", side_effect=DatabaseError(sentinel)
        ) as start:
            response = self.client.post(
                self.path + "ownership-transfer/", {"target_user_id": self.target.pk}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(sentinel, str(response.data))
        self.assertIn("状態を確認", response.data["error"])
        start.assert_called_once()

    def test_candidates_with_duplicate_display_names_have_distinct_public_usernames(self):
        self.admin.nickname = self.target.nickname
        self.admin.save(update_fields=["nickname"])
        response = self.client.get(self.path + "ownership-transfer/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["name"] for row in response.data["candidates"]], [self.target.nickname] * 2)
        self.assertEqual(
            {row["username"] for row in response.data["candidates"]}, {self.target.username, self.admin.username}
        )
        self.assertTrue(all(set(row) == {"id", "name", "username"} for row in response.data["candidates"]))

    def test_former_creator_without_a_session_role_cannot_read_private_group_session(self):
        accept_transfer(self.group.pk, self.target, start_transfer(self.group.pk, self.owner, self.target.pk).pk)
        session = TRPGSession.objects.create(
            title="新所有者だけの非公開セッション",
            group=self.group,
            created_by=self.target,
            gm=self.target,
            visibility="private",
        )
        GroupMembership.objects.filter(group=self.group, user=self.owner).delete()
        response = self.client.get(f"/api/schedules/sessions/{session.pk}/")
        self.assertEqual(response.status_code, 404)
        from schedules.views import _visible_sessions_for

        self.assertFalse(_visible_sessions_for(self.owner).filter(pk=session.pk).exists())
