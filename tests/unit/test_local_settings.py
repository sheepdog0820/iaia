import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[2]


class LocalSettingsTests(TestCase):
    def test_local_settings_load_monthly_and_yearly_stripe_price_ids_from_env_file(self):
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as handle:
            handle.write('SECRET_KEY=test-local-secret\n')
            handle.write('STRIPE_PREMIUM_PRICE_ID=price_monthly_local\n')
            handle.write('STRIPE_PREMIUM_YEARLY_PRICE_ID=price_yearly_local\n')
            handle.write('STRIPE_PREMIUM_EXPECTED_CURRENCY=jpy\n')
            handle.write('STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT=480\n')
            handle.write('STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT=4800\n')
            env_file = handle.name

        try:
            env = os.environ.copy()
            env.pop('STRIPE_PREMIUM_PRICE_ID', None)
            env.pop('STRIPE_PREMIUM_YEARLY_PRICE_ID', None)
            env.pop('STRIPE_PREMIUM_EXPECTED_CURRENCY', None)
            env.pop('STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT', None)
            env.pop('STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT', None)
            env.update({
                'APP_ENV': 'local',
                'ENV_FILE': env_file,
                'DJANGO_SETTINGS_MODULE': 'tableno.settings',
            })
            result = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    'import json; from django.conf import settings; '
                    'print(json.dumps({'
                    '"monthly": settings.STRIPE_PREMIUM_PRICE_ID, '
                    '"yearly": settings.STRIPE_PREMIUM_YEARLY_PRICE_ID, '
                    '"currency": settings.STRIPE_PREMIUM_EXPECTED_CURRENCY, '
                    '"monthly_amount": settings.STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT, '
                    '"yearly_amount": settings.STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT, '
                    '"app_env": settings.APP_ENV, '
                    '"environment": settings.ENVIRONMENT'
                    '}))',
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            Path(env_file).unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertEqual(payload['monthly'], 'price_monthly_local')
        self.assertEqual(payload['yearly'], 'price_yearly_local')
        self.assertEqual(payload['currency'], 'jpy')
        self.assertEqual(payload['monthly_amount'], '480')
        self.assertEqual(payload['yearly_amount'], '4800')
        self.assertEqual(payload['app_env'], 'local')
        self.assertEqual(payload['environment'], 'development')

    def test_local_settings_load_env_file_with_utf8_bom(self):
        with tempfile.NamedTemporaryFile('w', encoding='utf-8-sig', delete=False) as handle:
            handle.write('SECRET_KEY=test-local-secret-with-bom\n')
            handle.write('STRIPE_PREMIUM_PRICE_ID=price_monthly_bom\n')
            handle.write('STRIPE_PREMIUM_YEARLY_PRICE_ID=price_yearly_bom\n')
            env_file = handle.name

        try:
            env = os.environ.copy()
            env.pop('SECRET_KEY', None)
            env.pop('STRIPE_PREMIUM_PRICE_ID', None)
            env.pop('STRIPE_PREMIUM_YEARLY_PRICE_ID', None)
            env.update({
                'APP_ENV': 'local',
                'ENV_FILE': env_file,
                'DJANGO_SETTINGS_MODULE': 'tableno.settings',
            })
            result = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    'import json; from django.conf import settings; '
                    'print(json.dumps({'
                    '"secret": settings.SECRET_KEY, '
                    '"monthly": settings.STRIPE_PREMIUM_PRICE_ID, '
                    '"yearly": settings.STRIPE_PREMIUM_YEARLY_PRICE_ID'
                    '}))',
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            Path(env_file).unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertEqual(payload['secret'], 'test-local-secret-with-bom')
        self.assertEqual(payload['monthly'], 'price_monthly_bom')
        self.assertEqual(payload['yearly'], 'price_yearly_bom')

    def test_checkout_is_disabled_by_default_in_local_settings(self):
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as handle:
            handle.write('SECRET_KEY=test-local-secret\n')
            env_file = handle.name

        try:
            env = os.environ.copy()
            env.pop('STRIPE_CHECKOUT_ENABLED', None)
            env.update({
                'APP_ENV': 'local',
                'ENV_FILE': env_file,
                'DJANGO_SETTINGS_MODULE': 'tableno.settings',
            })

            result = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    'import json; from django.conf import settings; '
                    'print(json.dumps({"checkout_enabled": settings.STRIPE_CHECKOUT_ENABLED}))',
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            Path(env_file).unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertFalse(payload['checkout_enabled'])

    def test_checkout_can_be_enabled_explicitly_in_local_settings(self):
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as handle:
            handle.write('SECRET_KEY=test-local-secret\n')
            env_file = handle.name

        try:
            env = os.environ.copy()
            env.update({
                'APP_ENV': 'local',
                'ENV_FILE': env_file,
                'DJANGO_SETTINGS_MODULE': 'tableno.settings',
                'STRIPE_CHECKOUT_ENABLED': 'True',
            })

            result = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    'import json; from django.conf import settings; '
                    'print(json.dumps({"checkout_enabled": settings.STRIPE_CHECKOUT_ENABLED}))',
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            Path(env_file).unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertTrue(payload['checkout_enabled'])
