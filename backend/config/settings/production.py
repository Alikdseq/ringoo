"""
Production settings for Ringoo project.

Fail-closed: DEBUG запрещён; SECRET_KEY / ALLOWED_HOSTS / OTP / DB / Redis
обязательны. Не генерируем SECRET_KEY из публичных идентификаторов.
"""

import os
import urllib.parse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

ON_VERCEL = os.getenv('VERCEL') == '1'

# ---------------------------------------------------------------------------
# DEBUG — никогда не True в production module
# ---------------------------------------------------------------------------
_debug_raw = os.getenv('DEBUG', 'False').strip().lower()
if _debug_raw in ('1', 'true', 'yes'):
    raise ImproperlyConfigured(
        'DEBUG=True is forbidden when using config.settings.production. '
        'Use config.settings.development for local debugging.'
    )
DEBUG = False

# HttpOnly JWT-куки только по HTTPS
JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'True') == 'True'
JWT_COOKIE_ENABLED = os.getenv('JWT_COOKIE_ENABLED', 'True') == 'True'

# Swagger/ReDoc и /api/schema/ (в production по умолчанию закрыты)
API_DOCS_PUBLIC = os.getenv('API_DOCS_PUBLIC', 'False') == 'True'

# ---------------------------------------------------------------------------
# SECRET_KEY — обязателен, без деривации из project id
# ---------------------------------------------------------------------------
_sk = (SECRET_KEY or '').strip()
if (
    not _sk
    or len(_sk) < 48
    or 'django-insecure' in _sk
    or _sk == 'your-secret-key-here-change-in-production'
):
    raise ImproperlyConfigured(
        'SECRET_KEY must be set to a unique cryptographically strong value '
        '(≥48 characters). Do not use development defaults or derive from '
        'public project identifiers.'
    )
SECRET_KEY = _sk
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

# ---------------------------------------------------------------------------
# ALLOWED_HOSTS — обязателен
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()
]
if ON_VERCEL:
    for host in (
        '.vercel.app',
        os.getenv('VERCEL_URL', '').strip(),
        os.getenv('VERCEL_BRANCH_URL', '').strip(),
        os.getenv('VERCEL_PROJECT_PRODUCTION_URL', '').strip(),
    ):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS is empty. Set a comma-separated list of hostnames '
        '(e.g. shop.example.com,www.shop.example.com).'
    )

# ---------------------------------------------------------------------------
# MFA / OTP — обязателен для Django Admin в production
# ---------------------------------------------------------------------------
if not ADMIN_OTP_ENABLED:
    raise ImproperlyConfigured(
        'ADMIN_OTP_ENABLED must be true in production. Enroll TOTP devices '
        'for every staff/superuser before go-live. '
        'Set ADMIN_OTP_ENABLED=1 (default for production settings).'
    )
# Гарантируем приложения OTP (на случай если base загрузился иначе)
for _otp_app in ('django_otp', 'django_otp.plugins.otp_totp'):
    if _otp_app not in INSTALLED_APPS:
        INSTALLED_APPS.append(_otp_app)
if 'django_otp.middleware.OTPMiddleware' not in MIDDLEWARE:
    # После AuthenticationMiddleware
    try:
        _auth_idx = MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')
        MIDDLEWARE.insert(_auth_idx + 1, 'django_otp.middleware.OTPMiddleware')
    except ValueError:
        MIDDLEWARE.append('django_otp.middleware.OTPMiddleware')

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_WEAK_DB_USERS = frozenset({'postgres', 'root', 'admin', 'superuser'})
_WEAK_DB_PASSWORDS = frozenset({'', 'postgres', 'password', 'pass', 'root', 'admin', 'changeme'})


