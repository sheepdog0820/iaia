import io
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import CharacterSheet
from accounts.serializers import CharacterImageSerializer
from accounts.test_character_factories import create_character_with_system_data


@skipUnlessDBFeature("has_select_for_update")
class CharacterImageConcurrencyTests(TransactionTestCase):
    def check_last_slot(self, edition):
        user = get_user_model().objects.create_user(username="image_concurrency")
        character, detail = create_character_with_system_data(user=user, edition=edition, name="画像競合確認")
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color="red").save(buffer, "PNG")
        content = buffer.getvalue()
        first_validated = Event()
        second_validated = Event()
        original_validate = CharacterImageSerializer.validate

        def validate(serializer, attrs):
            result = original_validate(serializer, attrs)
            if not first_validated.is_set():
                first_validated.set()
                # Expose the old check/save race. With a row lock, the second
                # request cannot validate until this bounded wait has ended.
                second_validated.wait(timeout=2)
            else:
                second_validated.set()
            return result

        def upload(index):
            close_old_connections()
            try:
                if index:
                    self.assertTrue(first_validated.wait(timeout=10))
                client = APIClient()
                client.force_authenticate(user=user)
                return client.post(
                    f"/api/accounts/character-sheets/{character.pk}/images/",
                    {"image": SimpleUploadedFile(f"new-{index}.png", content, content_type="image/png")},
                    format="multipart",
                ).status_code
            finally:
                close_old_connections()

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            existing = []
            for index in range(4):
                image = detail.images.create(
                    image=SimpleUploadedFile(f"old-{index}.png", content, content_type="image/png"),
                    order=index,
                    is_main=index == 0,
                )
                existing.append((image.pk, image.image.name))
            with patch.object(CharacterImageSerializer, "validate", validate):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    responses = list(pool.map(upload, range(2)))
            self.assertEqual(sorted(responses), [201, 400])
            self.assertEqual(detail.images.count(), 5)
            self.assertEqual(detail.images.filter(is_main=True).count(), 1)
            for pk, name in existing:
                self.assertEqual(detail.images.get(pk=pk).image.name, name)
                with detail.images.get(pk=pk).image.open("rb") as stored:
                    self.assertEqual(stored.read(), content)

    def test_6th_last_slot_rejects_concurrent_excess(self):
        self.check_last_slot("6th")

    def test_7th_last_slot_rejects_concurrent_excess(self):
        self.check_last_slot("7th")

    def check_main_switches(self, edition, use_update):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL lock inspection is required")
        user = get_user_model().objects.create_user(username="main_image_concurrency")
        character, detail = create_character_with_system_data(user=user, edition=edition, name="メイン画像競合確認")
        first_waiting, release_first, second_connected = Event(), Event(), Event()
        second_pid = []
        image_model = detail.images.model
        original_save = image_model.save

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            images = []
            for index in range(3):
                buffer = io.BytesIO()
                Image.new("RGB", (8, 8), color="red").save(buffer, "PNG")
                images.append(
                    detail.images.create(
                        image=SimpleUploadedFile(f"switch-{index}.png", buffer.getvalue(), content_type="image/png"),
                        order=index,
                        is_main=index == 0,
                    )
                )

            def save(instance, *args, **kwargs):
                if instance.pk == images[1].pk and instance.is_main:
                    first_waiting.set()
                    if not release_first.wait(timeout=15):
                        raise AssertionError("First image switch was not released")
                return original_save(instance, *args, **kwargs)

            def switch(index):
                close_old_connections()
                try:
                    connection.ensure_connection()
                    if index == 2:
                        second_pid.append(connection.connection.info.backend_pid)
                        second_connected.set()
                    client = APIClient()
                    client.raise_request_exception = False
                    client.force_authenticate(user=user)
                    url = f"/api/accounts/character-sheets/{character.pk}/images/{images[index].pk}/"
                    if use_update:
                        return client.patch(url, {"is_main": True}, format="json").status_code
                    return client.patch(url + "set_main/").status_code
                finally:
                    close_old_connections()

            with patch.object(image_model, "save", save), ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(switch, 1)
                second = None
                try:
                    self.assertTrue(first_waiting.wait(timeout=10))
                    second = pool.submit(switch, 2)
                    self.assertTrue(second_connected.wait(timeout=10))
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT cardinality(pg_blocking_pids(%s))", [second_pid[0]])
                            blocked = cursor.fetchone()[0] > 0
                        if blocked or second.done():
                            break
                        time.sleep(0.01)
                    self.assertTrue(blocked or second.done(), "Second request neither blocked nor completed")
                finally:
                    release_first.set()
                self.assertEqual(first.result(timeout=15), 200)
                self.assertIsNotNone(second)
                self.assertEqual(second.result(timeout=15), 200)

            self.assertEqual(list(detail.images.filter(is_main=True).values_list("pk", flat=True)), [images[2].pk])
            self.assertEqual(detail.images.count(), 3)
            for image in images:
                self.assertTrue(image.image.storage.exists(image.image.name))

    def test_6th_concurrent_main_actions(self):
        self.check_main_switches("6th", use_update=False)

    def test_7th_concurrent_main_actions(self):
        self.check_main_switches("7th", use_update=False)

    def test_6th_concurrent_main_updates(self):
        self.check_main_switches("6th", use_update=True)

    def test_7th_concurrent_main_updates(self):
        self.check_main_switches("7th", use_update=True)

    def check_ownership_after_lock(self, edition):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL lock inspection is required")
        owner = get_user_model().objects.create_user(username="waiting_image_owner")
        successor = get_user_model().objects.create_user(username="new_image_owner")
        character, detail = create_character_with_system_data(user=owner, edition=edition, name="画像所有権競合確認")
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color="red").save(buffer, "PNG")
        content = buffer.getvalue()

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            image = detail.images.create(
                image=SimpleUploadedFile("owner.png", content, content_type="image/png"), is_main=True, order=0
            )
            base = f"/api/accounts/character-sheets/{character.pk}/images/"
            for action in ("create", "update", "delete", "reorder", "set_main"):
                with self.subTest(action=action):
                    CharacterSheet.objects.filter(pk=character.pk).update(user=owner)
                    connected, pid = Event(), []

                    def write():
                        close_old_connections()
                        try:
                            connection.ensure_connection()
                            pid.append(connection.connection.info.backend_pid)
                            connected.set()
                            client = APIClient()
                            client.force_authenticate(user=owner)
                            if action == "create":
                                response = client.post(
                                    base,
                                    {"image": SimpleUploadedFile("new.png", content, content_type="image/png")},
                                    format="multipart",
                                )
                            elif action == "update":
                                response = client.patch(base + f"{image.pk}/", {"order": 9}, format="json")
                            elif action == "delete":
                                response = client.delete(base + f"{image.pk}/")
                            elif action == "reorder":
                                response = client.patch(
                                    base + "reorder/", {"order": [{"id": image.pk, "order": 9}]}, format="json"
                                )
                            else:
                                response = client.post(base + f"{image.pk}/set_main/")
                            return response.status_code
                        finally:
                            close_old_connections()

                    with ThreadPoolExecutor(max_workers=1) as pool:
                        with transaction.atomic():
                            CharacterSheet.objects.select_for_update().get(pk=character.pk)
                            future = pool.submit(write)
                            self.assertTrue(connected.wait(timeout=10))
                            deadline = time.monotonic() + 10
                            blocked = False
                            while time.monotonic() < deadline:
                                with connection.cursor() as cursor:
                                    cursor.execute("SELECT cardinality(pg_blocking_pids(%s))", [pid[0]])
                                    blocked = cursor.fetchone()[0] > 0
                                if blocked or future.done():
                                    break
                                time.sleep(0.01)
                            self.assertTrue(blocked, "Image writer did not wait for the registry row lock")
                            CharacterSheet.objects.filter(pk=character.pk).update(user=successor)
                        self.assertEqual(future.result(timeout=15), 403)
                    image.refresh_from_db()
                    self.assertEqual((image.order, image.is_main), (0, True))
                    self.assertEqual(detail.images.count(), 1)
                    with image.image.open("rb") as stored:
                        self.assertEqual(stored.read(), content)

    def test_6th_waiting_writers_recheck_ownership(self):
        self.check_ownership_after_lock("6th")

    def test_7th_waiting_writers_recheck_ownership(self):
        self.check_ownership_after_lock("7th")
