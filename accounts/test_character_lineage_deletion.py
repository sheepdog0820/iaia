from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from schedules import session_permissions
from schedules.models import TRPGSession

from .character_models import CharacterSheet, CharacterSheet6th, CharacterSheet7th
from .models import Group


class CharacterLineageDeletionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="lineage-owner")
        self.other = get_user_model().objects.create_user(username="lineage-other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def tree(self, edition):
        model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
        root = CharacterSheet.objects.create(user=self.user, edition=edition)
        model.objects.create(
            character_sheet=root,
            name="履歴の探索者",
            version=1,
            age=25,
            **{
                f"{stat}_value": 12 if edition == "6th" else 60
                for stat in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")
            },
        )
        middle = root.create_new_version("第2世代")
        leaf = middle.create_new_version("第3世代")
        branch = root.create_new_version("別の成長")
        return model, [root, middle, leaf, branch]

    def test_api_deletion_keeps_survivors_and_connected_history(self):
        for edition in ("6th", "7th"):
            for deleted_index in (0, 1, 2):
                with self.subTest(edition=edition, deleted_index=deleted_index):
                    model, records = self.tree(edition)
                    target = records[deleted_index]
                    before = {record.pk: record.system_data.version for record in records}
                    response = self.client.delete(f"/api/accounts/character-sheets/{target.pk}/")
                    self.assertEqual(response.status_code, 204)
                    self.assertFalse(CharacterSheet.objects.filter(pk=target.pk).exists())
                    remaining = [record for record in records if record.pk != target.pk]
                    for record in remaining:
                        detail = model.objects.get(character_sheet=record)
                        self.assertEqual(detail.name, "履歴の探索者")
                        self.assertEqual(detail.version, before[record.pk])
                        self.assertEqual(
                            self.client.get(f"/api/accounts/character-sheets/{record.pk}/").status_code, 200
                        )
                    data = {record.pk: model.objects.get(character_sheet=record) for record in remaining}
                    if deleted_index == 0:
                        self.assertIsNone(data[records[1].pk].parent_data_id)
                        self.assertEqual(data[records[2].pk].parent_data_id, data[records[1].pk].pk)
                        self.assertEqual(data[records[3].pk].parent_data_id, data[records[1].pk].pk)
                    elif deleted_index == 1:
                        self.assertEqual(data[records[2].pk].parent_data_id, data[records[0].pk].pk)
                    newest = remaining[-1].create_new_version("削除後の成長")
                    self.assertEqual(newest.system_data.version, 5)

    def test_other_user_cannot_delete_lineage(self):
        self.client.force_authenticate(self.other)
        for edition in ("6th", "7th"):
            model, records = self.tree(edition)
            response = self.client.delete(f"/api/accounts/character-sheets/{records[0].pk}/")
            self.assertIn(response.status_code, (403, 404))
            self.assertEqual(model.objects.filter(character_sheet__in=records).count(), 4)

    def test_bulk_deletion_does_not_cascade_to_later_versions(self):
        for edition in ("6th", "7th"):
            model, records = self.tree(edition)
            CharacterSheet.objects.filter(pk=records[0].pk).delete()
            self.assertEqual(model.objects.filter(character_sheet__in=records[1:]).count(), 3)

    @override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}})
    def test_survivors_keep_related_data(self):
        for edition in ("6th", "7th"):
            model, records = self.tree(edition)
            detail = records[2].system_data
            skill = detail.skills.create(skill_name="目星", base_value=25, occupation_points=40)
            equipment = detail.equipment.create(name="手帳", item_type="item", quantity=2)
            original = records[0].system_data.images.create(is_main=True)
            original.image.save("lineage-proof.png", ContentFile(b"isolated image file fixture"))
            portrait = detail.images.create(image=original.image.name, is_main=True)
            group = Group.objects.create(name="世代保持の検証", created_by=self.user)
            participants = []
            for sheet in (records[0], records[2]):
                session = TRPGSession.objects.create(
                    title="世代保持の検証", date=timezone.now(), gm=self.other, group=group
                )
                participants.append(
                    session_permissions.create_participant(
                        session=session, user=self.user, character_name=detail.name, character_sheet=sheet
                    )
                )
            records[0].delete()
            for related in (skill, equipment, portrait):
                related.refresh_from_db()
                self.assertEqual(related.character_sheet_id, detail.pk)
            self.assertEqual(skill.occupation_points, 40)
            self.assertEqual(equipment.quantity, 2)
            self.assertEqual(portrait.image.name, original.image.name)
            with portrait.image.open("rb") as image_file:
                self.assertEqual(image_file.read(), b"isolated image file fixture")
            for participant in participants:
                participant.refresh_from_db()
                self.assertEqual(participant.character_name, detail.name)
                self.assertEqual(participant.user_id, self.user.pk)
            self.assertIsNone(participants[0].character_sheet_id)
            self.assertEqual(participants[1].character_sheet_id, records[2].pk)

    def test_unsaved_sheet_cannot_be_deleted(self):
        with self.assertRaises(ValueError):
            CharacterSheet(user=self.user, edition="6th").delete()

    def test_missing_detail_or_already_deleted_registry_is_safe(self):
        for edition in ("6th", "7th"):
            orphan = CharacterSheet.objects.create(user=self.user, edition=edition)
            stale = CharacterSheet.objects.get(pk=orphan.pk)
            orphan.delete()
            self.assertEqual(stale.delete(), (0, {}))

    def test_deleting_promoted_root_ignores_cached_old_parent(self):
        for edition in ("6th", "7th"):
            model, records = self.tree(edition)
            self.assertEqual(records[1].system_data.parent_data_id, records[0].system_data.pk)
            records[0].delete()
            records[1].delete()
            leaf = model.objects.get(character_sheet=records[2])
            branch = model.objects.get(character_sheet=records[3])
            self.assertIsNone(leaf.parent_data_id)
            self.assertEqual(branch.parent_data_id, leaf.pk)

    def test_reparenting_rolls_back_if_deletion_fails(self):
        for edition in ("6th", "7th"):
            model, records = self.tree(edition)
            before = list(model.objects.filter(character_sheet__in=records).values_list("pk", "parent_data_id"))
            with patch("django.db.models.Model.delete", side_effect=RuntimeError("isolated failure")):
                with self.assertRaises(RuntimeError):
                    records[1].delete()
            self.assertEqual(
                list(model.objects.filter(character_sheet__in=records).values_list("pk", "parent_data_id")), before
            )


