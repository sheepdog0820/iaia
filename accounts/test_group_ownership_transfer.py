"""Approved F02 ownership contract, using synthetic users and groups only."""

import importlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.billing_deletion import GroupOwnershipDeletionBlocked
from accounts.discord_views import _is_group_admin as discord_group_admin
from accounts.group_link_views import _is_group_admin as link_group_admin
from accounts.models import Group, GroupMembership, GroupOwnershipTransfer
from schedules.integration_access import visible_user_sessions
from schedules.models import TRPGSession
from schedules.participant_claims import can_review_group_claim
from schedules.session_permissions import is_group_admin

User = get_user_model()


class GroupOwnershipTransferTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="ownership_creator", nickname="元の所有者")
        self.target = User.objects.create_user(username="ownership_target", nickname="新しい所有者")
        self.admin = User.objects.create_user(username="ownership_admin")
        self.outsider = User.objects.create_user(username="ownership_outsider")
        self.group = Group.objects.create(name="所有権引継ぎの合成グループ", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")
        GroupMembership.objects.create(group=self.group, user=self.target, role="member")
        GroupMembership.objects.create(group=self.group, user=self.admin, role="admin")

    def service(self):
        return importlib.import_module("accounts.group_ownership")

    def start(self, actor=None, target=None):
        return self.service().start_transfer(self.group.pk, actor or self.owner, (target or self.target).pk)

    def accept(self, transfer, actor=None):
        return self.service().accept_transfer(self.group.pk, actor or self.target, transfer.pk)

    def test_creation_keeps_creator_history_and_sets_current_owner(self):
        self.assertEqual(self.group.owner_id, self.owner.pk)
        self.assertEqual(self.group.created_by_id, self.owner.pk)

    def test_new_owner_membership_validation_normalizes_default_role_to_admin(self):
        group = Group.objects.create(name="所有者の初期所属", created_by=self.owner)
        membership = GroupMembership(group=group, user=self.owner)
        membership.full_clean()
        self.assertEqual(membership.role, "admin")
        membership.save()
        self.assertEqual(GroupMembership.objects.get(pk=membership.pk).role, "admin")

    def test_admin_bulk_user_delete_blocks_owned_groups_before_any_billing_action(self):
        request = RequestFactory().post("/admin/")
        request.user = self.admin
        with patch("accounts.admin.delete_account_after_billing_check") as delete:
            with self.assertRaises(GroupOwnershipDeletionBlocked):
                admin.site._registry[User].delete_queryset(
                    request, User.objects.filter(pk__in=[self.owner.pk, self.outsider.pk])
                )
        delete.assert_not_called()
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.outsider.pk).exists())

    def test_stale_admin_group_save_cannot_restore_former_owner(self):
        stale = Group.objects.get(pk=self.group.pk)
        self.accept(self.start())
        request = RequestFactory().post("/admin/")
        request.user = self.admin
        stale.name = "管理画面の保存後も現在所有者を保持"
        admin.site._registry[Group].save_model(request, stale, None, True)
        current = Group.objects.get(pk=self.group.pk)
        self.assertEqual(current.owner_id, self.target.pk)
        self.assertEqual(current.created_by_id, self.owner.pk)
        self.assertEqual(current.name, stale.name)

    def test_admin_can_create_group_with_its_own_owner_membership(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:accounts_group_add"),
            {
                "name": "管理画面の新規所有グループ",
                "description": "",
                "visibility": "private",
                "created_by": "",
                "created_at_0": "2026-10-31",
                "created_at_1": "12:00:00",
                "groupmembership_set-TOTAL_FORMS": "0",
                "groupmembership_set-INITIAL_FORMS": "0",
                "groupmembership_set-MIN_NUM_FORMS": "0",
                "groupmembership_set-MAX_NUM_FORMS": "1000",
                "_save": "保存",
            },
        )
        self.assertEqual(response.status_code, 302, str(response.context["errors"]) if response.context else "")
        group = Group.objects.get(name="管理画面の新規所有グループ")
        self.assertEqual(group.owner_id, self.admin.pk)
        self.assertEqual(group.created_by_id, self.admin.pk)
        self.assertEqual(GroupMembership.objects.get(group=group, user=self.admin).role, "admin")

    def test_invalid_identity_missing_group_and_inactive_actor_make_no_request(self):
        service = self.service()
        for identifier in (True, 0, -1, 1.2, "1", 9223372036854775808):
            with self.subTest(identifier=identifier), self.assertRaises(service.OwnershipTransferError):
                service.start_transfer(self.group.pk, self.owner, identifier)
        with self.assertRaises(service.OwnershipTransferError) as missing:
            service.start_transfer(self.group.pk + 1000, self.owner, self.target.pk)
        self.assertEqual(missing.exception.code, "not_found")
        with self.assertRaises(service.OwnershipTransferError) as anonymous:
            service.start_transfer(self.group.pk, AnonymousUser(), self.target.pk)
        self.assertEqual(anonymous.exception.code, "unauthenticated")
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(service.OwnershipTransferError) as inactive:
            self.start()
        self.assertEqual(inactive.exception.code, "inactive_actor")
        self.assertFalse(GroupOwnershipTransfer.objects.exists())

    def test_expired_request_can_be_replaced_without_accepting_the_old_id(self):
        expired = self.start()
        end = timezone.now() - timedelta(seconds=1)
        type(expired).objects.filter(pk=expired.pk).update(created_at=end - timedelta(days=7), expires_at=end)
        replacement = self.start(target=self.admin)
        self.assertNotEqual(replacement.pk, expired.pk)
        self.assertFalse(type(expired).objects.filter(pk=expired.pk).exists())
        with self.assertRaises(self.service().OwnershipTransferError):
            self.accept(expired)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_accept_rejects_changed_or_disabled_current_owner(self):
        pending = self.start()
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(self.service().OwnershipTransferError) as inactive:
            self.accept(pending)
        self.assertEqual(inactive.exception.code, "invalid_owner")
        self.owner.is_active = True
        self.owner.save(update_fields=["is_active"])
        Group.objects.filter(pk=self.group.pk).update(owner=self.admin)
        with self.assertRaises(self.service().OwnershipTransferError) as changed:
            self.accept(pending)
        self.assertEqual(changed.exception.code, "changed")
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.admin.pk)

    def test_pending_is_hidden_after_target_leaves_or_is_disabled(self):
        pending = self.start()
        GroupMembership.objects.filter(group=self.group, user=self.target).delete()
        self.assertIsNone(self.service().pending_transfer(self.group.pk, self.target))
        self.assertEqual(self.service().pending_transfer(self.group.pk, self.owner).pk, pending.pk)
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])
        with self.assertRaises(self.service().OwnershipTransferError):
            self.service().pending_transfer(self.group.pk, self.target)

    def test_only_target_consent_completes_seven_day_request(self):
        transfer = self.start()
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)
        self.assertEqual(transfer.requested_by_id, self.owner.pk)
        self.assertEqual(transfer.target_id, self.target.pk)
        self.assertEqual(transfer.expires_at - transfer.created_at, timedelta(days=7))

        with self.assertRaises(self.service().OwnershipTransferError) as caught:
            self.accept(transfer, self.admin)
        self.assertEqual(caught.exception.code, "not_found")
        self.accept(transfer)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)
        self.assertEqual(self.group.created_by_id, self.owner.pk)
        for user in (self.owner, self.target):
            self.assertEqual(GroupMembership.objects.get(group=self.group, user=user).role, "admin")
        self.assertFalse(type(transfer).objects.filter(group=self.group).exists())
        with self.assertRaises(self.service().OwnershipTransferError):
            self.accept(transfer)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.target.pk)

    def test_other_admin_cannot_start_or_cancel_a_transfer(self):
        with self.assertRaises(self.service().OwnershipTransferError) as caught:
            self.start(self.admin)
        self.assertEqual(caught.exception.code, "not_owner")
        transfer = self.start()
        with self.assertRaises(self.service().OwnershipTransferError):
            self.service().cancel_transfer(self.group.pk, self.admin, transfer.pk)
        self.assertTrue(type(transfer).objects.filter(pk=transfer.pk).exists())

    def test_target_must_be_an_active_registered_member_other_than_owner(self):
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])
        for target in (self.owner, self.outsider, self.target):
            with self.subTest(target=target.pk), self.assertRaises(self.service().OwnershipTransferError):
                self.start(target=target)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_single_pending_request_cancel_decline_and_expiry_preserve_owner(self):
        transfer = self.start()
        with self.assertRaises(self.service().OwnershipTransferError) as caught:
            self.start(target=self.admin)
        self.assertEqual(caught.exception.code, "pending_exists")
        self.service().cancel_transfer(self.group.pk, self.owner, transfer.pk)
        self.assertFalse(type(transfer).objects.filter(group=self.group).exists())

        transfer = self.start()
        self.service().decline_transfer(self.group.pk, self.target, transfer.pk)
        self.assertFalse(type(transfer).objects.filter(group=self.group).exists())

        transfer = self.start()
        expired_at = timezone.now() - timedelta(seconds=1)
        type(transfer).objects.filter(pk=transfer.pk).update(
            created_at=expired_at - timedelta(days=7), expires_at=expired_at
        )
        with self.assertRaises(self.service().OwnershipTransferError) as caught:
            self.accept(transfer)
        self.assertEqual(caught.exception.code, "expired")
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)

    def test_accept_rechecks_target_membership_and_account_state(self):
        for change in ("leave", "disable"):
            with self.subTest(change=change):
                transfer = self.start()
                if change == "leave":
                    GroupMembership.objects.filter(group=self.group, user=self.target).delete()
                else:
                    self.target.is_active = False
                    self.target.save(update_fields=["is_active"])
                with self.assertRaises(self.service().OwnershipTransferError):
                    self.accept(transfer)
                self.group.refresh_from_db()
                self.assertEqual(self.group.owner_id, self.owner.pk)
                self.service().cancel_transfer(self.group.pk, self.owner, transfer.pk)
                GroupMembership.objects.get_or_create(group=self.group, user=self.target, defaults={"role": "member"})

    def test_former_creator_deletion_keeps_group_and_current_owner_deletion_is_protected(self):
        self.accept(self.start())
        self.owner.delete()
        self.group.refresh_from_db()
        self.assertIsNone(self.group.created_by_id)
        self.assertEqual(self.group.owner_id, self.target.pk)
        with self.assertRaises(ProtectedError), transaction.atomic():
            User.objects.filter(pk=self.target.pk).delete()
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())
        self.assertTrue(Group.objects.filter(pk=self.group.pk).exists())

    def test_current_owner_membership_cannot_be_demoted_or_deleted_even_in_bulk(self):
        self.accept(self.start())
        membership = GroupMembership.objects.get(group=self.group, user=self.target)
        membership.role = "member"
        with self.assertRaises(ValidationError):
            membership.save(update_fields=["role"])
        with self.assertRaises(ProtectedError), transaction.atomic():
            GroupMembership.objects.filter(pk=membership.pk).delete()
        self.assertEqual(GroupMembership.objects.get(pk=membership.pk).role, "admin")
        group_id = self.group.pk
        self.group.delete()
        self.assertFalse(Group.objects.filter(pk=group_id).exists())

    def test_owner_membership_identity_cannot_be_reassigned_by_admin_validation(self):
        other_group = Group.objects.create(name="付け替え先の合成グループ", created_by=self.outsider)
        for field, value in (("user", self.outsider), ("group", other_group)):
            membership = GroupMembership.objects.get(group=self.group, user=self.owner)
            setattr(membership, field, value)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                membership.full_clean()

    def test_owner_membership_identity_cannot_be_reassigned_during_save(self):
        other_group = Group.objects.create(name="付け替え先の合成グループ", created_by=self.outsider)
        membership_id = GroupMembership.objects.get(group=self.group, user=self.owner).pk
        for field, value in (("user", self.outsider), ("group", other_group)):
            membership = GroupMembership.objects.get(pk=membership_id)
            setattr(membership, field, value)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                membership.save(update_fields=[field])

    def test_tampered_in_memory_identity_cannot_delete_actual_owner_membership(self):
        membership = GroupMembership.objects.get(group=self.group, user=self.owner)
        membership.user = self.outsider
        with self.assertRaises(ProtectedError), transaction.atomic():
            membership.delete()
        self.assertTrue(GroupMembership.objects.filter(group=self.group, user=self.owner, role="admin").exists())

    def test_stale_membership_delete_after_explicit_group_delete_is_harmless(self):
        stale = GroupMembership.objects.get(group=self.group, user=self.owner)
        group_id = self.group.pk
        self.group.delete()
        self.assertEqual(stale.delete()[0], 0)
        self.assertFalse(Group.objects.filter(pk=group_id).exists())
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())

    def test_membership_save_to_a_deleted_group_preserves_its_original_row(self):
        destination = Group.objects.create(name="削除済みの付け替え先", created_by=self.outsider)
        destination_id = destination.pk
        destination.delete()
        member = GroupMembership.objects.get(group=self.group, user=self.target)
        member.group_id = destination_id
        with self.assertRaises(Group.DoesNotExist):
            member.save(update_fields=["group"])
        member.refresh_from_db()
        self.assertEqual(member.group_id, self.group.pk)

    def test_nested_group_delete_preview_restores_its_previous_permission_scope(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        second = Group.objects.create(name="内側の削除確認", created_by=self.outsider)
        second_owner = GroupMembership.objects.create(group=second, user=self.outsider, role="admin")
        first_owner = GroupMembership.objects.get(group=self.group, user=self.owner)
        request._iaia_explicit_group_deletion = {self.group.pk}
        admin.site._registry[Group].get_deleted_objects([second], request)
        members_admin = admin.site._registry[GroupMembership]
        self.assertEqual(request._iaia_explicit_group_deletion, {self.group.pk})
        self.assertTrue(members_admin.has_delete_permission(request, first_owner))
        self.assertFalse(members_admin.has_delete_permission(request, second_owner))
        del request._iaia_explicit_group_deletion
        self.assertFalse(members_admin.has_delete_permission(request, first_owner))

    def test_former_creator_loses_creator_based_group_privileges_after_leaving(self):
        self.accept(self.start())
        GroupMembership.objects.filter(group=self.group, user=self.owner).delete()
        self.group.refresh_from_db()
        session = TRPGSession.objects.create(
            title="新所有者の合成セッション", group=self.group, created_by=self.target, gm=self.target
        )
        self.assertFalse(is_group_admin(self.owner, session))
        self.assertFalse(can_review_group_claim(self.owner, self.group))
        self.assertFalse(discord_group_admin(self.owner, self.group))
        self.assertFalse(link_group_admin(self.owner, self.group))
        self.assertFalse(visible_user_sessions(self.owner).filter(pk=session.pk).exists())
        self.assertTrue(is_group_admin(self.target, session))

    def test_admin_cannot_edit_owner_or_creator_history(self):
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        fields = admin.site._registry[Group].get_readonly_fields(request, self.group)
        self.assertIn("owner", fields)
        self.assertIn("created_by", fields)

    def test_membership_full_clean_and_admin_deletion_protect_current_owner(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        membership = GroupMembership.objects.get(group=self.group, user=self.owner)
        membership.role = "member"
        with self.assertRaises(ValidationError):
            membership.full_clean()
        self.assertFalse(admin.site._registry[GroupMembership].has_delete_permission(request, membership))
        self.assertTrue(admin.site._registry[Group].has_delete_permission(request, self.group))

    def test_group_admin_inline_cannot_delete_owner_membership(self):
        from accounts.admin import GroupMembershipInline

        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        inline = GroupMembershipInline(Group, admin.site)
        factory = inline.get_formset(request, self.group)
        prefix = factory.get_default_prefix()
        membership = GroupMembership.objects.get(group=self.group, user=self.owner)
        data = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(membership.pk),
            f"{prefix}-0-user": str(self.owner.pk),
            f"{prefix}-0-role": "admin",
            f"{prefix}-0-joined_at_0": "2026-10-31",
            f"{prefix}-0-joined_at_1": "12:00:00",
            f"{prefix}-0-DELETE": "on",
        }
        formset = factory(data=data, instance=self.group, queryset=GroupMembership.objects.filter(pk=membership.pk))
        self.assertFalse(formset.is_valid())
        self.assertIn("所有", str(formset.non_form_errors()))

        # Django ignores a deleted form's model-validation errors. Changing its
        # user field must not disguise the owner row selected for deletion.
        data[f"{prefix}-0-user"] = str(self.outsider.pk)
        tampered = factory(data=data, instance=self.group, queryset=GroupMembership.objects.filter(pk=membership.pk))
        self.assertFalse(tampered.is_valid())
        self.assertIn("所有", str(tampered.non_form_errors()))

    def test_admin_bulk_membership_delete_refuses_owner_without_server_error(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.admin)
        membership = GroupMembership.objects.get(group=self.group, user=self.owner)
        response = self.client.post(
            reverse("admin:accounts_groupmembership_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [str(membership.pk)],
                "post": "yes",
            },
        )
        self.assertIn(response.status_code, (302, 403))
        self.assertTrue(GroupMembership.objects.filter(pk=membership.pk).exists())

    def test_admin_can_explicitly_delete_group_with_owner_membership(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.admin)
        group_id = self.group.pk
        response = self.client.post(reverse("admin:accounts_group_delete", args=[group_id]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Group.objects.filter(pk=group_id).exists())
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())

    def test_admin_can_explicitly_bulk_delete_groups_with_owner_membership(self):
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.admin)
        group_id = self.group.pk
        response = self.client.post(
            reverse("admin:accounts_group_changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [str(group_id)],
                "post": "yes",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Group.objects.filter(pk=group_id).exists())