def _database_from_url(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    options: dict = {'connect_timeout': 10}
    if ON_VERCEL or os.getenv('DB_SSL', '').lower() in ('1', 'true', 'require'):
        options['sslmode'] = 'require'
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/'),
        'USER': urllib.parse.unquote(parsed.username or ''),
        'PASSWORD': urllib.parse.unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or 5432),
        'CONN_MAX_AGE': 0 if ON_VERCEL else int(os.getenv('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': options,
    }


def _assert_db_credentials(user: str, password: str) -> None:
    u = (user or '').strip().lower()
    p = password or ''
    if u in _WEAK_DB_USERS:
        raise ImproperlyConfigured(
            'Production must not connect to PostgreSQL as a superuser/default '
            f'role ({user!r}). Create a least-privilege application role '
            '(see docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md).'
        )
    if p.strip().lower() in _WEAK_DB_PASSWORDS or len(p) < 16:
        raise ImproperlyConfigured(
            'DB_PASSWORD must be a unique strong secret (≥16 characters) and '
            'must not use defaults like "postgres".'
        )


_database_url = os.getenv('DATABASE_URL', '').strip()
if _database_url:
    DATABASES = {'default': _database_from_url(_database_url)}
    if not ON_VERCEL:
        _assert_db_credentials(
            DATABASES['default'].get('USER', ''),
            DATABASES['default'].get('PASSWORD', ''),
        )
elif ON_VERCEL:
    import shutil
    from pathlib import Path

    _bundled_db = Path(BASE_DIR) / 'vercel_data' / 'catalog.db'
    if os.getenv('RINGOO_VERCEL_BUILD') == '1':
        _bundled_db.parent.mkdir(parents=True, exist_ok=True)
        _sqlite_name = _bundled_db
    else:
        _runtime_db = Path('/tmp/ringoo-catalog.db')
        if _bundled_db.exists() and not _runtime_db.exists():
            shutil.copy2(_bundled_db, _runtime_db)
        _sqlite_name = _runtime_db
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _sqlite_name,
        }
    }
else:
    _db_user = os.getenv('DB_USER', '').strip()
    _db_password = os.getenv('DB_PASSWORD', '')
    _assert_db_credentials(_db_user, _db_password)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'ringoo_prod'),
            'USER': _db_user,
            'PASSWORD': _db_password,
            'HOST': os.getenv('DB_HOST', 'db'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

if ON_VERCEL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ringoo',
        },
        'sessions': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ringoo-sessions',
        },
    }
else:
    # Redis password required for non-Vercel production when using redis URL
    _redis_url = (
        os.getenv('REDIS_URL')
        or os.getenv('CELERY_BROKER_URL')
        or ''
    ).strip()
    _redis_password = os.getenv('REDIS_PASSWORD', '').strip()
    if not _redis_password and '://:' not in _redis_url:
        raise ImproperlyConfigured(
            'REDIS_PASSWORD (or redis://:password@… in REDIS_URL) is required '
            'in production. Do not run Redis without authentication.'
        )
    if _redis_password and len(_redis_password) < 16:
        raise ImproperlyConfigured(
            'REDIS_PASSWORD must be at least 16 characters.'
        )

# CORS: только разрешённые домены; * запрещён
CORS_ALLOW_ALL_ORIGINS = False
if os.getenv("CORS_ALLOW_ALL_ORIGINS", "").lower() in ("1", "true", "yes"):
    raise ImproperlyConfigured(
        "CORS_ALLOW_ALL_ORIGINS must not be enabled in production."
    )
if not CORS_ALLOWED_ORIGINS and not ON_VERCEL:
    raise ImproperlyConfigured(
        'CORS_ALLOWED_ORIGINS must list your https frontend origin(s).'
    )

# CSRF
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]
if ON_VERCEL:
    for origin in (
        'https://*.vercel.app',
        f"https://{os.getenv('VERCEL_URL', '').strip()}" if os.getenv('VERCEL_URL') else '',
        f"https://{os.getenv('VERCEL_PROJECT_PRODUCTION_URL', '').strip()}"
        if os.getenv('VERCEL_PROJECT_PRODUCTION_URL')
        else '',
    ):
        if origin and origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
elif not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        'CSRF_TRUSTED_ORIGINS must include https://your-frontend-domain '
        'when running behind a browser client.'
    )

