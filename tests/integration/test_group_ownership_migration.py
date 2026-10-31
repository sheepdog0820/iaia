"""Data-bearing ownership initialization and guarded reversal on isolated PG."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.group_ownership import accept_transfer, start_transfer
from accounts.models import Group, GroupMembership, GroupOwnershipTransfer


class GroupOwnershipMigrationTests(TransactionTestCase):
    old = [("accounts", "0068_merge_skill_bonus_into_other")]
    new = [("accounts", "0069_group_ownership_transfer")]

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL ownership migration/data constraints")
        executor = MigrationExecutor(connection)
        self.latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.latest))
        executor.migrate(self.old)
        self.apps = executor.loader.project_state(self.old).apps
        old_user = self.apps.get_model("accounts", "CustomUser")
        self.creator_id = old_user.objects.create(username="ownership_migration_creator").pk
        self.target_id = old_user.objects.create(username="ownership_migration_target").pk
        self.group_id = (
            self.apps.get_model("accounts", "Group")
            .objects.create(
                name="作成履歴を保つ合成グループ",
                description="保存対象の説明",
                visibility="private",
                created_by_id=self.creator_id,
            )
            .pk
        )

    def forward(self):
        MigrationExecutor(connection).migrate(self.new)
        return Group.objects.get(pk=self.group_id)

    def transfer(self):
        self.forward()
        users = get_user_model().objects
        creator, target = users.get(pk=self.creator_id), users.get(pk=self.target_id)
        GroupMembership.objects.create(group_id=self.group_id, user=target, role="member")
        request = start_transfer(self.group_id, creator, target.pk)
        accept_transfer(self.group_id, target, request.pk)
        return creator, target

    def test_initialization_fills_owner_and_missing_admin_without_changing_group_data(self):
        before = self.apps.get_model("accounts", "Group").objects.get(pk=self.group_id)
        group = self.forward()
        self.assertEqual(group.owner_id, self.creator_id)
        self.assertEqual(group.created_by_id, self.creator_id)
        for field in ("name", "description", "visibility", "created_at", "updated_at"):
            self.assertEqual(getattr(group, field), getattr(before, field))
        self.assertEqual(GroupMembership.objects.get(group=group, user_id=self.creator_id).role, "admin")
        self.assertFalse(GroupOwnershipTransfer.objects.exists())

    def test_initialization_promotes_creator_and_preserves_other_members_and_join_dates(self):
        membership = self.apps.get_model("accounts", "GroupMembership")
        old_owner = membership.objects.create(group_id=self.group_id, user_id=self.creator_id, role="member")
        old_member = membership.objects.create(group_id=self.group_id, user_id=self.target_id, role="member")
        self.forward()
        owner = GroupMembership.objects.get(pk=old_owner.pk)
        member = GroupMembership.objects.get(pk=old_member.pk)
        self.assertEqual(owner.role, "admin")
        self.assertEqual(owner.joined_at, old_owner.joined_at)
        self.assertEqual(member.role, "member")
        self.assertEqual(member.joined_at, old_member.joined_at)

    def test_reversal_when_owner_equals_creator_and_no_request_preserves_roles_and_reapplies(self):
        self.forward()
        MigrationExecutor(connection).migrate(self.old)
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state(self.old).apps
        self.assertEqual(
            apps.get_model("accounts", "Group").objects.get(pk=self.group_id).created_by_id, self.creator_id
        )
        self.assertEqual(
            apps.get_model("accounts", "GroupMembership")
            .objects.get(group_id=self.group_id, user_id=self.creator_id)
            .role,
            "admin",
        )
        self.forward()
        self.assertEqual(Group.objects.get(pk=self.group_id).owner_id, self.creator_id)

    def assert_reversal_refused(self):
        with self.assertRaises(IrreversibleError):
            MigrationExecutor(connection).migrate(self.old)
        self.assertIn(self.new[0], MigrationRecorder(connection).applied_migrations())
        with connection.cursor() as cursor:
            columns = {
                column.name: column
                for column in connection.introspection.get_table_description(cursor, "accounts_group")
            }
        self.assertFalse(columns["owner_id"].null_ok)

    def test_real_transfer_refuses_reversal_without_restoring_former_owner(self):
        self.transfer()
        self.assert_reversal_refused()
        self.assertEqual(Group.objects.get(pk=self.group_id).owner_id, self.target_id)
        self.assertEqual(GroupMembership.objects.get(group_id=self.group_id, user_id=self.target_id).role, "admin")

    def test_deleted_creator_refuses_reversal_and_group_stays_with_current_owner(self):
        creator, target = self.transfer()
        creator.delete()
        self.assert_reversal_refused()
        group = Group.objects.get(pk=self.group_id)
        self.assertIsNone(group.created_by_id)
        self.assertEqual(group.owner_id, target.pk)

    def test_pending_request_refuses_reversal_without_dropping_request(self):
        self.forward()
        users = get_user_model().objects
        GroupMembership.objects.create(group_id=self.group_id, user_id=self.target_id, role="member")
        request = start_transfer(self.group_id, users.get(pk=self.creator_id), self.target_id)
        self.assert_reversal_refused()
        self.assertTrue(GroupOwnershipTransfer.objects.filter(pk=request.pk).exists())

    def test_request_constraints_enforce_unique_group_distinct_users_and_expiry(self):
        self.forward()
        now = timezone.now()
        base = {
            "group_id": self.group_id,
            "requested_by_id": self.creator_id,
            "target_id": self.target_id,
            "created_at": now,
            "expires_at": now + timedelta(days=7),
        }
        for changes in ({"target_id": self.creator_id}, {"expires_at": now}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                GroupOwnershipTransfer.objects.create(**{**base, **changes})
        GroupOwnershipTransfer.objects.create(**base)
        with self.assertRaises(IntegrityError), transaction.atomic():
            GroupOwnershipTransfer.objects.create(**base)
