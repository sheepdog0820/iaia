"""
本番環境用設定ファイル
"""
import os
from pathlib import Path

from .settings import *  # noqa: F401,F403


def _split_env_list(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def _get_bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


WEBSOCKET_NOTIFICATIONS_ENABLED = _get_bool_env(
    'WEBSOCKET_NOTIFICATIONS_ENABLED',
    default=True,
)
USE_REDIS_CACHE = _get_bool_env('USE_REDIS_CACHE', default=True)


def _require_env(name):
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f'{name} is required for production/staging')
    return value.strip()


def _validate_env_pair(id_key, secret_key):
    identifier = os.environ.get(id_key, '').strip()
    secret = os.environ.get(secret_key, '').strip()
    if identifier and not secret:
        raise RuntimeError(f'{secret_key} is required when {id_key} is set')
    if secret and not identifier:
        raise RuntimeError(f'{id_key} is required when {secret_key} is set')


def _require_non_placeholder_env(name, placeholder_fragment=None, placeholder_fragments=()):
    value = _require_env(name)
    if placeholder_fragment and placeholder_fragment in value:
        raise RuntimeError(f'{name} must be set to a production value')
    if any(fragment in value for fragment in placeholder_fragments):
        raise RuntimeError(f'{name} must be set to a production value')
    return value


def _require_stripe_secret_key():
    value = _require_env('STRIPE_SECRET_KEY')
    if ENVIRONMENT == 'production' and not value.startswith('sk_live_'):
        raise RuntimeError('STRIPE_SECRET_KEY must be a live key in production')
    return value


def _build_s3_url(base_domain, bucket, region, location):
    prefix = location.strip('/')
    if base_domain:
        return f'https://{base_domain}/{prefix}/'
    return f'https://{bucket}.s3.{region}.amazonaws.com/{prefix}/'


# 環境ラベル（urls.py 側の media serve 判定でも使用）
ENVIRONMENT = os.environ.get('ENVIRONMENT', os.environ.get('DJANGO_ENV', 'production')).strip().lower()
if not ENVIRONMENT:
    ENVIRONMENT = 'production'

# セキュリティ設定
DEBUG = False
ALLOWED_HOSTS = _split_env_list(_require_env('ALLOWED_HOSTS'))
CSRF_TRUSTED_ORIGINS = _split_env_list(_require_env('CSRF_TRUSTED_ORIGINS'))

try:
    SITE_ID = int(_require_env('SITE_ID'))
except ValueError as exc:
    raise RuntimeError('SITE_ID must be an integer for production/staging') from exc

# セキュリティヘッダー
SECURE_SSL_REDIRECT = _get_bool_env('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _get_bool_env('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = _get_bool_env('SECURE_HSTS_PRELOAD', default=True)

# データベース設定（MySQL / PostgreSQL）
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').strip().lower()
DB_NAME = _require_env('DB_NAME')
DB_USER = _require_env('DB_USER')
DB_PASSWORD = _require_env('DB_PASSWORD')
DB_HOST = _require_env('DB_HOST')

if DB_ENGINE in ('mysql', 'mariadb'):
    db_backend = 'django.db.backends.mysql'
    db_default_port = '3306'
    db_options = {'charset': 'utf8mb4'}
elif DB_ENGINE in ('postgres', 'postgresql'):
    db_backend = 'django.db.backends.postgresql'
    db_default_port = '5432'
    db_options = {}
else:
    raise RuntimeError(f'Unsupported DB_ENGINE: {DB_ENGINE}')

DB_PORT = os.environ.get('DB_PORT', db_default_port)
DB_SSL_MODE = os.environ.get('DB_SSL_MODE', '').strip()
DB_SSL_CA = os.environ.get('DB_SSL_CA', '').strip()
if DB_SSL_MODE:
    if DB_ENGINE in ('mysql', 'mariadb'):
        db_options.setdefault('ssl', {})
        db_options['ssl']['ssl_mode'] = DB_SSL_MODE
    else:
        db_options['sslmode'] = DB_SSL_MODE
if DB_SSL_CA:
    if DB_ENGINE in ('mysql', 'mariadb'):
        db_options.setdefault('ssl', {})
        db_options['ssl']['ca'] = DB_SSL_CA
    else:
        db_options['sslrootcert'] = DB_SSL_CA

DATABASES = {
    'default': {
        'ENGINE': db_backend,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'CONN_MAX_AGE': 60,
        'OPTIONS': db_options,
    }
}

# キャッシュ・セッション・非同期設定
if USE_REDIS_CACHE:
    REDIS_URL = _require_env('REDIS_URL')
    cache_pool_kwargs = {'max_connections': int(os.environ.get('REDIS_MAX_CONNECTIONS', '50'))}
    redis_ssl_cert_reqs = os.environ.get('REDIS_SSL_CERT_REQS', '').strip()
    if REDIS_URL.startswith('rediss://') and redis_ssl_cert_reqs:
        cache_pool_kwargs['ssl_cert_reqs'] = redis_ssl_cert_reqs

    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': cache_pool_kwargs,
            },
            'KEY_PREFIX': 'tableno',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = os.environ.get(
        'SESSION_ENGINE',
        'django.contrib.sessions.backends.cache',
    )
    SESSION_CACHE_ALIAS = 'default'
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
                'capacity': 1000,
                'expiry': 60,
            },
        },
    }
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
else:
    REDIS_URL = ''
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': os.environ.get('CACHE_LOCATION', 'tableno-production'),
            'KEY_PREFIX': 'tableno',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = os.environ.get(
        'SESSION_ENGINE',
        'django.contrib.sessions.backends.db',
    )
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', '')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', '')

