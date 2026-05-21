"""
Development settings for Ringoo project.
"""

import copy
from datetime import timedelta

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Локальная отладка: 5 попыток входа/мин (base) быстро даёт 429; axes — отдельный лимит.
if DEBUG:
    REST_FRAMEWORK = copy.deepcopy(REST_FRAMEWORK)
    _rates = REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    _rates['auth_login'] = os.getenv('AUTH_LOGIN_THROTTLE', '60/minute')
    _rates['auth_register'] = os.getenv('AUTH_REGISTER_THROTTLE', '30/hour')
    if os.getenv('AXES_FAILURE_LIMIT') is None:
        AXES_FAILURE_LIMIT = 40
    if os.getenv('AXES_COOLOFF_HOURS') is None:
        AXES_COOLOFF_TIME = timedelta(minutes=30)

# Локально документация API включена; в prod см. production.API_DOCS_PUBLIC
API_DOCS_PUBLIC = os.getenv('API_DOCS_PUBLIC', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Database
# USE_SQLITE=True — запуск без PostgreSQL (для быстрого старта локально).
# Иначе используется PostgreSQL (нужен запущенный сервер и корректные DB_* в .env).
def _db_env(key: str, default: str) -> str:
    val = os.getenv(key, default)
    return str(val).strip() or default


# По умолчанию SQLite в development (без PostgreSQL). Для Docker/PostgreSQL задайте USE_SQLITE=False
_use_sqlite = (
    os.getenv('USE_SQLITE', 'true').lower() in ('1', 'true', 'yes')
    or not _db_env('DB_HOST', '').strip()
)

if _use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db_env('DB_NAME', 'ringoo'),
            'USER': _db_env('DB_USER', 'postgres'),
            'PASSWORD': _db_env('DB_PASSWORD', 'postgres'),
            'HOST': _db_env('DB_HOST', 'localhost'),
            'PORT': _db_env('DB_PORT', '5432'),
            'OPTIONS': {
                'options': '-c client_encoding=UTF8',
                'connect_timeout': 10,
            },
        }
    }

# Email Backend (Console for development)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Кэш: в dev без Redis — LocMem, чтобы лимиты и сессии работали без docker redis.
# В production нельзя заменять общий Redis на LocMem при нескольких воркерах: ключи
# идемпотентности заказа (X-Idempotency-Key) хранятся в default cache — см. DEPLOYMENT.md.
_use_redis = os.getenv('USE_REDIS', 'true').lower() in ('1', 'true', 'yes')
_redis_url = (os.getenv('REDIS_URL') or '').strip()
if not _use_redis or not _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ringoo-default',
        },
        'sessions': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ringoo-sessions',
        },
    }

# Debug Toolbar (only in development)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }

# CORS: разрешить любой Origin только при DEBUG=True (этот модуль — только dev).
# В production используется config.settings.production: там CORS_ALLOW_ALL_ORIGINS = False.
# Не выставляйте DEBUG=True в проде: иначе при случайной загрузке development.py откроется CORS *.
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True

# CSRF: разрешить запросы с фронта на localhost (Origin checking)
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',') if o.strip()
]

# Security Settings (relaxed for development)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

# Logging Configuration
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
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['redact_pii'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'ringoo.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# OWASP 4.6.2: напоминание при dev-ключе (не блокирует запуск)
if DEBUG and SECRET_KEY and (
    'django-insecure' in SECRET_KEY or len(SECRET_KEY) < 48
):
    import warnings

    warnings.warn(
        'SECRET_KEY looks like a development default. Use a strong key in production (env).',
        stacklevel=1,
    )
