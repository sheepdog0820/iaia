from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class CharacterCreatePlayerNameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="character-player",
            password="test-password",
            nickname="プレイヤー表示名",
        )
        self.client.force_login(self.user)

    def test_6th_create_page_prefills_player_name_from_logged_in_user(self):
        response = self.client.get(reverse("character_create_6th"))

        self.assertContains(response, 'id="player-name" name="player_name" value="プレイヤー表示名"')

    def test_7th_create_page_prefills_player_name_from_logged_in_user(self):
        response = self.client.get(reverse("character_create_7th"))

        self.assertContains(response, 'id="player-name" name="player_name" value="プレイヤー表示名"')
