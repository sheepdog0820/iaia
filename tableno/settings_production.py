"""
本番環境用設定ファイル
"""
from .settings import *
import os
from pathlib import Path

# 環境変数のリスト分割ヘルパー
def _split_env_list(value):
    return [item.strip() for item in value.split(',') if item.strip()]

# セキュリティ設定
DEBUG = False
ALLOWED_HOSTS = _split_env_list(os.environ.get('ALLOWED_HOSTS', ''))
if not ALLOWED_HOSTS:
    raise RuntimeError('ALLOWED_HOSTS is required for production/staging')

# セキュリティヘッダー
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# データベース設定（MySQL / PostgreSQL）
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()
if DB_ENGINE in ('mysql', 'mariadb'):
    db_engine = 'django.db.backends.mysql'
    db_port = '3306'
    db_options = {'charset': 'utf8mb4'}
elif DB_ENGINE in ('postgres', 'postgresql'):
    db_engine = 'django.db.backends.postgresql'
    db_port = '5432'
    db_options = {}
else:
    raise ValueError(f'Unsupported DB_ENGINE: {DB_ENGINE}')

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': os.environ.get('DB_NAME', 'tableno'),
        'USER': os.environ.get('DB_USER', 'tableno_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', db_port),
        'CONN_MAX_AGE': 60,  # 接続プーリング
        'OPTIONS': db_options,
    }
}

# キャッシュ設定（Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        },
        'KEY_PREFIX': 'tableno',
        'TIMEOUT': 300,  # 5分
    }
}

# セッション設定
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# 静的ファイル設定
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# メディアファイル設定
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# メール設定
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@yourdomain.com')

# ロギング設定
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'logs'))
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
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'tableno.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'tableno': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Admin設定
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@yourdomain.com')),
]
MANAGERS = ADMINS

# OAuth設定（本番環境用）
if 'GOOGLE_OAUTH_CLIENT_ID' in os.environ:
    GOOGLE_OAUTH_CLIENT_ID = os.environ['GOOGLE_OAUTH_CLIENT_ID']
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ['GOOGLE_OAUTH_CLIENT_SECRET']

# CORS設定（必要に応じて）
CORS_ALLOWED_ORIGINS = _split_env_list(os.environ.get('CORS_ALLOWED_ORIGINS', ''))

# CSRFトークン設定
CSRF_TRUSTED_ORIGINS = _split_env_list(os.environ.get('CSRF_TRUSTED_ORIGINS', ''))
if not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError('CSRF_TRUSTED_ORIGINS is required for production/staging')

# ファイルアップロード設定
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

# タイムゾーン設定
TIME_ZONE = 'Asia/Tokyo'
USE_TZ = True

# パフォーマンス設定
CONN_MAX_AGE = 60  # データベース接続の再利用

# Django REST Framework設定（本番環境用）
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',  # HTMLレンダラーを無効化
)

# Sentry設定（エラー監視）
if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

# WhiteNoise設定
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# 圧縮設定
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_COMPRESS_OFFLINE = True

# Django Compressor設定（CSSとJSの圧縮）
INSTALLED_APPS.append('compressor')
if 'STATICFILES_FINDERS' not in globals():
    STATICFILES_FINDERS = [
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    ]
if 'compressor.finders.CompressorFinder' not in STATICFILES_FINDERS:
    STATICFILES_FINDERS.append('compressor.finders.CompressorFinder')

COMPRESS_ENABLED = True
COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter',
                         'compressor.filters.cssmin.CSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
