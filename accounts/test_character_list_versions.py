from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from accounts.models import CustomUser
from accounts.test_character_factories import create_character_with_system_data


class CharacterListVersionTests(TestCase):
    def test_latest_includes_descendants_and_queries_stay_bounded(self):
        user = CustomUser.objects.create_user(username="list-version-owner")
        other = CustomUser.objects.create_user(username="list-version-other")
        client = APIClient()
        client.force_authenticate(user)
        expected = {}
        for edition in ("6th", "7th"):
            root, root_data = create_character_with_system_data(user=user, edition=edition)
            second, second_data = create_character_with_system_data(
                user=user, edition=edition, parent_data=root_data, version=2
            )
            third, _ = create_character_with_system_data(user=user, edition=edition, parent_data=second_data, version=4)
            branch, _ = create_character_with_system_data(
                user=user, edition=edition, parent_data=root_data, version=3, is_active=False
            )
            for item in (root, second, third, branch):
                expected[item.pk] = 4
            independent, _ = create_character_with_system_data(user=user, edition=edition, version=1)
            expected[independent.pk] = 1
            create_character_with_system_data(user=other, edition=edition, version=99)
        with CaptureQueriesContext(connection) as queries:
            response = client.get("/api/accounts/character-sheets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["id"]: row["latest_version"] for row in response.data}, expected)
        self.assertLessEqual(len(queries), 10)
        response = client.get("/api/accounts/character-sheets/?page_size=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertTrue(any(row["latest_version"] == 4 for row in response.data["results"]))
        for row in response.data["results"]:
            self.assertEqual(row["latest_version"], expected[row["id"]])