# 静的/メディア配信設定（S3利用時は STORAGES に切替）
USE_S3_STORAGE = _get_bool_env('USE_S3_STORAGE', default=False)
if USE_S3_STORAGE:
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS.append('storages')

    AWS_STORAGE_BUCKET_NAME = _require_env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = _require_env('AWS_S3_REGION_NAME')
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '').strip()
    AWS_S3_SIGNATURE_VERSION = os.environ.get('AWS_S3_SIGNATURE_VERSION', 's3v4').strip()
    AWS_S3_ADDRESSING_STYLE = os.environ.get('AWS_S3_ADDRESSING_STYLE', 'auto').strip()
    AWS_QUERYSTRING_AUTH = _get_bool_env('AWS_QUERYSTRING_AUTH', default=False)
    AWS_S3_CACHE_CONTROL = os.environ.get('AWS_S3_CACHE_CONTROL', 'max-age=86400, public').strip()
    AWS_STATIC_LOCATION = os.environ.get('AWS_STATIC_LOCATION', 'static').strip('/')
    AWS_MEDIA_LOCATION = os.environ.get('AWS_MEDIA_LOCATION', 'media').strip('/')

    s3_common_options = {
        'bucket_name': AWS_STORAGE_BUCKET_NAME,
        'region_name': AWS_S3_REGION_NAME,
        'signature_version': AWS_S3_SIGNATURE_VERSION,
        'addressing_style': AWS_S3_ADDRESSING_STYLE,
        'querystring_auth': AWS_QUERYSTRING_AUTH,
        'default_acl': None,
        'object_parameters': {
            'CacheControl': AWS_S3_CACHE_CONTROL,
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        s3_common_options['custom_domain'] = AWS_S3_CUSTOM_DOMAIN

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                **s3_common_options,
                'location': AWS_MEDIA_LOCATION,
                'file_overwrite': False,
            },
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                **s3_common_options,
                'location': AWS_STATIC_LOCATION,
                'file_overwrite': True,
            },
        },
    }

    STATIC_URL = _build_s3_url(
        AWS_S3_CUSTOM_DOMAIN,
        AWS_STORAGE_BUCKET_NAME,
        AWS_S3_REGION_NAME,
        AWS_STATIC_LOCATION,
    )
    MEDIA_URL = _build_s3_url(
        AWS_S3_CUSTOM_DOMAIN,
        AWS_STORAGE_BUCKET_NAME,
        AWS_S3_REGION_NAME,
        AWS_MEDIA_LOCATION,
    )
    # django-compressor / collectstatic 互換のためローカル作業ディレクトリは保持する
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_URL = '/media/'

# メール設定
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _get_bool_env('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'support@tableno.jp')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', CONTACT_EMAIL)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@tableno.jp')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Stripe billing / legal disclosure settings
STRIPE_SECRET_KEY = _require_stripe_secret_key()
STRIPE_WEBHOOK_SECRET = _require_env('STRIPE_WEBHOOK_SECRET')
STRIPE_PREMIUM_PRICE_ID = _require_env('STRIPE_PREMIUM_PRICE_ID')
STRIPE_PREMIUM_YEARLY_PRICE_ID = os.environ.get('STRIPE_PREMIUM_YEARLY_PRICE_ID', '').strip()
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '').strip()
STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID = os.environ.get(
    'STRIPE_CUSTOMER_PORTAL_CONFIGURATION_ID',
    '',
).strip()
STRIPE_REVOKE_ON_REFUND_OR_DISPUTE = _get_bool_env(
    'STRIPE_REVOKE_ON_REFUND_OR_DISPUTE',
    default=True,
)
PUBLIC_SITE_URL = _require_env('PUBLIC_SITE_URL').rstrip('/')
PREMIUM_PRICE_LABEL = _require_non_placeholder_env(
    'PREMIUM_PRICE_LABEL',
    placeholder_fragments=('Stripe Checkout', 'Checkout画面に表示'),
)
LEGAL_PAYMENT_METHOD = _require_env('LEGAL_PAYMENT_METHOD')
LEGAL_PAYMENT_TIMING = _require_env('LEGAL_PAYMENT_TIMING')
LEGAL_SERVICE_DELIVERY_TIMING = _require_env('LEGAL_SERVICE_DELIVERY_TIMING')
LEGAL_CANCELLATION_METHOD = _require_env('LEGAL_CANCELLATION_METHOD')
LEGAL_CANCELLATION_EFFECT = _require_env('LEGAL_CANCELLATION_EFFECT')
LEGAL_REFUND_POLICY = _require_env('LEGAL_REFUND_POLICY')
LEGAL_SELLER_NAME = _require_env('LEGAL_SELLER_NAME')
LEGAL_SELLER_ADDRESS = _require_non_placeholder_env(
    'LEGAL_SELLER_ADDRESS',
    placeholder_fragment='請求があった場合',
)
LEGAL_SELLER_PHONE = _require_non_placeholder_env(
    'LEGAL_SELLER_PHONE',
    placeholder_fragment='請求があった場合',
)

