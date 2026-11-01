"""Invalid imported fields return a client error and leave no partial character."""

import json
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
    CharacterSkill6th,
    CharacterSkill7th,
    CustomUser,
)


class CcfoliaImportValidationTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="ccfolia-validation-free")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.client.raise_request_exception = False
        self.url = reverse("character-sheet-import-ccfolia-json")

    def payload(self, edition):
        return {
            "kind": "character",
            "edition": edition,
            "data": {
                "name": f"取込検証 {edition}",
                "params": [
                    {"label": label, "value": "65" if edition == "7th" else "13"}
                    for label in ("STR", "CON", "POW", "DEX", "APP", "SIZ", "INT", "EDU")
                ],
                "status": [{"label": "SAN", "value": 60, "max": 65}],
            },
            "skills": [{"name": "目星", "value": 65}],
        }

    def row_counts(self):
        return tuple(
            model.objects.count()
            for model in (CharacterSheet, CharacterSheet6th, CharacterSheet7th, CharacterSkill6th, CharacterSkill7th)
        )

    def assert_rejected_without_writes(self, payload, **profile):
        before = self.row_counts()
        response = self.client.post(
            self.url,
            json.dumps({"ccfolia": payload, **profile}, ensure_ascii=True).encode("ascii"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.row_counts(), before)
        self.assertIn("ccfolia", response.data)
        message = str(response.data["ccfolia"])
        self.assertIn("確認してください", message)
        self.assertIn("保存されていません", message)
        self.assertNotIn("private-fixture", message)
        self.assertNotIn("ValidationError", message)

    def test_invalid_skill_values_and_names_are_rejected_atomically(self):
        for edition in ("6th", "7th"):
            for name, value in (("目星", 1000), ("目星", -1), ("private-fixture-" + "技" * 101, 65)):
                with self.subTest(edition=edition, name_length=len(name), value=value):
                    payload = self.payload(edition)
                    payload["skills"] = [{"name": name, "value": value}]
                    self.assert_rejected_without_writes(payload)

    def test_invalid_skills_from_standard_commands_are_rejected(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                payload = self.payload(edition)
                payload.pop("skills")
                payload["data"]["commands"] = "CCB<=1000 【目星】"
                self.assert_rejected_without_writes(payload)

    def test_overlong_character_name_is_rejected(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                payload = self.payload(edition)
                payload["data"]["name"] = "private-fixture-" + "名" * 101
                self.assert_rejected_without_writes(payload)

    def test_overlong_optional_profile_fields_are_rejected(self):
        for edition in ("6th", "7th"):
            for field, limit in (("gender", 50), ("occupation", 100), ("birthplace", 100), ("residence", 100)):
                with self.subTest(edition=edition, field=field):
                    self.assert_rejected_without_writes(
                        self.payload(edition), **{field: "private-fixture-" + "名" * limit}
                    )

    def test_unrepresentable_status_integers_are_rejected(self):
        lower, upper = connection.ops.integer_field_range("IntegerField")
        for edition in ("6th", "7th"):
            for label in ("HP", "MP", "SAN") + (("幸運",) if edition == "7th" else ()):
                for value in (lower - 1, upper + 1):
                    with self.subTest(edition=edition, label=label, value=value):
                        payload = self.payload(edition)
                        payload["data"]["status"] = [{"label": label, "value": value, "max": value}]
                        self.assert_rejected_without_writes(payload)

    def test_valid_boundaries_remain_available_to_free_users(self):
        self.assertFalse(self.user.is_premium)
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                payload = self.payload(edition)
                payload["data"]["name"] = "名" * 100
                payload["data"]["status"] = [
                    {"label": "HP", "value": 0, "max": 10},
                    {"label": "SAN", "value": -1, "max": 65},
                    {"label": "幸運", "value": 0, "max": 0},
                ]
                payload["skills"] = [{"name": "技" * 100, "value": 999}]
                response = self.client.post(
                    self.url,
                    {"ccfolia": payload, "gender": "性" * 50, "occupation": "職" * 100},
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.data)
                imported = CharacterSheet.objects.get(pk=response.data["id"])
                self.assertEqual(imported.edition, edition)
                self.assertEqual(imported.user_id, self.user.pk)
                detail = imported.system_data
                self.assertEqual(detail.name, "名" * 100)
                self.assertEqual(detail.hit_points_current, 0)
                self.assertEqual(detail.sanity_current, -1)
                self.assertEqual(detail.skills.get().current_value, 999)
                if edition == "7th":
                    self.assertEqual((detail.luck_current, detail.luck_max), (0, 0))

    def test_unrepresentable_text_is_rejected_without_partial_rows(self):
        for edition in ("6th", "7th"):
            for invalid in ("\x00", "\ud800"):
                for field in ("name", "externalUrl", "iconUrl", "skill", "gender"):
                    with self.subTest(edition=edition, invalid=ascii(invalid), field=field):
                        payload = self.payload(edition)
                        text = "private-fixture-" + invalid
                        profile = {}
                        if field == "skill":
                            payload["skills"] = [{"name": text, "value": 65}]
                        elif field == "gender":
                            profile["gender"] = text
                        else:
                            payload["data"][field] = text
                        self.assert_rejected_without_writes(payload, **profile)

    def test_failed_import_preserves_existing_character_version(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                payload = self.payload(edition)
                response = self.client.post(self.url, {"ccfolia": payload}, format="json")
                self.assertEqual(response.status_code, 201, response.data)
                original = CharacterSheet.objects.get(pk=response.data["id"]).system_data
                payload["skills"] = [{"name": "図書館", "value": 65}, {"name": "目星", "value": 1000}]
                self.assert_rejected_without_writes(payload)
                original.refresh_from_db()
                self.assertEqual(original.version, 1)
                self.assertIsNone(original.parent_data_id)
                self.assertEqual(original.skills.get().current_value, 65)

    def test_valid_reimport_preserves_version_lineage(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                imported = []
                for _ in range(3):
                    response = self.client.post(self.url, {"ccfolia": self.payload(edition)}, format="json")
                    self.assertEqual(response.status_code, 201, response.data)
                    imported.append(CharacterSheet.objects.get(pk=response.data["id"]).system_data)
                self.assertEqual([detail.version for detail in imported], [1, 2, 3])
                self.assertEqual([detail.parent_data_id for detail in imported], [None, imported[0].pk, imported[0].pk])
                self.assertEqual([detail.skills.get().current_value for detail in imported], [65, 65, 65])

    def test_database_fault_is_not_reported_as_invalid_input(self):
        before = self.row_counts()
        with patch.object(CharacterSheet7th, "save", side_effect=OperationalError("synthetic database fault")):
            response = self.client.post(self.url, {"ccfolia": self.payload("7th")}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.row_counts(), before)
