from django.contrib.auth import get_user_model
from django.test import TestCase

from .test_character_factories import create_6th_character, create_7th_character


class CharacterFactoryTests(TestCase):
    def test_factory_creates_a_registry_and_only_the_matching_edition_data(self):
        user = get_user_model().objects.create_user(username="factory-user", password="test-password")

        sixth_registry, sixth = create_6th_character(user=user, name="Sixth", str_value=12)
        seventh_registry, seventh = create_7th_character(user=user, name="Seventh", pow_value=60)

        self.assertEqual(sixth_registry.sixth_edition_data.pk, sixth.pk)
        self.assertEqual(sixth.name, "Sixth")
        self.assertEqual(seventh_registry.seventh_edition_data.pk, seventh.pk)
        self.assertEqual(seventh.name, "Seventh")
        self.assertFalse(hasattr(sixth_registry, "name"))
        self.assertFalse(hasattr(seventh_registry, "pow_value"))