# ロギング設定
LOG_TO_STDOUT = _get_bool_env('LOG_TO_STDOUT', default=True)
ENABLE_FILE_LOGGING = _get_bool_env('ENABLE_FILE_LOGGING', default=False)
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'logs'))
if ENABLE_FILE_LOGGING:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

logging_handlers = {
    'mail_admins': {
        'level': 'ERROR',
        'filters': ['require_debug_false'],
        'class': 'django.utils.log.AdminEmailHandler',
        'formatter': 'verbose',
    },
}
if LOG_TO_STDOUT:
    logging_handlers['console'] = {
        'level': 'INFO',
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    }
if ENABLE_FILE_LOGGING:
    logging_handlers['file'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': os.path.join(LOG_DIR, 'tableno.log'),
        'maxBytes': 1024 * 1024 * 10,
        'backupCount': 10,
        'formatter': 'verbose',
    }
    logging_handlers['error_file'] = {
        'level': 'ERROR',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': os.path.join(LOG_DIR, 'errors.log'),
        'maxBytes': 1024 * 1024 * 10,
        'backupCount': 10,
        'formatter': 'verbose',
    }

django_handlers = []
tableno_handlers = []
request_handlers = ['mail_admins']
if LOG_TO_STDOUT:
    django_handlers.append('console')
    tableno_handlers.append('console')
if ENABLE_FILE_LOGGING:
    django_handlers.insert(0, 'file')
    tableno_handlers.insert(0, 'file')
    request_handlers.insert(0, 'error_file')

if not django_handlers:
    django_handlers = ['mail_admins']
if not tableno_handlers:
    tableno_handlers = ['mail_admins']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': logging_handlers,
    'loggers': {
        'django': {
            'handlers': django_handlers,
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': request_handlers,
            'level': 'ERROR',
            'propagate': False,
        },
        'tableno': {
            'handlers': tableno_handlers,
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Admin設定
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', SUPPORT_EMAIL)),
]
MANAGERS = ADMINS

# OAuth設定
_validate_env_pair('GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET')
_validate_env_pair('DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET')
if 'GOOGLE_OAUTH_CLIENT_ID' in os.environ:
    GOOGLE_OAUTH_CLIENT_ID = os.environ['GOOGLE_OAUTH_CLIENT_ID']
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ['GOOGLE_OAUTH_CLIENT_SECRET']

# CORS設定（必要に応じて）
CORS_ALLOWED_ORIGINS = _split_env_list(os.environ.get('CORS_ALLOWED_ORIGINS', ''))

# ファイルアップロード設定
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# タイムゾーン設定
TIME_ZONE = 'Asia/Tokyo'
USE_TZ = True

# パフォーマンス設定
CONN_MAX_AGE = 60

# Django REST Framework設定（本番環境用）
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
)

# Sentry設定（エラー監視）
if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        send_default_pii=False,
        environment=ENVIRONMENT,
    )

# WhiteNoise設定（S3非利用時のみ）
if not USE_S3_STORAGE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    WHITENOISE_AUTOREFRESH = False
    WHITENOISE_USE_FINDERS = False
    WHITENOISE_COMPRESS_OFFLINE = True

# Django Compressor設定（CSSとJSの圧縮）
if 'compressor' not in INSTALLED_APPS:
    INSTALLED_APPS.append('compressor')
if 'STATICFILES_FINDERS' not in globals():
    STATICFILES_FINDERS = [
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    ]
if 'compressor.finders.CompressorFinder' not in STATICFILES_FINDERS:
    STATICFILES_FINDERS.append('compressor.finders.CompressorFinder')

COMPRESS_ENABLED = True
if USE_S3_STORAGE:
    COMPRESS_ENABLED = False
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