# Trust X-Forwarded-Proto only when explicitly enabled (reverse proxy).
# Do NOT enable unless the proxy strips client-supplied X-Forwarded-* .
_trust_proxy = os.getenv('TRUST_PROXY', '1' if ON_VERCEL else '0').strip().lower() in (
    '1',
    'true',
    'yes',
)
if _trust_proxy or ON_VERCEL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Axes: число прокси до Django (обычно 1 за nginx/caddy)
if os.getenv('AXES_IPWARE_PROXY_COUNT', '').strip() == '' and _trust_proxy:
    AXES_IPWARE_PROXY_COUNT = int(os.getenv('AXES_IPWARE_PROXY_COUNT', '1') or '1')

if ON_VERCEL:
    MEDIA_ROOT = BASE_DIR / 'catalog_media'
    SERVE_MEDIA = True
    _public_host = (
        os.getenv('VERCEL_PROJECT_PRODUCTION_URL', '').strip()
        or os.getenv('VERCEL_URL', '').strip()
    )
    if _public_host:
        PUBLIC_API_ORIGIN = f'https://{_public_host}'.rstrip('/')

# Integrations remain opt-in (defaults false in base). Documented for ops.
# Sber callback token required when enabled:
if SBER_ECOM_ENABLED and not str(SBER_ECOM_CALLBACK_TOKEN or '').strip():
    raise ImproperlyConfigured(
        'SBER_ECOM_CALLBACK_TOKEN is required when SBER_ECOM_ENABLED=true in production. '
        'Set a long random secret and put the same value in SBER_ECOM_CALLBACK_URL (?token=...).'
    )
if SBER_ECOM_CALLBACK_TOKEN_REQUIRED is None:
    SBER_ECOM_CALLBACK_TOKEN_REQUIRED = True

# ЮKassa: при включении в production обязательны shopId и secret; test-режим по умолчанию.
if YOOKASSA_ENABLED:
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise ImproperlyConfigured(
            'YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY are required when YOOKASSA_ENABLED=true.'
        )
    if YOOKASSA_TEST_MODE and not YOOKASSA_SECRET_KEY.startswith('test_'):
        raise ImproperlyConfigured(
            'YOOKASSA_TEST_MODE=1 requires a test secret key (prefix test_).'
        )
    if not YOOKASSA_TEST_MODE and YOOKASSA_SECRET_KEY.startswith('test_'):
        raise ImproperlyConfigured(
            'Live YooKassa mode cannot use a test_ secret key. Set YOOKASSA_TEST_MODE=1 or use live keys.'
        )
    if SBER_ECOM_ENABLED:
        # Не падаем: роутер выбирает ЮKassa; предупреждение для ops.
        import logging as _logging

        _logging.getLogger(__name__).warning(
            'Both YOOKASSA_ENABLED and SBER_ECOM_ENABLED are true; runtime uses YooKassa only.'
        )

# Security Settings
SECURE_SSL_REDIRECT = os.getenv(
    'SECURE_SSL_REDIRECT',
    'False' if ON_VERCEL else 'True',
) == 'True'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'False') == 'True'
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'True') == 'True'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False') == 'True'
X_FRAME_OPTIONS = 'DENY'

# Email Backend
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@ringoo.ru')

USE_S3 = os.getenv('USE_S3', 'False') == 'True'

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
    }
else:
    INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS
    MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

# Каталог логов должен существовать до конфигурации FileHandler (иначе старт падает).
_LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/app/logs/django.log')
if not ON_VERCEL:
    try:
        os.makedirs(os.path.dirname(_LOG_FILE_PATH) or '.', exist_ok=True)
    except OSError:
        pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_pii': {
            '()': 'config.logging_filters.RedactPIIFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['redact_pii'],
        },
        **({} if ON_VERCEL else {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': _LOG_FILE_PATH,
                'maxBytes': 1024 * 1024 * 10,
                'backupCount': 5,
                'formatter': 'json',
                'filters': ['redact_pii'],
            },
        }),
    },
    'root': {
        'handlers': ['console'] if ON_VERCEL else ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if ON_VERCEL else ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'] if ON_VERCEL else ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'ringoo.security': {
            'handlers': ['console'] if ON_VERCEL else ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
