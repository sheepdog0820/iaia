from datetime import timedelta

from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import CustomUser
from accounts.serializers import CharacterSheetListSerializer
from accounts.test_character_factories import create_character_with_system_data


class CharacterListImageSelectionTests(TestCase):
    def test_list_batches_image_queries_for_both_editions(self):
        user = CustomUser.objects.create_user(username="batched-list-images")
        other = CustomUser.objects.create_user(username="other-list-images")
        create_character_with_system_data(user=other, edition="6th")
        client = APIClient()
        client.force_authenticate(user)
        expected = {}
        for edition in ("6th", "7th"):
            for number in range(4):
                registry, detail = create_character_with_system_data(user=user, edition=edition)
                selected = None
                if number:
                    selected = detail.images.create(image="character_images/first.png", order=0)
                    last = detail.images.create(image="character_images/last.png", order=2, is_main=number == 2)
                    if number == 2:
                        selected = last
                expected[registry.pk] = selected.image.url if selected else None
        with CaptureQueriesContext(connection) as queries:
            response = client.get("/api/accounts/character-sheets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["id"] for row in response.data}, set(expected))
        for row in response.data:
            path = expected[row["id"]]
            self.assertEqual(row["character_image"], "http://testserver" + path if path else None)
        image_queries = [query for query in queries if 'FROM "accounts_characterimage' in query["sql"]]
        self.assertLessEqual(len(image_queries), 2)

    def test_list_uses_order_then_upload_time_unless_main_is_selected(self):
        user = CustomUser.objects.create_user(username="list-images")
        request = RequestFactory().get("/")
        for edition in ("6th", "7th"):
            with self.subTest(edition=edition):
                registry, detail = create_character_with_system_data(user=user, edition=edition)
                later = detail.images.create(image="character_images/later.png", order=1)
                earlier = detail.images.create(image="character_images/earlier.png", order=1)
                detail.images.filter(pk=earlier.pk).update(uploaded_at=timezone.now() - timedelta(days=1))
                detail.images.create(image="character_images/last.png", order=2)
                data = CharacterSheetListSerializer(registry, context={"request": request}).data
                self.assertEqual(data["character_image"], request.build_absolute_uri(earlier.image.url))
                later.is_main = True
                later.save(update_fields=["is_main"])
                data = CharacterSheetListSerializer(registry, context={"request": request}).data
                self.assertEqual(data["character_image"], request.build_absolute_uri(later.image.url))
