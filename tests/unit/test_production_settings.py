import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[2]


class ProductionSettingsTests(TestCase):
    def run_settings_probe(self, overrides=None, expression=None, check=True):
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
            'STRIPE_SECRET_KEY': 'sk_live_test',
            'STRIPE_WEBHOOK_SECRET': 'whsec_test',
            'STRIPE_PREMIUM_PRICE_ID': 'price_test',
            'STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID': 'bpc_live_test',
            'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE': 'False',
            'PUBLIC_SITE_URL': 'https://tableno.jp',
            'PREMIUM_PRICE_LABEL': '月額500円',
            'LEGAL_PAYMENT_METHOD': 'クレジットカード',
            'LEGAL_PAYMENT_TIMING': '初回申し込み時および毎月の更新日に課金します。',
            'LEGAL_SERVICE_DELIVERY_TIMING': '決済完了後ただちに提供します。',
            'LEGAL_CANCELLATION_METHOD': 'プレミアム管理画面から解約できます。',
            'LEGAL_CANCELLATION_EFFECT': '解約後も支払い済み期間の終了まで利用できます。',
            'LEGAL_REFUND_POLICY': '返金は原則受け付けません。',
            'LEGAL_SELLER_NAME': 'テスト販売者',
            'LEGAL_SELLER_ADDRESS': '東京都千代田区1-1-1',
            'LEGAL_SELLER_PHONE': '03-0000-0000',
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
        if not check:
            return result
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

    def test_billing_production_settings_are_loaded_from_env(self):
        payload = self.run_settings_probe(
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "stripe_secret_key": settings.STRIPE_SECRET_KEY,
    "stripe_webhook_secret": settings.STRIPE_WEBHOOK_SECRET,
    "stripe_premium_price_id": settings.STRIPE_PREMIUM_PRICE_ID,
    "stripe_customer_portal_configuration_id": settings.STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID,
    "stripe_revoke_on_refund_or_dispute": settings.STRIPE_REVOKE_ON_REFUND_OR_DISPUTE,
    "public_site_url": settings.PUBLIC_SITE_URL,
    "premium_price_label": settings.PREMIUM_PRICE_LABEL,
    "legal_payment_method": settings.LEGAL_PAYMENT_METHOD,
    "legal_payment_timing": settings.LEGAL_PAYMENT_TIMING,
    "legal_service_delivery_timing": settings.LEGAL_SERVICE_DELIVERY_TIMING,
    "legal_cancellation_method": settings.LEGAL_CANCELLATION_METHOD,
    "legal_cancellation_effect": settings.LEGAL_CANCELLATION_EFFECT,
    "legal_refund_policy": settings.LEGAL_REFUND_POLICY,
    "legal_seller_name": settings.LEGAL_SELLER_NAME,
    "legal_seller_address": settings.LEGAL_SELLER_ADDRESS,
    "legal_seller_phone": settings.LEGAL_SELLER_PHONE,
    "premium_expiration_task": settings.CELERY_BEAT_SCHEDULE["expire-premium-access"]["task"],
    "premium_expiration_schedule": settings.CELERY_BEAT_SCHEDULE["expire-premium-access"]["schedule"],
}))
''',
        )

        self.assertEqual(payload['stripe_secret_key'], 'sk_live_test')
        self.assertEqual(payload['stripe_webhook_secret'], 'whsec_test')
        self.assertEqual(payload['stripe_premium_price_id'], 'price_test')
        self.assertEqual(payload['stripe_customer_portal_configuration_id'], 'bpc_live_test')
        self.assertFalse(payload['stripe_revoke_on_refund_or_dispute'])
        self.assertEqual(payload['public_site_url'], 'https://tableno.jp')
        self.assertEqual(payload['premium_price_label'], '月額500円')
        self.assertEqual(payload['legal_payment_method'], 'クレジットカード')
        self.assertEqual(payload['legal_payment_timing'], '初回申し込み時および毎月の更新日に課金します。')
        self.assertEqual(payload['legal_service_delivery_timing'], '決済完了後ただちに提供します。')
        self.assertEqual(payload['legal_cancellation_method'], 'プレミアム管理画面から解約できます。')
        self.assertEqual(payload['legal_cancellation_effect'], '解約後も支払い済み期間の終了まで利用できます。')
        self.assertEqual(payload['legal_refund_policy'], '返金は原則受け付けません。')
        self.assertEqual(payload['legal_seller_name'], 'テスト販売者')
        self.assertEqual(payload['legal_seller_address'], '東京都千代田区1-1-1')
        self.assertEqual(payload['legal_seller_phone'], '03-0000-0000')
        self.assertEqual(
            payload['premium_expiration_task'],
            'schedules.tasks.expire_premium_access',
        )
        self.assertLessEqual(payload['premium_expiration_schedule'], 3600.0)

    def test_placeholder_price_label_setting_fails_fast(self):
        result = self.run_settings_probe(
            {
                'PREMIUM_PRICE_LABEL': '月額料金はStripe Checkout画面に表示される金額',
            },
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PREMIUM_PRICE_LABEL must be set to a production value', result.stderr)

    def test_production_rejects_stripe_test_secret_key(self):
        result = self.run_settings_probe(
            {
                'APP_ENV': 'aws-prod',
                'ENVIRONMENT': 'production',
                'STRIPE_SECRET_KEY': 'sk_test_should_not_be_used_in_prod',
            },
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('STRIPE_SECRET_KEY must be a live key in production', result.stderr)

    def test_staging_allows_stripe_test_secret_key(self):
        payload = self.run_settings_probe(
            {
                'APP_ENV': 'aws-pre',
                'ENVIRONMENT': 'staging',
                'STRIPE_SECRET_KEY': 'sk_test_staging',
            },
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "environment": settings.ENVIRONMENT,
    "stripe_secret_key": settings.STRIPE_SECRET_KEY,
}))
''',
        )

        self.assertEqual(payload['environment'], 'staging')
        self.assertEqual(payload['stripe_secret_key'], 'sk_test_staging')

    def test_redis_can_be_disabled_for_low_cost_aws_pre(self):
        payload = self.run_settings_probe(
            {
                'APP_ENV': 'aws-pre',
                'USE_REDIS_CACHE': 'False',
                'WEBSOCKET_NOTIFICATIONS_ENABLED': 'False',
                'SESSION_ENGINE': 'django.contrib.sessions.backends.db',
                'CELERY_BROKER_URL': '',
                'CELERY_RESULT_BACKEND': '',
            },
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "cache": settings.CACHES["default"],
    "session_engine": settings.SESSION_ENGINE,
    "channel_layer": settings.CHANNEL_LAYERS["default"],
    "websocket_notifications_enabled": settings.WEBSOCKET_NOTIFICATIONS_ENABLED,
    "celery_broker_url": settings.CELERY_BROKER_URL,
    "celery_result_backend": settings.CELERY_RESULT_BACKEND,
}))
''',
        )

        self.assertEqual(
            payload['cache']['BACKEND'],
            'django.core.cache.backends.locmem.LocMemCache',
        )
        self.assertEqual(
            payload['session_engine'],
            'django.contrib.sessions.backends.db',
        )
        self.assertEqual(
            payload['channel_layer']['BACKEND'],
            'channels.layers.InMemoryChannelLayer',
        )
        self.assertFalse(payload['websocket_notifications_enabled'])
        self.assertEqual(payload['celery_broker_url'], '')
        self.assertEqual(payload['celery_result_backend'], '')

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

    def test_missing_billing_setting_fails_fast(self):
        result = subprocess.run(
            [sys.executable, '-c', 'import tableno.settings_production'],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                'APP_ENV': 'aws-prod',
                'SECRET_KEY': 'test-production-secret',
                'ALLOWED_HOSTS': 'tableno.jp',
                'CSRF_TRUSTED_ORIGINS': 'https://tableno.jp',
                'SITE_ID': '1',
                'DB_ENGINE': 'mysql',
                'DB_NAME': 'tableno',
                'DB_USER': 'tableno',
                'DB_PASSWORD': 'database-password',
                'DB_HOST': 'database.example.internal',
                'REDIS_URL': 'redis://cache.example.internal:6379/1',
                'USE_S3_STORAGE': 'False',
                'STRIPE_SECRET_KEY': '',
                'STRIPE_WEBHOOK_SECRET': 'whsec_test',
                'STRIPE_PREMIUM_PRICE_ID': 'price_test',
                'PUBLIC_SITE_URL': 'https://tableno.jp',
                'PREMIUM_PRICE_LABEL': '月額500円',
                'LEGAL_SELLER_NAME': 'テスト販売者',
                'LEGAL_SELLER_ADDRESS': '東京都千代田区1-1-1',
                'LEGAL_SELLER_PHONE': '03-0000-0000',
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('STRIPE_SECRET_KEY is required', result.stderr)

    def test_placeholder_legal_disclosure_setting_fails_fast(self):
        result = subprocess.run(
            [sys.executable, '-c', 'import tableno.settings_production'],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                'APP_ENV': 'aws-prod',
                'SECRET_KEY': 'test-production-secret',
                'ALLOWED_HOSTS': 'tableno.jp',
                'CSRF_TRUSTED_ORIGINS': 'https://tableno.jp',
                'SITE_ID': '1',
                'DB_ENGINE': 'mysql',
                'DB_NAME': 'tableno',
                'DB_USER': 'tableno',
                'DB_PASSWORD': 'database-password',
                'DB_HOST': 'database.example.internal',
                'REDIS_URL': 'redis://cache.example.internal:6379/1',
                'USE_S3_STORAGE': 'False',
                'STRIPE_SECRET_KEY': 'sk_live_test',
                'STRIPE_WEBHOOK_SECRET': 'whsec_test',
                'STRIPE_PREMIUM_PRICE_ID': 'price_test',
                'PUBLIC_SITE_URL': 'https://tableno.jp',
                'PREMIUM_PRICE_LABEL': '月額500円',
                'LEGAL_PAYMENT_METHOD': 'クレジットカード',
                'LEGAL_PAYMENT_TIMING': '初回申し込み時および毎月の更新日に課金します。',
                'LEGAL_SERVICE_DELIVERY_TIMING': '決済完了後ただちに提供します。',
                'LEGAL_CANCELLATION_METHOD': 'プレミアム管理画面から解約できます。',
                'LEGAL_CANCELLATION_EFFECT': '解約後も支払い済み期間の終了まで利用できます。',
                'LEGAL_REFUND_POLICY': '返金は原則受け付けません。',
                'LEGAL_SELLER_NAME': 'テスト販売者',
                'LEGAL_SELLER_ADDRESS': '請求があった場合、遅滞なく開示します。',
                'LEGAL_SELLER_PHONE': '03-0000-0000',
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('LEGAL_SELLER_ADDRESS must be set to a production value', result.stderr)
