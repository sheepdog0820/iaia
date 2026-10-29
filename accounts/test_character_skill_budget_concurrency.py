"""Concurrent skill API allocations must share the existing character budget."""

from concurrent.futures import ThreadPoolExecutor
from itertools import product
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.db.models import Sum
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient, APITransactionTestCase

from accounts.character_models import CharacterSkillSystemData
from accounts.test_character_factories import create_character_with_system_data
from accounts.views.character_views import CharacterSkillViewSet


@skipUnlessDBFeature("has_select_for_update")
class CharacterSkillBudgetConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="skill-budget-owner", password=None)

    def character(self, edition):
        return create_character_with_system_data(
            user=self.owner,
            edition=edition,
            name="技能競合確認",
            edu_value=50 if edition == "7th" else 12,
            int_value=50 if edition == "7th" else 14,
        )

    def check_race(self, edition, field, kinds):
        sheet, detail = self.character(edition)
        quota = (
            detail.calculate_occupation_points() if field == "occupation_points" else detail.calculate_hobby_points()
        )
        skills = [detail.skills.create(skill_name=f"競合技能{i}", base_value=5) for i in range(2)]
        first_validated, second_validated = Event(), Event()
        original_clean = CharacterSkillSystemData.clean

        def clean(instance):
            original_clean(instance)
            if not first_validated.is_set():
                first_validated.set()
                # A shared parent lock prevents the second validation until
                # this bounded wait ends and the first transaction commits.
                second_validated.wait(timeout=2)
            else:
                second_validated.set()

        def write(index):
            close_old_connections()
            try:
                if index:
                    self.assertTrue(first_validated.wait(timeout=10))
                client = APIClient()
                client.force_authenticate(self.owner)
                url = f"/api/accounts/character-sheets/{sheet.pk}/skills/"
                if kinds[index] == "update":
                    return client.patch(url + f"{skills[index].pk}/", {field: quota}, format="json").status_code
                if kinds[index] == "bulk":
                    return client.patch(
                        url + "bulk_update/", {"skills": [{"id": skills[index].pk, field: quota}]}, format="json"
                    ).status_code
                return client.post(
                    url, {"skill_name": f"追加技能{index}", "base_value": 5, field: quota}, format="json"
                ).status_code
            finally:
                close_old_connections()

        with patch.object(CharacterSkillSystemData, "clean", clean):
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(write, range(2)))
        used = detail.skills.aggregate(total=Sum(field))["total"] or 0
        self.assertEqual(responses, [201 if kinds[0] == "create" else 200, 400])
        self.assertEqual(used, quota)
        self.assertEqual(detail.skills.count(), 3 if kinds[0] == "create" else 2)

    def test_concurrent_allocation(self):
        for edition, field, first, second in product(
            ("6th", "7th"),
            ("occupation_points", "interest_points"),
            ("create", "update", "bulk"),
            ("create", "update", "bulk"),
        ):
            with self.subTest(edition=edition, field=field, first=first, second=second):
                self.check_race(edition, field, (first, second))

    def test_partial_updates_preserve_the_other_committed_field(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail = self.character(edition)
                skill = detail.skills.create(skill_name="元の技能名", base_value=20)
                first_read, second_read, first_finished = Event(), Event(), Event()
                original_update = CharacterSkillViewSet.perform_update

                def update(view, serializer):
                    if "other_points" in serializer.validated_data:
                        first_read.set()
                        self.assertTrue(second_read.wait(timeout=10))
                        try:
                            return original_update(view, serializer)
                        finally:
                            first_finished.set()
                    second_read.set()
                    self.assertTrue(first_finished.wait(timeout=10))
                    return original_update(view, serializer)

                def write(index):
                    close_old_connections()
                    try:
                        if index:
                            self.assertTrue(first_read.wait(timeout=10))
                        client = APIClient()
                        client.force_authenticate(self.owner)
                        return client.patch(
                            f"/api/accounts/character-sheets/{sheet.pk}/skills/{skill.pk}/",
                            {"skill_name": "更新後の技能名"} if index else {"other_points": 7},
                            format="json",
                        ).status_code
                    finally:
                        close_old_connections()

                with patch.object(CharacterSkillViewSet, "perform_update", update):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        responses = list(pool.map(write, range(2)))
                self.assertEqual(responses, [200, 200])
                skill.refresh_from_db()
                self.assertEqual((skill.skill_name, skill.other_points, skill.current_value), ("更新後の技能名", 7, 27))


class CharacterSkillUpdateAtomicityTests(APITransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="skill-update-atomic-owner", password=None)
        self.client.force_authenticate(self.owner)
        self.client.raise_request_exception = False

    def skill(self, edition):
        sheet, detail = create_character_with_system_data(
            user=self.owner,
            edition=edition,
            name="技能更新の原子性確認",
            edu_value=50 if edition == "7th" else 12,
            int_value=50 if edition == "7th" else 14,
        )
        skill = detail.skills.create(skill_name="変更前の技能", base_value=20)
        return sheet, detail, skill

    def test_failure_after_save_rolls_back_the_update(self):
        for edition, validation in product(("6th", "7th"), (True, False)):
            with self.subTest(edition=edition, validation=validation):
                sheet, _, skill = self.skill(edition)
                original_save = type(skill).save

                def fail(instance, *args, **kwargs):
                    original_save(instance, *args, **kwargs)
                    if validation:
                        raise ValidationError({"other_points": "技能の入力を確認してください。"})
                    raise RuntimeError("synthetic-private-update-after-write")

                with patch.object(type(skill), "save", fail):
                    response = self.client.patch(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/{skill.pk}/",
                        {"other_points": 7},
                        format="json",
                    )
                self.assertEqual(response.status_code, 400 if validation else 500)
                self.assertNotIn("synthetic-private-update-after-write", response.content.decode())
                skill.refresh_from_db()
                self.assertEqual((skill.other_points, skill.current_value), (0, 20))

    def test_deleted_skill_is_not_recreated_by_a_stale_update(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, detail, skill = self.skill(edition)
                original_update = CharacterSkillViewSet.perform_update

                def delete_before_update(view, serializer):
                    type(skill).objects.filter(pk=skill.pk).delete()
                    return original_update(view, serializer)

                with patch.object(CharacterSkillViewSet, "perform_update", delete_before_update):
                    response = self.client.patch(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/{skill.pk}/",
                        {"other_points": 7},
                        format="json",
                    )
                self.assertEqual(response.status_code, 404)
                self.assertFalse(detail.skills.exists())

    def test_ownership_is_rechecked_before_writing_a_stale_update(self):
        other = get_user_model().objects.create_user(username="skill-new-owner", password=None)
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                sheet, _, skill = self.skill(edition)
                original_update = CharacterSkillViewSet.perform_update

                def transfer_before_update(view, serializer):
                    type(sheet).objects.filter(pk=sheet.pk).update(user=other)
                    return original_update(view, serializer)

                with patch.object(CharacterSkillViewSet, "perform_update", transfer_before_update):
                    response = self.client.patch(
                        f"/api/accounts/character-sheets/{sheet.pk}/skills/{skill.pk}/",
                        {"other_points": 7},
                        format="json",
                    )
                self.assertEqual(response.status_code, 404)
                skill.refresh_from_db()
                self.assertEqual((skill.other_points, skill.current_value), (0, 20))
