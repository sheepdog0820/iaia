from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import Group, GroupMembership


class GroupMemberInputValidationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(username="member_input_owner")
        cls.member = user_model.objects.create_user(username="member_input_target")
        cls.group = Group.objects.create(name="入力検証グループ", created_by=cls.owner, visibility="private")
        GroupMembership.objects.create(group=cls.group, user=cls.owner, role="admin")
        GroupMembership.objects.create(group=cls.group, user=cls.member, role="member")

    def setUp(self):
        self.client.force_authenticate(self.owner)
        self.client.raise_request_exception = False

    def request_action(self, action, data):
        method = self.client.post if action == "set_member_role" else self.client.delete
        return method(f"/api/accounts/groups/{self.group.pk}/{action}/", data=data, format="json")

    def assert_target_unchanged(self):
        self.assertTrue(GroupMembership.objects.filter(group=self.group, user=self.member, role="member").exists())

    def test_fractional_id_cannot_change_another_members_role(self):
        response = self.request_action("set_member_role", {"user_id": self.member.pk + 0.5, "role": "admin"})
        self.assertEqual(response.status_code, 400)
        self.assert_target_unchanged()

    def test_fractional_id_cannot_remove_another_member(self):
        response = self.request_action("remove_member", {"user_id": self.member.pk + 0.5})
        self.assertEqual(response.status_code, 400)
        self.assert_target_unchanged()

    def test_malformed_member_id_returns_client_error(self):
        response = self.request_action("set_member_role", {"user_id": "invalid-id", "role": "admin"})
        self.assertEqual(response.status_code, 400)
        self.assert_target_unchanged()

    def test_invalid_ids_never_mutate_or_fall_back_to_username(self):
        invalid_ids = (
            None,
            "",
            False,
            True,
            0,
            -1,
            0.0,
            float(self.member.pk),
            "1.0",
            "invalid",
            [],
            {},
            "９",
            "9" * 5000,
        )
        for action in ("set_member_role", "remove_member"):
            for value in invalid_ids:
                with self.subTest(action=action, value_type=type(value).__name__, value_prefix=str(value)[:20]):
                    data = {"user_id": value, "role": "admin", "username": self.member.username}
                    response = self.request_action(action, data)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"], "ユーザーIDは正の整数で指定してください")
                    self.assert_target_unchanged()

    def test_non_object_bodies_are_client_errors(self):
        for action in ("set_member_role", "remove_member"):
            for data in ([], [self.member.pk], "invalid", 3):
                with self.subTest(action=action, body_type=type(data).__name__):
                    response = self.request_action(action, data)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"], "入力内容はオブジェクト形式で指定してください")
                    self.assert_target_unchanged()

    def test_integer_and_digit_string_ids_keep_existing_operations(self):
        for value in (self.member.pk, str(self.member.pk)):
            with self.subTest(value_type=type(value).__name__):
                response = self.request_action("set_member_role", {"user_id": value, "role": "admin"})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    GroupMembership.objects.filter(group=self.group, user=self.member, role="admin").exists()
                )
                response = self.request_action("set_member_role", {"user_id": value, "role": "member"})
                self.assertEqual(response.status_code, 200)
                response = self.request_action("remove_member", {"user_id": value})
                self.assertEqual(response.status_code, 200)
                self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.member).exists())
                GroupMembership.objects.create(group=self.group, user=self.member, role="member")

    def test_username_removal_requires_string_and_preserves_valid_lookup(self):
        for username in (None, "", False, self.member.pk, [], {}):
            with self.subTest(value_type=type(username).__name__):
                response = self.request_action("remove_member", {"username": username})
                self.assertEqual(response.status_code, 400)
                self.assert_target_unchanged()
        response = self.request_action("remove_member", {"username": self.member.username})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GroupMembership.objects.filter(group=self.group, user=self.member).exists())

    def test_role_errors_are_japanese_and_existing_memberships_stay_unchanged(self):
        cases = (
            ({}, 400, "ユーザーIDと権限を指定してください"),
            ({"user_id": self.member.pk, "role": "owner"}, 400, "権限はadminまたはmemberを指定してください"),
            ({"user_id": self.member.pk + 9999, "role": "admin"}, 404, "メンバーが見つかりません"),
        )
        for data, code, message in cases:
            with self.subTest(code=code, message=message):
                response = self.request_action("set_member_role", data)
                self.assertEqual(response.status_code, code)
                self.assertEqual(response.json()["error"], message)
                self.assert_target_unchanged()

    def test_non_admin_cannot_change_members_even_with_invalid_input(self):
        self.client.force_authenticate(self.member)
        for action in ("set_member_role", "remove_member"):
            with self.subTest(action=action):
                response = self.request_action(action, {"user_id": "invalid-id", "role": "admin"})
                self.assertEqual(response.status_code, 403)
                self.assert_target_unchanged()
