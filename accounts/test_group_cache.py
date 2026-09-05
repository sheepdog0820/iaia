from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership


class GroupCacheTests(APITestCase):
    def test_group_responses_with_membership_and_roles_are_not_cached(self):
        user = get_user_model().objects.create_user(username="group-cache")
        group = Group.objects.create(name="権限検証", created_by=user)
        GroupMembership.objects.create(group=group, user=user, role="admin")
        self.client.force_authenticate(user)
        responses = [
            self.client.get("/api/accounts/groups/"),
            self.client.get(f"/api/accounts/groups/{group.pk}/"),
            self.client.get(f"/api/accounts/groups/{group.pk}/members/"),
            self.client.patch(f"/api/accounts/groups/{group.pk}/", {"description": "更新"}, format="json"),
        ]
        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response.get("Cache-Control", ""))
                self.assertIn("no-cache", response["Cache-Control"])
                self.assertIn("private", response["Cache-Control"])

    def test_unauthenticated_group_response_is_not_cached(self):
        response = self.client.get("/api/accounts/groups/")
        self.assertIn(response.status_code, (401, 403))
        self.assertIn("no-store", response.get("Cache-Control", ""))
