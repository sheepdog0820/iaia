import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[2]


class ProductionSettingsTests(TestCase):
    def run_settings_probe(self, overrides=None, expression=None):
        env = {
            'APP_ENV': 'aws-prod',
            'SECRET_KEY': 'test-production-secret',
            'ALLOWED_HOSTS': 'tableno.jp,www.tableno.jp',
            'CSRF_TRUSTED_ORIGINS': 'https://tableno.jp,https://www.tableno.jp',
            'SITE_ID': '1',
            'DB_ENGINE': 'mysql',
            'DB_NAME': 'tableno',
            'DB_USER': 'tableno',
            'DB_PASSWORD': 'database-password',
            'DB_HOST': 'database.example.internal',
            'DB_PORT': '3306',
            'REDIS_URL': 'redis://cache.example.internal:6379/1',
            'USE_S3_STORAGE': 'False',
            'LOG_TO_STDOUT': 'True',
            'ENABLE_FILE_LOGGING': 'False',
        }
        env.update(overrides or {})
        probe = expression or '''
import json
from tableno import settings_production as settings
print(json.dumps({
    "database": settings.DATABASES["default"],
    "cache": settings.CACHES["default"],
    "proxy_header": settings.SECURE_PROXY_SSL_HEADER,
    "forwarded_host": settings.USE_X_FORWARDED_HOST,
    "static_url": settings.STATIC_URL,
    "media_url": settings.MEDIA_URL,
    "storages": getattr(settings, "STORAGES", None),
    "websocket_notifications_enabled": settings.WEBSOCKET_NOTIFICATIONS_ENABLED,
    "contact_email": settings.CONTACT_EMAIL,
    "support_email": settings.SUPPORT_EMAIL,
    "default_from_email": settings.DEFAULT_FROM_EMAIL,
    "server_email": settings.SERVER_EMAIL,
    "admins": settings.ADMINS,
}))
'''
        result = subprocess.run(
            [sys.executable, '-c', probe],
            cwd=REPO_ROOT,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip())

    def test_proxy_and_mysql_tls_settings(self):
        payload = self.run_settings_probe(
            {
                'DB_SSL_MODE': 'VERIFY_IDENTITY',
                'DB_SSL_CA': '/certs/rds-ca.pem',
                'REDIS_URL': 'rediss://cache.example.internal:6379/1',
                'REDIS_SSL_CERT_REQS': 'required',
            }
        )

        self.assertEqual(
            payload['proxy_header'],
            ['HTTP_X_FORWARDED_PROTO', 'https'],
        )
        self.assertTrue(payload['forwarded_host'])
        self.assertTrue(payload['websocket_notifications_enabled'])
        self.assertEqual(
            payload['database']['OPTIONS']['ssl'],
            {
                'ssl_mode': 'VERIFY_IDENTITY',
                'ca': '/certs/rds-ca.pem',
            },
        )
        self.assertEqual(
            payload['cache']['OPTIONS']['CONNECTION_POOL_KWARGS']['ssl_cert_reqs'],
            'required',
        )

    def test_postgresql_tls_settings(self):
        payload = self.run_settings_probe(
            {
                'DB_ENGINE': 'postgresql',
                'DB_PORT': '5432',
                'DB_SSL_MODE': 'verify-full',
                'DB_SSL_CA': '/certs/rds-ca.pem',
            }
        )

        self.assertEqual(
            payload['database']['ENGINE'],
            'django.db.backends.postgresql',
        )
        self.assertEqual(
            payload['database']['OPTIONS'],
            {
                'sslmode': 'verify-full',
                'sslrootcert': '/certs/rds-ca.pem',
            },
        )

    def test_s3_storage_settings(self):
        payload = self.run_settings_probe(
            {
                'USE_S3_STORAGE': 'True',
                'AWS_STORAGE_BUCKET_NAME': 'tableno-assets',
                'AWS_S3_REGION_NAME': 'ap-northeast-1',
                'AWS_S3_CUSTOM_DOMAIN': 'assets.tableno.jp',
            }
        )

        self.assertEqual(payload['static_url'], 'https://assets.tableno.jp/static/')
        self.assertEqual(payload['media_url'], 'https://assets.tableno.jp/media/')
        self.assertEqual(
            payload['storages']['default']['BACKEND'],
            'storages.backends.s3.S3Storage',
        )
        self.assertEqual(
            payload['storages']['staticfiles']['BACKEND'],
            'storages.backends.s3.S3Storage',
        )

    def test_mail_identity_defaults_use_tableno_addresses(self):
        payload = self.run_settings_probe()

        self.assertEqual(payload['contact_email'], 'support@tableno.jp')
        self.assertEqual(payload['support_email'], 'support@tableno.jp')
        self.assertEqual(payload['default_from_email'], 'noreply@tableno.jp')
        self.assertEqual(payload['server_email'], 'noreply@tableno.jp')
        self.assertEqual(payload['admins'], [['Admin', 'support@tableno.jp']])

    def test_missing_required_setting_fails_fast(self):
        result = subprocess.run(
            [sys.executable, '-c', 'import tableno.settings_production'],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                'APP_ENV': 'aws-prod',
                'SECRET_KEY': 'test-production-secret',
                'ALLOWED_HOSTS': '',
                'CSRF_TRUSTED_ORIGINS': 'https://tableno.jp',
                'SITE_ID': '1',
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ALLOWED_HOSTS is required', result.stderr)
