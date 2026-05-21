"""
Test settings for Ringoo project.
"""

from .base import *

# Тесты схемы/редиректов: документация доступна (как в dev)
API_DOCS_PUBLIC = True

# Use in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations during tests for speed
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Password hashing (faster for tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests
LOGGING_CONFIG = None

# Disable cache during tests (sessions cache required for SessionMiddleware when using APIClient)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# Email backend (in-memory for tests)
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable Celery during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Security settings (relaxed for tests)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS (allow all for tests)
CORS_ALLOW_ALL_ORIGINS = True

# Throttling: лимиты auth_* из base слишком строгие для массовых тестов
_REST_FW = dict(REST_FRAMEWORK)
_rates = dict(_REST_FW.get('DEFAULT_THROTTLE_RATES') or {})
_rates['auth_login'] = '10000/minute'
_rates['auth_register'] = '10000/minute'
_rates['legal_analytics'] = '10000/minute'
_REST_FW['DEFAULT_THROTTLE_RATES'] = _rates
REST_FRAMEWORK = _REST_FW

# django-axes: без миграций axes в быстрых тестах (MIGRATION_MODULES отключены)
AXES_ENABLED = False
ADMIN_OTP_ENABLED = False
