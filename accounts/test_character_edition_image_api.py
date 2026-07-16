from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .character_models import CharacterImage6th
from .test_character_factories import create_6th_character


class EditionImageApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="edition-image", password="test-password")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.sheet, self.detail = create_6th_character(user=self.user, name="Image detail")

    def test_set_main_and_delete_use_the_edition_image_table(self):
        first = CharacterImage6th.objects.create(
            character_sheet=self.detail, image="first.jpg", is_main=True, order=0
        )
        second = CharacterImage6th.objects.create(
            character_sheet=self.detail, image="second.jpg", is_main=False, order=1
        )

        set_main_url = reverse(
            "character-images-set-main", kwargs={"character_sheet_id": self.sheet.id, "pk": second.id}
        )
        self.assertEqual(self.client.post(set_main_url).status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_main)
        self.assertTrue(second.is_main)

        delete_url = reverse(
            "character-images-detail", kwargs={"character_sheet_id": self.sheet.id, "pk": second.id}
        )
        self.assertEqual(self.client.delete(delete_url).status_code, 204)
        first.refresh_from_db()
        self.assertTrue(first.is_main)
        self.assertEqual(CharacterImage6th.objects.filter(character_sheet=self.detail).count(), 1)
