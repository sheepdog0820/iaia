import re
import ssl
from pathlib import Path
from unittest import TestCase

from celery import Celery
from redis import SSLConnection


class RedisTLSInfrastructureTests(TestCase):
    def setUp(self):
        self.terraform = (Path(__file__).resolve().parents[2] / "infrastructure/terraform/main.tf").read_text(
            encoding="utf-8"
        )

    def test_celery_broker_and_result_backend_require_trusted_certificates(self):
        parameter = re.search(r'celery_redis_url\s*=.*?ssl_cert_reqs=([^"\s]+)', self.terraform)
        self.assertIsNotNone(parameter)
        url = f"rediss://cache.example.test:6379/0?ssl_cert_reqs={parameter.group(1)}"
        app = Celery("tls-configuration-test", broker=url, backend=url, set_as_current=False)
        try:
            self.assertEqual(app.connection().ssl["ssl_cert_reqs"], ssl.CERT_REQUIRED)
            self.assertEqual(app.backend.connparams["ssl_cert_reqs"], ssl.CERT_REQUIRED)
        finally:
            app.close()

    def test_cache_client_requires_trusted_certificates(self):
        parameter = re.search(r'name\s*=\s*"REDIS_SSL_CERT_REQS",\s*value\s*=\s*"([^"]+)"', self.terraform)
        self.assertIsNotNone(parameter)
        connection = SSLConnection(host="cache.example.test", ssl_cert_reqs=parameter.group(1))
        self.assertEqual(connection.cert_reqs, ssl.CERT_REQUIRED)
