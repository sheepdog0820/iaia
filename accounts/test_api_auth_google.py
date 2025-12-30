from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class DummyFlow:
    def __init__(self):
        self.redirect_uri = None
        self.credentials = None

    def fetch_token(self, code):
        self.credentials = SimpleNamespace(id_token='dummy-id-token')


@override_settings(GOOGLE_OAUTH_CLIENT_ID='test-client', GOOGLE_OAUTH_CLIENT_SECRET='test-secret')
class GoogleAuthApiTests(APITestCase):
    def setUp(self):
        self.url = '/api/auth/google/'

    def test_google_auth_requires_credentials(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.id_token.verify_oauth2_token')
    def test_google_auth_id_token_creates_user(self, mock_verify):
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'email': 'idtoken.user@example.com',
            'given_name': 'IdToken',
            'family_name': 'User',
            'name': 'IdToken User',
            'picture': 'http://example.com/pic.jpg',
            'email_verified': True,
        }

        response = self.client.post(self.url, {'id_token': 'fake'}, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertTrue(data['created'])
        self.assertEqual(data['user']['email'], 'idtoken.user@example.com')

        self.assertTrue(User.objects.filter(email='idtoken.user@example.com').exists())

    @patch('accounts.views.api_auth_views.id_token.verify_oauth2_token')
    def test_google_auth_id_token_invalid_issuer(self, mock_verify):
        mock_verify.return_value = {
            'iss': 'https://invalid.example.com',
            'email': 'badissuer@example.com',
            'email_verified': True,
        }

        response = self.client.post(self.url, {'id_token': 'fake'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.id_token.verify_oauth2_token')
    def test_google_auth_id_token_unverified_email(self, mock_verify):
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'email': 'unverified@example.com',
            'email_verified': False,
        }

        response = self.client.post(self.url, {'id_token': 'fake'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.requests.get')
    def test_google_auth_access_token_success(self, mock_get):
        mock_get.return_value = DummyResponse(
            200,
            {
                'email': 'access.user@example.com',
                'given_name': 'Access',
                'family_name': 'User',
                'name': 'Access User',
                'picture': 'http://example.com/pic.jpg',
                'verified_email': True,
            },
        )

        response = self.client.post(self.url, {'access_token': 'fake'}, format='json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertTrue(data['created'])
        self.assertEqual(data['user']['email'], 'access.user@example.com')

    @patch('accounts.views.api_auth_views.requests.get')
    def test_google_auth_access_token_invalid(self, mock_get):
        mock_get.return_value = DummyResponse(400, {'error': 'invalid'})

        response = self.client.post(self.url, {'access_token': 'fake'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('accounts.views.api_auth_views.Flow.from_client_config')
    @patch('accounts.views.api_auth_views.id_token.verify_oauth2_token')
    def test_google_auth_code_flow_success(self, mock_verify, mock_flow):
        mock_flow.return_value = DummyFlow()
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'email': 'code.user@example.com',
            'given_name': 'Code',
            'family_name': 'User',
            'name': 'Code User',
            'email_verified': True,
        }

        response = self.client.post(
            self.url,
            {'code': 'fake-code', 'redirect_uri': 'http://localhost:3000'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertTrue(data['created'])
        self.assertEqual(data['user']['email'], 'code.user@example.com')
