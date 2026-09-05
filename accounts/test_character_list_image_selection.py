from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.models import CustomUser
from accounts.serializers import CharacterSheetListSerializer
from accounts.test_character_factories import create_character_with_system_data


class CharacterListImageSelectionTests(TestCase):
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
