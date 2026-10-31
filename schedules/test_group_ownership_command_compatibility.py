from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import Group, GroupMembership
from schedules.management.commands.reset_dev_session_data import Command as ResetCommand


class GroupOwnershipCommandCompatibilityTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="current-owner")
        self.creator = get_user_model().objects.create_user(username="former-creator")
        self.group = Group.objects.create(name="所有権移譲済みの診断用", owner=self.owner, created_by=self.creator)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")

    def test_import_audit_reports_missing_creator_without_crashing(self):
        self.creator.delete()
        out = StringIO()
        call_command(
            "audit_past_import_data", group_name=self.group.name, expected_created_by="former-creator", stdout=out
        )
        self.assertIn("グループ作成者の不一致", out.getvalue())
        self.assertIn("退会済みユーザー", out.getvalue())
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)
        self.assertIsNone(self.group.created_by_id)

    def test_development_occurrence_seed_does_not_rejoin_former_creator(self):
        missing_membership = Group.objects.create(name="作成者退会済みの所属補完", owner=self.owner, created_by=None)
        ResetCommand(stdout=StringIO())._add_occurrences_and_attendance()
        self.assertEqual(GroupMembership.objects.get(group=missing_membership, user=self.owner).role, "admin")
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.creator).exists())
        self.creator.delete()
        ResetCommand(stdout=StringIO())._add_occurrences_and_attendance()
        self.assertEqual(GroupMembership.objects.get(group=self.group, user=self.owner).role, "admin")

    def test_import_repair_changes_history_without_reassigning_current_owner(self):
        out = StringIO()
        call_command("repair_past_import_data", group_name=self.group.name, created_by=self.owner.username, stdout=out)
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)
        self.assertEqual(self.group.created_by_id, self.owner.pk)

    @override_settings(DEBUG=True)
    def test_reset_preserves_group_transferred_from_seed_user(self):
        self.creator.username = "flow_gm"
        self.creator.save(update_fields=["username"])
        with (
            patch("schedules.management.commands.reset_dev_session_data.call_command"),
            patch.object(ResetCommand, "_ensure_admin"),
        ):
            call_command("reset_dev_session_data", force=True, skip_flow=True, stdout=StringIO())
        self.group.refresh_from_db()
        self.assertEqual(self.group.owner_id, self.owner.pk)
        self.assertIsNone(self.group.created_by_id)
