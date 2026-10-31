from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership


class GroupCreationAtomicityTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="atomic_group_owner")
        self.client.force_authenticate(self.owner)
        self.client.raise_request_exception = False

    def test_membership_failure_rolls_back_group_and_allows_a_clean_retry(self):
        data = {"name": "作成失敗から再試行するグループ", "visibility": "private"}
        with patch(
            "accounts.views.group_views.GroupMembership.objects.create",
            side_effect=RuntimeError("synthetic creator membership failure"),
        ):
            response = self.client.post("/api/accounts/groups/", data, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Group.objects.filter(name=data["name"]).exists())

        response = self.client.post("/api/accounts/groups/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Group.objects.filter(name=data["name"]).count(), 1)
        self.assertTrue(
            GroupMembership.objects.filter(group_id=response.data["id"], user=self.owner, role="admin").exists()
        )

    def test_successful_create_retains_creator_admin_membership(self):
        response = self.client.post(
            "/api/accounts/groups/", {"name": "正常に作成するグループ", "visibility": "private"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        group = Group.objects.get(pk=response.data["id"])
        self.assertEqual(group.created_by_id, self.owner.pk)
        self.assertEqual(GroupMembership.objects.filter(group=group).count(), 1)
        self.assertTrue(GroupMembership.objects.filter(group=group, user=self.owner, role="admin").exists())
