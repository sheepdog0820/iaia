"""
Runtime environment selector.

APP_ENV values:
- local
- aws-pre
- aws-prod
"""

from __future__ import annotations

import os


_APP_ENV_ALIASES = {
    'local': 'local',
    'dev': 'local',
    'development': 'local',
    'aws-pre': 'aws-pre',
    'aws-preprod': 'aws-pre',
    'aws-stg': 'aws-pre',
    'aws-staging': 'aws-pre',
    'pre': 'aws-pre',
    'preprod': 'aws-pre',
    'stg': 'aws-pre',
    'staging': 'aws-pre',
    'aws-prod': 'aws-prod',
    'aws-production': 'aws-prod',
    'prod': 'aws-prod',
    'production': 'aws-prod',
}


def _normalize_app_env(raw_value: str | None) -> str:
    value = (raw_value or 'local').strip().lower()
    if value not in _APP_ENV_ALIASES:
        supported = ', '.join(sorted(set(_APP_ENV_ALIASES.values())))
        raise RuntimeError(
            f'Unsupported APP_ENV: {raw_value!r}. '
            f'Use one of: {supported}'
        )
    return _APP_ENV_ALIASES[value]


def configure_runtime_environment() -> str:
    """
    Configure DJANGO_SETTINGS_MODULE from APP_ENV unless already specified.
    Returns the normalized APP_ENV value.
    """
    app_env = _normalize_app_env(os.environ.get('APP_ENV'))

    if app_env == 'local':
        os.environ.setdefault('ENV_FILE', '.env.development')
        os.environ.setdefault('ENVIRONMENT', 'development')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings')
        return app_env

    if app_env == 'aws-pre':
        # AWS runtime should rely on environment variables / secrets injection,
        # not local .env files.
        os.environ.setdefault('ENVIRONMENT', 'staging')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings_production')
        return app_env

    # aws-prod
    # AWS runtime should rely on environment variables / secrets injection,
    # not local .env files.
    os.environ.setdefault('ENVIRONMENT', 'production')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tableno.settings_production')
    return app_env
