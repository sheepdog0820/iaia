from unittest.mock import patch

from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from allauth.socialaccount.models import SocialAccount

User = get_user_model()


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


@override_settings(
    DISCORD_CLIENT_ID='test-client',
    DISCORD_CLIENT_SECRET='test-secret',
    DISCORD_REDIRECT_URI='http://localhost:3000/callback',
)
class DiscordAuthApiTests(APITestCase):
    def setUp(self):
        self.url = '/api/auth/discord/'

    def test_requires_code_or_token(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.post')
    def test_token_exchange_failure(self, mock_post):
        mock_post.return_value = DummyResponse(400, {'error': 'invalid'})

        response = self.client.post(
            self.url,
            {'code': 'bad'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_user_fetch_failure(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(400, {'error': 'invalid'})

        response = self.client.post(
            self.url,
            {'code': 'code'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_create_user_from_discord(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(
            200,
            {
                'id': '123',
                'username': 'discorduser',
                'global_name': 'Discord User',
                'email': 'discord@example.com',
                'verified': True,
            },
        )

        response = self.client.post(
            self.url,
            {'code': 'code', 'redirect_uri': 'http://localhost:3000/callback'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['created'])
        self.assertFalse(data.get('linked'))
        self.assertEqual(data['user']['email'], 'discord@example.com')
        self.assertTrue(SocialAccount.objects.filter(provider='discord', uid='123').exists())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_link_conflict(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(
            200,
            {
                'id': '999',
                'username': 'conflict_user',
            },
        )

        owner = User.objects.create_user(username='owner', email='')
        SocialAccount.objects.create(
            user=owner,
            provider='discord',
            uid='999',
            extra_data={'id': '999'},
        )

        other = User.objects.create_user(username='other', email='')
        self.client.force_authenticate(user=other)

        response = self.client.post(self.url, {'code': 'code'}, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertIn('error', response.json())
