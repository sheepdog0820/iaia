"""Real PostgreSQL row-lock tests for consent, role changes and account deletion."""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.db.backends.signals import connection_created
from django.db.models.deletion import ProtectedError
from django.test import Client, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.billing_deletion import GroupOwnershipDeletionBlocked, delete_account_after_billing_check
from accounts.group_ownership import OwnershipTransferError, accept_transfer, cancel_transfer, start_transfer
from accounts.models import Group, GroupMembership, GroupOwnershipTransfer, PremiumSubscription
from accounts.views.group_views import GroupViewSet

User = get_user_model()


class GroupOwnershipConcurrencyTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL ownership row-lock verification")
        self.owner = User.objects.create_user(username="ownership_race_owner")
        self.target = User.objects.create_user(username="ownership_race_target")
        self.admin = User.objects.create_user(username="ownership_race_admin")
        self.group = Group.objects.create(name="所有権の合成並行試験", created_by=self.owner)
        for user, role in ((self.owner, "admin"), (self.target, "member"), (self.admin, "admin")):
            GroupMembership.objects.create(group=self.group, user=user, role=role)

    def worker(self, name, user_id, operation):
        ident = threading.get_ident()

        def label_connection(sender, connection, **kwargs):
            if threading.get_ident() == ident:
                connection.connection.execute("SELECT set_config('application_name', %s, false)", [name])

        connections.close_all()
        connection_created.connect(label_connection, weak=False)
        try:
            user = User.objects.get(pk=user_id)
            try:
                return operation(user)
            except OwnershipTransferError as exc:
                return {"code": exc.code}
            except GroupOwnershipDeletionBlocked:
                return {"code": "deletion_blocked"}
        finally:
            connection_created.disconnect(label_connection)
            connections.close_all()

    def wait_for_row_lock(self, name):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'", [name]
                )
                if cursor.fetchone()[0] == 1:
                    return
            time.sleep(0.03)
        self.fail("The same worker did not reach an observed PostgreSQL lock wait")

    def while_worker_blocked(self, user_id, worker, controller):
        name = "f02-" + uuid.uuid4().hex[:16]
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Group.objects.select_for_update().get(pk=self.group.pk)
                future = pool.submit(self.worker, name, user_id, worker)
                self.wait_for_row_lock(name)
                controller()
            return future.result(timeout=12)

    def test_cancel_wins_while_accept_is_waiting_for_same_group(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        result = self.while_worker_blocked(
            self.target.pk,
            lambda user: accept_transfer(self.group.pk, user, request.pk),
            lambda: cancel_transfer(self.group.pk, self.owner, request.pk),
        )
        self.assertEqual(result, {"code": "not_found"})
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_target_cannot_leave_after_accept_commits_while_leave_was_waiting(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)

        def leave(user):
            client = APIClient()
            client.force_authenticate(user)
            return client.post(f"/api/accounts/groups/{self.group.pk}/leave/").status_code

        status = self.while_worker_blocked(
            self.target.pk, leave, lambda: accept_transfer(self.group.pk, self.target, request.pk)
        )
        self.assertEqual(status, 400)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.target).role, "admin")

    def _role_or_remove_after_accept(self, remove):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)

        def change(user):
            client = APIClient()
            client.force_authenticate(user)
            url = f"/api/accounts/groups/{self.group.pk}/"
            if remove:
                return client.delete(url + "remove_member/", {"user_id": self.target.pk}, format="json").status_code
            return client.post(
                url + "set_member_role/", {"user_id": self.target.pk, "role": "member"}, format="json"
            ).status_code

        status = self.while_worker_blocked(
            self.admin.pk, change, lambda: accept_transfer(self.group.pk, self.target, request.pk)
        )
        self.assertEqual(status, 400)
        self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.target).role, "admin")

    def test_new_owner_cannot_be_demoted_by_an_already_waiting_request(self):
        self._role_or_remove_after_accept(False)

    def test_new_owner_cannot_be_removed_by_an_already_waiting_request(self):
        self._role_or_remove_after_accept(True)

    def test_membership_reassignment_loaded_before_accept_cannot_remove_new_owner(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        outsider = User.objects.create_user(username="ownership_race_new_identity")

        def reassign(user):
            membership = GroupMembership.objects.get(group=self.group, user=self.target)
            membership.user = outsider
            try:
                membership.save(update_fields=["user"])
            except ValidationError:
                return "protected"
            return "unexpected_reassignment"

        outcome = self.while_worker_blocked(
            self.admin.pk, reassign, lambda: accept_transfer(self.group.pk, self.target, request.pk)
        )
        self.assertEqual(outcome, "protected")
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.target).role, "admin")
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=outsider).exists())

    def test_already_waiting_admin_mutations_recheck_revoked_admin_rights(self):
        original_name = self.group.name
        for action in ("patch", "destroy", "set_role", "remove"):
            GroupMembership.objects.filter(group=self.group, user=self.admin).update(role="admin")

            def mutate(user):
                client = APIClient()
                client.force_authenticate(user)
                url = f"/api/accounts/groups/{self.group.pk}/"
                if action == "patch":
                    return client.patch(url, {"name": "許可されない更新"}, format="json").status_code
                if action == "destroy":
                    return client.delete(url).status_code
                if action == "set_role":
                    return client.post(
                        url + "set_member_role/", {"user_id": self.target.pk, "role": "admin"}, format="json"
                    ).status_code
                return client.delete(url + "remove_member/", {"user_id": self.target.pk}, format="json").status_code

            def revoke():
                membership = GroupMembership.objects.get(group=self.group, user=self.admin)
                membership.role = "member"
                membership.save(update_fields=["role"])

            with self.subTest(action=action):
                self.assertEqual(self.while_worker_blocked(self.admin.pk, mutate, revoke), 403)
                self.group.refresh_from_db()
                self.assertEqual(self.group.name, original_name)
                self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.target).role, "member")

    def test_waiting_stale_membership_delete_does_not_remove_owner_of_its_new_group(self):
        other_owner = User.objects.create_user(username="ownership_other_group_owner")
        other_group = Group.objects.create(name="移動先の合成グループ", created_by=other_owner)
        GroupMembership.objects.create(group=other_group, user=other_owner, role="admin")

        def delete_stale(user):
            member = GroupMembership.objects.get(group=self.group, user=self.target)
            try:
                member.delete()
            except ProtectedError:
                return "protected"
            return "unexpected_deletion"

        def move_and_transfer():
            member = GroupMembership.objects.get(group=self.group, user=self.target)
            member.group = other_group
            member.save(update_fields=["group"])
            pending = start_transfer(other_group.pk, other_owner, self.target.pk)
            accept_transfer(other_group.pk, self.target, pending.pk)

        result = self.while_worker_blocked(self.admin.pk, delete_stale, move_and_transfer)
        self.assertEqual(result, "protected")
        other_group.refresh_from_db()
        self.assertEqual(other_group.owner_id, self.target.pk)
        self.assertEqual(GroupMembership.objects.get(group=other_group, user=self.target).role, "admin")

    def test_duplicate_membership_delete_after_another_delete_is_harmless(self):
        def delete_stale(user):
            return GroupMembership.objects.get(group=self.group, user=self.target).delete()[0]

        def remove_first():
            GroupMembership.objects.get(group=self.group, user=self.target).delete()

        result = self.while_worker_blocked(self.admin.pk, delete_stale, remove_first)
        self.assertEqual(result, 0)
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.target).exists())
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_membership_created_after_deletion_snapshot_stops_before_stripe(self):
        PremiumSubscription.objects.create(
            user=self.target, stripe_customer_id="cus_synthetic_group_change", subscription_status="canceled"
        )

        def join_another_group():
            group = Group.objects.create(name="退会待機中に参加したグループ", created_by=self.admin)
            GroupMembership.objects.create(group=group, user=self.target)

        with patch("accounts.billing_deletion.get_stripe") as stripe:
            result = self.while_worker_blocked(
                self.target.pk, lambda user: delete_account_after_billing_check(user), join_another_group
            )
        self.assertEqual(result, {"code": "deletion_blocked"})
        stripe.assert_not_called()
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())
        self.assertEqual(GroupMembership.objects.filter(user=self.target).count(), 2)

    def _site_admin_member_request_after_accept(self, operation):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        membership_id = GroupMembership.objects.get(group=self.group, user=self.target).pk
        pending = start_transfer(self.group.pk, self.owner, self.target.pk)

        def admin_request(user):
            client = Client()
            client.force_login(user)
            if operation == "change":
                return client.post(
                    reverse("admin:accounts_groupmembership_change", args=[membership_id]),
                    {
                        "group": self.group.pk,
                        "user": self.target.pk,
                        "role": "member",
                        "joined_at_0": "2026-10-31",
                        "joined_at_1": "12:00:00",
                        "_save": "保存",
                    },
                ).status_code
            if operation == "delete":
                return client.post(
                    reverse("admin:accounts_groupmembership_delete", args=[membership_id]), {"post": "yes"}
                ).status_code
            return client.post(
                reverse("admin:accounts_groupmembership_changelist"),
                {
                    "action": "delete_selected",
                    "_selected_action": [str(membership_id)],
                    "post": "yes",
                },
            ).status_code

        status = self.while_worker_blocked(
            self.admin.pk, admin_request, lambda: accept_transfer(self.group.pk, self.target, pending.pk)
        )
        self.assertEqual(status, 302)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(GroupMembership.objects.get(pk=membership_id).role, "admin")

    def test_site_admin_member_change_waiting_for_accept_preserves_owner(self):
        self._site_admin_member_request_after_accept("change")

    def test_site_admin_member_delete_waiting_for_accept_preserves_owner(self):
        self._site_admin_member_request_after_accept("delete")

    def test_site_admin_member_bulk_delete_waiting_for_accept_preserves_owner(self):
        self._site_admin_member_request_after_accept("bulk")

    def test_waiting_role_save_does_not_mutate_a_membership_moved_to_another_group(self):
        other_owner = User.objects.create_user(username="ownership_moved_role_owner")
        other = Group.objects.create(name="権限更新中の別グループ", created_by=other_owner)

        def save_stale(user):
            membership = GroupMembership.objects.get(group=self.group, user=self.target)
            membership.role = "admin"
            try:
                membership.save(update_fields=["role"])
            except ValidationError:
                return "changed"
            return "unexpected_promotion"

        def move():
            membership = GroupMembership.objects.get(group=self.group, user=self.target)
            membership.group = other
            membership.save(update_fields=["group"])

        self.assertEqual(self.while_worker_blocked(self.admin.pk, save_stale, move), "changed")
        self.assertEqual(GroupMembership.objects.get(group=other, user=self.target).role, "member")

    def test_site_admin_group_inline_delete_waiting_for_accept_rolls_back_safely(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        pending = start_transfer(self.group.pk, self.owner, self.target.pk)
        members = list(GroupMembership.objects.filter(group=self.group).order_by("pk"))
        data = {
            "name": "拒否時には保存しない名前",
            "description": "",
            "visibility": "private",
            "created_at_0": "2026-10-31",
            "created_at_1": "12:00:00",
            "_save": "保存",
            "groupmembership_set-TOTAL_FORMS": str(len(members)),
            "groupmembership_set-INITIAL_FORMS": str(len(members)),
            "groupmembership_set-MIN_NUM_FORMS": "0",
            "groupmembership_set-MAX_NUM_FORMS": "1000",
        }
        for index, member in enumerate(members):
            prefix = f"groupmembership_set-{index}-"
            data.update(
                {
                    prefix + "id": str(member.pk),
                    prefix + "user": str(member.user_id),
                    prefix + "role": member.role,
                    prefix + "joined_at_0": "2026-10-31",
                    prefix + "joined_at_1": "12:00:00",
                }
            )
            if member.user_id == self.target.pk:
                data[prefix + "DELETE"] = "on"

        def change_group(user):
            client = Client()
            client.force_login(user)
            return client.post(reverse("admin:accounts_group_change", args=[self.group.pk]), data).status_code

        original_name = self.group.name
        status = self.while_worker_blocked(
            self.admin.pk, change_group, lambda: accept_transfer(self.group.pk, self.target, pending.pk)
        )
        self.assertEqual(status, 302)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, original_name)
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.target).role, "admin")

    def test_target_deletion_after_accept_is_blocked_before_stripe(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            result = self.while_worker_blocked(
                self.target.pk,
                delete_account_after_billing_check,
                lambda: accept_transfer(self.group.pk, self.target, request.pk),
            )
        self.assertEqual(result, {"code": "deletion_blocked"})
        stripe.assert_not_called()
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_target_deletion_before_accept_keeps_original_owner(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        target_id = self.target.pk
        with patch("accounts.billing_deletion.get_stripe") as stripe:
            result = self.while_worker_blocked(
                target_id,
                lambda user: accept_transfer(self.group.pk, user, request.pk),
                lambda: delete_account_after_billing_check(self.target),
            )
        # Authorization is refreshed before looking up a private request. The
        # already deleted actor cannot learn whether its old request remains.
        self.assertEqual(result, {"code": "inactive_actor"})
        stripe.assert_not_called()
        self.assertFalse(User.objects.filter(pk=target_id).exists())
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_disabled_target_is_rechecked_after_group_lock_wait(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        result = self.while_worker_blocked(
            self.target.pk,
            lambda user: accept_transfer(self.group.pk, user, request.pk),
            lambda: User.objects.filter(pk=self.target.pk).update(is_active=False),
        )
        self.assertEqual(result, {"code": "inactive_actor"})
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_two_starts_create_only_one_pending_request(self):
        barrier = threading.Barrier(2)

        def begin(user, target_id):
            barrier.wait(timeout=5)
            start_transfer(self.group.pk, user, target_id)
            return {"code": "created"}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    self.worker,
                    "f02-start-" + uuid.uuid4().hex[:8],
                    self.owner.pk,
                    lambda user, target=target: begin(user, target),
                )
                for target in (self.target.pk, self.admin.pk)
            ]
            outcomes = [future.result(timeout=12)["code"] for future in futures]
        self.assertCountEqual(outcomes, ["created", "pending_exists"])
        self.assertEqual(GroupOwnershipTransfer.objects.filter(group=self.group).count(), 1)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_duplicate_accept_changes_owner_once(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        barrier = threading.Barrier(2)

        def accept(user):
            barrier.wait(timeout=5)
            accept_transfer(self.group.pk, user, request.pk)
            return {"code": "accepted"}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self.worker, "f02-accept-" + uuid.uuid4().hex[:8], self.target.pk, accept) for _ in range(2)
            ]
            outcomes = [future.result(timeout=12)["code"] for future in futures]
        self.assertCountEqual(outcomes, ["accepted", "not_found"])
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertFalse(GroupOwnershipTransfer.objects.filter(group=self.group).exists())

    def test_group_name_patch_loaded_before_accept_does_not_restore_old_owner(self):
        request = start_transfer(self.group.pk, self.owner, self.target.pk)
        loaded = threading.Event()
        resume = threading.Event()
        original = GroupViewSet.perform_update

        def paused(view, serializer):
            loaded.set()
            if not resume.wait(timeout=8):
                raise RuntimeError("Synthetic stale PATCH coordination deadline")
            return original(view, serializer)

        def update(user):
            client = APIClient()
            client.force_authenticate(user)
            return client.patch(
                f"/api/accounts/groups/{self.group.pk}/", {"name": "移譲後も保持する名称"}, format="json"
            ).status_code

        with patch.object(GroupViewSet, "perform_update", paused), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.worker, "f02-patch-" + uuid.uuid4().hex[:8], self.owner.pk, update)
            try:
                self.assertTrue(loaded.wait(timeout=8))
                accept_transfer(self.group.pk, self.target, request.pk)
            finally:
                resume.set()
            self.assertEqual(future.result(timeout=12), 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(self.group.created_by_id, self.owner.pk)
        self.assertEqual(self.group.name, "移譲後も保持する名称")
