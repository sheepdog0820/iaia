from unittest import mock

from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_live_endpoint_returns_200(self):
        response = self.client.get('/health/live/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['check'], 'live')

    def test_ready_endpoint_returns_200(self):
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['check'], 'ready')
        self.assertEqual(payload['checks']['database'], 'ok')
        self.assertEqual(payload['checks']['cache'], 'ok')

    @mock.patch('tableno.health_views._check_database', side_effect=RuntimeError('db unavailable'))
    def test_ready_endpoint_returns_503_when_dependency_fails(self, _mock_db_check):
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload['status'], 'degraded')
        self.assertIn('database', payload['errors'])
        self.assertTrue(payload['checks']['database'].startswith('error:'))
