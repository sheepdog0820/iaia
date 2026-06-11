import os
from unittest import TestCase
from unittest.mock import patch

from tableno.runtime_env import configure_runtime_environment


class RuntimeEnvSwitchTests(TestCase):
    def test_local_profile_sets_base_settings(self):
        with patch.dict(os.environ, {'APP_ENV': 'local'}, clear=True):
            env = configure_runtime_environment()
            self.assertEqual(env, 'local')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'tableno.settings')
            self.assertEqual(os.environ['ENV_FILE'], '.env.development')
            self.assertEqual(os.environ['ENVIRONMENT'], 'development')

    def test_aws_pre_profile_sets_production_settings(self):
        with patch.dict(os.environ, {'APP_ENV': 'aws-pre'}, clear=True):
            env = configure_runtime_environment()
            self.assertEqual(env, 'aws-pre')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'tableno.settings_production')
            self.assertNotIn('ENV_FILE', os.environ)
            self.assertEqual(os.environ['ENVIRONMENT'], 'staging')

    def test_aws_prod_profile_sets_production_settings(self):
        with patch.dict(os.environ, {'APP_ENV': 'aws-prod'}, clear=True):
            env = configure_runtime_environment()
            self.assertEqual(env, 'aws-prod')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'tableno.settings_production')
            self.assertNotIn('ENV_FILE', os.environ)
            self.assertEqual(os.environ['ENVIRONMENT'], 'production')

    def test_explicit_django_settings_module_is_respected(self):
        with patch.dict(
            os.environ,
            {
                'APP_ENV': 'aws-pre',
                'DJANGO_SETTINGS_MODULE': 'tableno.custom_settings',
            },
            clear=True,
        ):
            env = configure_runtime_environment()
            self.assertEqual(env, 'aws-pre')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'tableno.custom_settings')
            self.assertNotIn('ENV_FILE', os.environ)

    def test_alias_value_is_supported(self):
        with patch.dict(os.environ, {'APP_ENV': 'staging'}, clear=True):
            env = configure_runtime_environment()
            self.assertEqual(env, 'aws-pre')

    def test_unsupported_value_raises(self):
        with patch.dict(os.environ, {'APP_ENV': 'unknown-env'}, clear=True):
            with self.assertRaises(RuntimeError):
                configure_runtime_environment()
