from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Lock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Group, GroupInviteLink, GroupMembership


@skipUnlessDBFeature("has_select_for_update")
class GroupInviteConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="invite_owner")
        self.invitee = get_user_model().objects.create_user(username="invite_joiner")
        self.group = Group.objects.create(name="招待競合テスト", created_by=self.owner)
        GroupMembership.objects.create(group=self.group, user=self.owner, role="admin")

    def join_concurrently(self, tokens, users):
        barrier = Barrier(2)
        guard = Lock()
        checks = 0
        original_exists = QuerySet.exists

        def synchronized_exists(queryset):
            nonlocal checks
            result = original_exists(queryset)
            if queryset.model is GroupMembership:
                with guard:
                    checks += 1
                    wait = checks <= 2
                if wait:
                    # Both requests observe non-membership before either obtains the lock.
                    barrier.wait(timeout=15)
            return result

        def join(index):
            close_old_connections()
            try:
                client = APIClient()
                client.raise_request_exception = False
                client.force_authenticate(user=users[index])
                return client.post(f"/api/group-invitations/{tokens[index]}/join/").status_code
            finally:
                close_old_connections()

        with patch.object(QuerySet, "exists", synchronized_exists):
            with ThreadPoolExecutor(max_workers=2) as executor:
                return list(executor.map(join, range(2)))

    def test_same_user_retry_with_last_use_is_successful(self):
        link, token = GroupInviteLink.issue(
            group=self.group, created_by=self.owner, expires_at=timezone.now() + timedelta(hours=1), max_uses=1
        )
        results = self.join_concurrently([token, token], [self.invitee, self.invitee])
        self.assertEqual(sorted(results), [200, 201])
        link.refresh_from_db()
        self.assertEqual(link.use_count, 1)
        self.assertEqual(GroupMembership.objects.filter(group=self.group, user=self.invitee).count(), 1)

    def test_same_user_retry_with_spare_uses_is_successful(self):
        link, token = GroupInviteLink.issue(
            group=self.group, created_by=self.owner, expires_at=timezone.now() + timedelta(hours=1), max_uses=2
        )
        results = self.join_concurrently([token, token], [self.invitee, self.invitee])
        self.assertEqual(sorted(results), [200, 201])
        link.refresh_from_db()
        self.assertEqual(link.use_count, 1)
        self.assertEqual(GroupMembership.objects.filter(group=self.group, user=self.invitee).count(), 1)

    def test_different_users_cannot_share_last_use(self):
        other = get_user_model().objects.create_user(username="invite_other")
        link, token = GroupInviteLink.issue(
            group=self.group, created_by=self.owner, expires_at=timezone.now() + timedelta(hours=1), max_uses=1
        )
        results = self.join_concurrently([token, token], [self.invitee, other])
        self.assertEqual(sorted(results), [201, 410])
        link.refresh_from_db()
        self.assertEqual(link.use_count, 1)
        self.assertEqual(GroupMembership.objects.filter(group=self.group, role="member").count(), 1)
