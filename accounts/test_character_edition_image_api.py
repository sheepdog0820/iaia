from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .character_models import CharacterImage6th
from .test_character_factories import create_6th_character, create_7th_character


class EditionImageApiTests(TestCase):
    def setUp(self):
        # Isolated test fixture or mocked credential; never a production secret.
        self.user = get_user_model().objects.create_user(
            username="edition-image", password="test-password"
        )  # nosec B106
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.sheet, self.detail = create_6th_character(user=self.user, name="Image detail")

    def test_set_main_and_delete_use_the_edition_image_table(self):
        first = CharacterImage6th.objects.create(character_sheet=self.detail, image="first.jpg", is_main=True, order=0)
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

        delete_url = reverse("character-images-detail", kwargs={"character_sheet_id": self.sheet.id, "pk": second.id})
        self.assertEqual(self.client.delete(delete_url).status_code, 204)
        first.refresh_from_db()
        self.assertTrue(first.is_main)
        self.assertEqual(CharacterImage6th.objects.filter(character_sheet=self.detail).count(), 1)

    def test_image_lists_are_not_cached_for_either_edition(self):
        seventh, _ = create_7th_character(user=self.user, name="Image cache check")
        for sheet in (self.sheet, seventh):
            with self.subTest(edition=sheet.edition):
                response = self.client.get(f"/api/accounts/character-sheets/{sheet.id}/images/")
                self.assertEqual(response.status_code, 200)
                directives = set(response.get("Cache-Control", "").split(", "))
                self.assertTrue({"private", "no-store", "no-cache", "max-age=0"}.issubset(directives))

    def test_unauthenticated_image_response_is_not_cached(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/accounts/character-sheets/{self.sheet.id}/images/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response.get("Cache-Control", ""))
