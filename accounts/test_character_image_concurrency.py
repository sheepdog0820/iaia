import io
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from PIL import Image
from rest_framework.test import APIClient

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
