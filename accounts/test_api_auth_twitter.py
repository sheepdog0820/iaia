from types import SimpleNamespace
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
    TWITTER_CLIENT_ID='test-client',
    TWITTER_CLIENT_SECRET='test-secret',
    TWITTER_REDIRECT_URI='http://localhost:3000/callback',
)
class TwitterAuthApiTests(APITestCase):
    def setUp(self):
        self.url = '/api/auth/twitter/'

    def test_requires_code_and_verifier(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.post')
    def test_token_exchange_failure(self, mock_post):
        mock_post.return_value = DummyResponse(400, {'error': 'invalid'})

        response = self.client.post(
            self.url,
            {'code': 'bad', 'code_verifier': 'verifier'},
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
            {'code': 'code', 'code_verifier': 'verifier'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_create_user_from_twitter(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(
            200,
            {'data': {'id': '123', 'username': 'xuser', 'name': 'X User'}}
        )

        response = self.client.post(
            self.url,
            {'code': 'code', 'code_verifier': 'verifier'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['created'])
        self.assertFalse(data['linked'])
        self.assertEqual(data['user']['nickname'], 'X User')
        self.assertTrue(SocialAccount.objects.filter(provider='twitter_oauth2', uid='123').exists())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_link_to_authenticated_user(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(
            200,
            {'data': {'id': '456', 'username': 'linkeduser', 'name': 'Linked User'}}
        )

        user = User.objects.create_user(
            username='existing',
            email='',
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            self.url,
            {'code': 'code', 'code_verifier': 'verifier'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['created'])
        self.assertTrue(data['linked'])
        self.assertEqual(data['user']['id'], user.id)
        self.assertTrue(SocialAccount.objects.filter(provider='twitter_oauth2', uid='456', user=user).exists())

    @patch('accounts.views.api_auth_views.requests.get')
    @patch('accounts.views.api_auth_views.requests.post')
    def test_link_conflict(self, mock_post, mock_get):
        mock_post.return_value = DummyResponse(200, {'access_token': 'token'})
        mock_get.return_value = DummyResponse(
            200,
            {'data': {'id': '789', 'username': 'conflict', 'name': 'Conflict'}}
        )

        owner = User.objects.create_user(username='owner', email='')
        SocialAccount.objects.create(
            user=owner,
            provider='twitter_oauth2',
            uid='789',
            extra_data={'id': '789'}
        )

        other = User.objects.create_user(username='other', email='')
        self.client.force_authenticate(user=other)

        response = self.client.post(
            self.url,
            {'code': 'code', 'code_verifier': 'verifier'},
            format='json'
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('error', response.json())
