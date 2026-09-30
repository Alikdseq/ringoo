"""
Production settings for Ringoo project.
"""

import urllib.parse

from django.core.exceptions import ImproperlyConfigured

from .base import *

ON_VERCEL = os.getenv('VERCEL') == '1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# HttpOnly JWT-куки только по HTTPS (если не переопределено)
JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'True') == 'True'

# Swagger/ReDoc и /api/schema/ (в production по умолчанию закрыты)
API_DOCS_PUBLIC = os.getenv('API_DOCS_PUBLIC', 'False') == 'True'

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
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS is empty or contains only blanks. '
        'Set a comma-separated list of hostnames (e.g. example.com,www.example.com).'
    )

if ON_VERCEL:
    _sk = SECRET_KEY or ''
    if len(_sk) < 48 or 'django-insecure' in _sk:
        import hashlib

        seed = (os.getenv('VERCEL_PROJECT_ID') or 'ringoo').strip()
        SECRET_KEY = (
            hashlib.sha256(f'ringoo-vercel:{seed}'.encode()).hexdigest()
            + hashlib.sha256(f'ringoo-jwt:{seed}'.encode()).hexdigest()
        )
        SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

if not DEBUG and not ON_VERCEL:
    _sk = SECRET_KEY or ''
    if len(_sk) < 48 or 'django-insecure' in _sk:
        raise ImproperlyConfigured(
            'SECRET_KEY must be at least 48 characters and must not use a default '
            '"django-insecure" development value. Set a strong key in the environment.'
        )

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


_database_url = os.getenv('DATABASE_URL', '').strip()
if _database_url:
    DATABASES = {'default': _database_from_url(_database_url)}
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
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'ringoo_prod'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'db'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 0 if ON_VERCEL else int(os.getenv('DB_CONN_MAX_AGE', '60')),
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

# CORS: только разрешённые домены (2.6.3), в prod не разрешать все
CORS_ALLOW_ALL_ORIGINS = False
if not DEBUG and os.getenv("CORS_ALLOW_ALL_ORIGINS", "").lower() in ("1", "true", "yes"):
    raise ImproperlyConfigured(
        "CORS_ALLOW_ALL_ORIGINS must not be enabled in production."
    )

# CSRF: для запросов с фронта с другого домена (если нужна сессия/куки)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
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
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if ON_VERCEL:
    MEDIA_ROOT = BASE_DIR / 'catalog_media'
    SERVE_MEDIA = True
    _public_host = (
        os.getenv('VERCEL_PROJECT_PRODUCTION_URL', '').strip()
        or os.getenv('VERCEL_URL', '').strip()
    )
    if _public_host:
        PUBLIC_API_ORIGIN = f'https://{_public_host}'.rstrip('/')

# Security Settings
# На Vercel TLS обрывается на платформе. Редирект внутри функции даёт лишний цикл.
SECURE_SSL_REDIRECT = os.getenv(
    'SECURE_SSL_REDIRECT',
    'False' if ON_VERCEL else 'True',
) == 'True'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
# По умолчанию выкл.: заголовок X-XSS-Protection устарел; при необходимости legacy-клиентов — True в env.
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'False') == 'True'
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'True') == 'True'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

# Email Backend
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@ringoo.ru')

# Static files (using WhiteNoise or S3)
USE_S3 = os.getenv('USE_S3', 'False') == 'True'

if USE_S3:
    # AWS S3 Settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Static files. Django 5.1+ читает STORAGES, не STATICFILES_STORAGE.
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
    }
else:
    # Use WhiteNoise for static files
    INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS
    MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

# Logging Configuration
# Каталог для LOG_FILE_PATH должен существовать (создайте в entrypoint или задайте путь в существующую директорию).
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
                'filename': os.getenv('LOG_FILE_PATH', '/app/logs/django.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
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
