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
            'STRIPE_CHECKOUT_ENABLED': 'False',
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

    def test_operational_billing_logger_is_routed_to_tableno_handlers(self):
        payload = self.run_settings_probe(
            expression='''
import json
from tableno import settings_production as settings
logger_config = settings.LOGGING['loggers']['tableno']
print(json.dumps({
    'tableno_handlers': logger_config['handlers'],
    'tableno_level': logger_config['level'],
    'tableno_propagate': logger_config['propagate'],
}))
''',
        )

        self.assertTrue(payload['tableno_handlers'])
        self.assertEqual(payload['tableno_level'], 'INFO')
        self.assertFalse(payload['tableno_propagate'])

    def test_mail_transport_defaults_use_smtp(self):
        payload = self.run_settings_probe(
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "email_backend": settings.EMAIL_BACKEND,
    "email_host": settings.EMAIL_HOST,
    "email_port": settings.EMAIL_PORT,
    "email_use_tls": settings.EMAIL_USE_TLS,
}))
''',
        )

        self.assertEqual(
            payload['email_backend'],
            'django.core.mail.backends.smtp.EmailBackend',
        )
        self.assertEqual(payload['email_host'], 'smtp.gmail.com')
        self.assertEqual(payload['email_port'], 587)
        self.assertTrue(payload['email_use_tls'])

    def test_mail_transport_can_be_overridden_from_env(self):
        payload = self.run_settings_probe(
            {
                'EMAIL_HOST': 'smtp.example.test',
                'EMAIL_PORT': '2525',
                'EMAIL_USE_TLS': 'False',
                'EMAIL_HOST_USER': 'mailer@example.test',
                'EMAIL_HOST_PASSWORD': 'mail-secret',
            },
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "email_host": settings.EMAIL_HOST,
    "email_port": settings.EMAIL_PORT,
    "email_use_tls": settings.EMAIL_USE_TLS,
    "email_host_user": settings.EMAIL_HOST_USER,
    "email_host_password": settings.EMAIL_HOST_PASSWORD,
}))
''',
        )

        self.assertEqual(payload['email_host'], 'smtp.example.test')
        self.assertEqual(payload['email_port'], 2525)
        self.assertFalse(payload['email_use_tls'])
        self.assertEqual(payload['email_host_user'], 'mailer@example.test')
        self.assertEqual(payload['email_host_password'], 'mail-secret')

    def test_mail_identity_defaults_use_tableno_addresses(self):
        payload = self.run_settings_probe()

        self.assertEqual(payload['contact_email'], 'support@tableno.jp')
        self.assertEqual(payload['support_email'], 'support@tableno.jp')
        self.assertEqual(payload['default_from_email'], 'noreply@tableno.jp')
        self.assertEqual(payload['server_email'], 'noreply@tableno.jp')
        self.assertEqual(payload['admins'], [['Admin', 'support@tableno.jp']])

    def test_production_authentication_settings_require_verified_email(self):
        payload = self.run_settings_probe(
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "account_login_methods": sorted(settings.ACCOUNT_LOGIN_METHODS),
    "account_signup_fields": settings.ACCOUNT_SIGNUP_FIELDS,
    "account_email_verification": settings.ACCOUNT_EMAIL_VERIFICATION,
    "account_prevent_enumeration": settings.ACCOUNT_PREVENT_ENUMERATION,
    "socialaccount_email_required": settings.SOCIALACCOUNT_EMAIL_REQUIRED,
    "account_forms": settings.ACCOUNT_FORMS,
}))
''',
        )

        self.assertEqual(payload['account_login_methods'], ['email'])
        self.assertEqual(
            payload['account_signup_fields'],
            ['email*', 'password1*', 'password2*'],
        )
        self.assertEqual(payload['account_email_verification'], 'mandatory')
        self.assertTrue(payload['account_prevent_enumeration'])
        self.assertTrue(payload['socialaccount_email_required'])
        self.assertEqual(
            payload['account_forms']['reset_password'],
            'accounts.forms.CustomPasswordResetForm',
        )

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
    "stripe_checkout_enabled": settings.STRIPE_CHECKOUT_ENABLED,
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
        self.assertFalse(payload['stripe_checkout_enabled'])
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

    def test_billing_checkout_can_be_enabled_explicitly_after_verification(self):
        payload = self.run_settings_probe(
            {'STRIPE_CHECKOUT_ENABLED': 'True'},
            expression='''
import json
from tableno import settings_production as settings
print(json.dumps({
    "stripe_checkout_enabled": settings.STRIPE_CHECKOUT_ENABLED,
}))
''',
        )

        self.assertTrue(payload['stripe_checkout_enabled'])

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

    def test_deploy_check_passes_with_ci_like_production_environment(self):
        result = subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy'],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                'SECRET_KEY': 'test-secret-key-for-deploy-check-with-enough-length-12345',
                'DJANGO_SETTINGS_MODULE': 'tableno.settings_production',
                'ENVIRONMENT': 'staging',
                'ALLOWED_HOSTS': 'localhost',
                'CSRF_TRUSTED_ORIGINS': 'http://localhost',
                'SITE_ID': '1',
                'DB_ENGINE': 'postgres',
                'DB_NAME': 'tableno_ci',
                'DB_USER': 'tableno_ci',
                'DB_PASSWORD': 'tableno_ci_password',
                'DB_HOST': 'localhost',
                'DB_PORT': '5432',
                'USE_REDIS_CACHE': 'False',
                'USE_S3_STORAGE': 'False',
                'STRIPE_SECRET_KEY': 'sk_test_ci_secret',
                'STRIPE_WEBHOOK_SECRET': 'whsec_ci_secret',
                'STRIPE_PREMIUM_PRICE_ID': 'price_ci_monthly',
                'PUBLIC_SITE_URL': 'https://staging.example.com',
                'PREMIUM_PRICE_LABEL': 'CI test premium plan',
                'LEGAL_PAYMENT_METHOD': 'Credit card via Stripe Checkout.',
                'LEGAL_PAYMENT_TIMING': 'Charged when the subscription starts.',
                'LEGAL_SERVICE_DELIVERY_TIMING': 'Premium access starts after webhook processing.',
                'LEGAL_CANCELLATION_METHOD': 'Users can cancel from the premium management page.',
                'LEGAL_CANCELLATION_EFFECT': 'Access remains active until the paid period ends.',
                'LEGAL_REFUND_POLICY': 'Refunds are handled by support after review.',
                'LEGAL_SELLER_NAME': 'Tableno CI',
                'LEGAL_SELLER_ADDRESS': '1-1 CI Test Address',
                'LEGAL_SELLER_PHONE': '000-0000-0000',
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('System check identified no issues', result.stdout)