@skipUnlessDBFeature("has_select_for_update")
class CharacterLineageDeletionConcurrencyTests(TransactionTestCase):
    def test_creation_waiting_for_parent_deletion_reads_updated_lineage(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                owner = get_user_model().objects.create_user(username=f"waiting-lineage-{edition}")
                model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
                root = CharacterSheet.objects.create(user=owner, edition=edition)
                model.objects.create(character_sheet=root, name="待機中の探索者", version=1)
                child = root.create_new_version("第2世代")
                locking = Event()

                def observe_lock(execute, sql, params, many, context):
                    if model._meta.db_table in sql and "FOR UPDATE" in sql:
                        locking.set()
                    return execute(sql, params, many, context)

                def create():
                    close_old_connections()
                    try:
                        with connection.execute_wrapper(observe_lock):
                            return CharacterSheet.objects.get(pk=child.pk).create_new_version("待機後の成長").pk
                    finally:
                        close_old_connections()

                with ThreadPoolExecutor(max_workers=1) as pool:
                    with transaction.atomic():
                        list(model.objects.select_for_update().order_by("pk"))
                        creation = pool.submit(create)
                        self.assertTrue(locking.wait(timeout=10))
                        root.delete()
                    new_id = creation.result(timeout=30)
                child_data = model.objects.get(character_sheet=child)
                self.assertIsNone(child_data.parent_data_id)
                newest = model.objects.get(character_sheet_id=new_id)
                self.assertEqual(newest.parent_data_id, child_data.pk)
                self.assertEqual(newest.version, 3)

    def test_root_deletion_and_descendant_creation_preserve_history(self):
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                owner = get_user_model().objects.create_user(username=f"concurrent-lineage-{edition}")
                model = CharacterSheet6th if edition == "6th" else CharacterSheet7th
                root = CharacterSheet.objects.create(user=owner, edition=edition)
                model.objects.create(character_sheet=root, name="並行操作の探索者", version=1)
                child = root.create_new_version("第2世代")
                barrier = Barrier(2)

                def operate(delete):
                    close_old_connections()
                    try:
                        sheet = CharacterSheet.objects.get(pk=root.pk if delete else child.pk)
                        barrier.wait(timeout=10)
                        if delete:
                            sheet.delete()
                        else:
                            return sheet.create_new_version("第3世代").pk
                    finally:
                        close_old_connections()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    deletion = pool.submit(operate, True)
                    creation = pool.submit(operate, False)
                    deletion.result(timeout=30)
                    new_id = creation.result(timeout=30)
                self.assertFalse(CharacterSheet.objects.filter(pk=root.pk).exists())
                child_data = model.objects.get(character_sheet=child)
                self.assertIsNone(child_data.parent_data_id)
                newest = model.objects.get(character_sheet_id=new_id)
                self.assertEqual(newest.parent_data_id, child_data.pk)
                self.assertEqual(newest.version, 3)
