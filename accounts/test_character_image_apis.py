from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import CharacterSheet, CharacterImage
from accounts.test_character_integration import CharacterIntegrationTestCase


User = get_user_model()


class CharacterImageAPISMokeTest(APITestCase):
    """画像APIの簡易スモークテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apitester',
            password='pass123',
            email='api@example.com'
        )
        self.client.force_authenticate(user=self.user)

        self.sheet = CharacterSheet.objects.create(
            user=self.user,
            name='Image API Sheet',
            edition='6th',
            age=25,
            str_value=10,
            con_value=10,
            pow_value=10,
            dex_value=10,
            app_value=10,
            siz_value=10,
            int_value=10,
            edu_value=10,
            hit_points_max=10,
            hit_points_current=10,
            magic_points_max=10,
            magic_points_current=10,
            sanity_starting=50,
            sanity_max=99,
            sanity_current=50,
        )

    def test_set_main_endpoint_updates_flag(self):
        """set-mainエンドポイントでメイン画像を切替できること"""
        img1 = CharacterImage.objects.create(
            character_sheet=self.sheet,
            image='test1.jpg',
            is_main=True,
            order=0,
        )
        img2 = CharacterImage.objects.create(
            character_sheet=self.sheet,
            image='test2.jpg',
            is_main=False,
            order=1,
        )

        url = reverse(
            'character-images-set-main',
            kwargs={'character_sheet_id': self.sheet.id, 'pk': img2.id},
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_main)
        self.assertTrue(img2.is_main)

    def test_delete_main_promotes_next(self):
        """メイン画像を削除すると次の画像がメインになる"""
        img1 = CharacterImage.objects.create(
            character_sheet=self.sheet,
            image='main.jpg',
            is_main=True,
            order=0,
        )
        img2 = CharacterImage.objects.create(
            character_sheet=self.sheet,
            image='second.jpg',
            is_main=False,
            order=1,
        )

        url = reverse(
            'character-images-detail',
            kwargs={'character_sheet_id': self.sheet.id, 'pk': img1.id},
        )
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        img2.refresh_from_db()
        self.assertTrue(img2.is_main)


class CCFOLIAEndpointSmokeTest(APITestCase):
    """CCFOLIAエクスポートの簡易確認"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='ccfoliauser',
            password='pass123',
            email='ccfolia@example.com'
        )
        self.client.force_authenticate(user=self.user)

        helper = CharacterIntegrationTestCase()
        helper.setUp()
        self.sheet = helper.create_character_with_stats(user=self.user)

    def test_ccfolia_json_status_ok(self):
        url = reverse('character-sheet-ccfolia-json', kwargs={'pk': self.sheet.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('data', resp.data)
        self.assertEqual(resp.data.get('kind'), 'character')
