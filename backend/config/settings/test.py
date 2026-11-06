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
# Callback без секрета в unit-тестах; prod fail-closed проверяется отдельно override_settings.
SBER_ECOM_CALLBACK_TOKEN_REQUIRED = False
SBER_ECOM_CALLBACK_TOKEN = ''
SBER_ECOM_ENABLED = False
# ЮKassa выкл. по умолчанию в тестах (не подхватывать YOOKASSA_* из shell/.env).
# Тесты ЮKassa включают через @override_settings.
YOOKASSA_ENABLED = False
YOOKASSA_TEST_MODE = True
YOOKASSA_SHOP_ID = ''
YOOKASSA_SECRET_KEY = ''


# CORS (allow all for tests)
CORS_ALLOW_ALL_ORIGINS = True

# Throttling: лимиты auth_* из base слишком строгие для массовых тестов
_REST_FW = dict(REST_FRAMEWORK)
_rates = dict(_REST_FW.get('DEFAULT_THROTTLE_RATES') or {})
_rates['auth_login'] = '10000/minute'
_rates['auth_register'] = '10000/minute'
_rates['legal_analytics'] = '10000/minute'
_rates['payment_pay_anon'] = '10000/minute'
_rates['payment_pay_user'] = '10000/minute'
_rates['payment_callback'] = '10000/minute'
_rates['payment_status_anon'] = '10000/minute'
_rates['payment_status_user'] = '10000/minute'
_rates['order_track'] = '10000/minute'
_rates['order_rate'] = '10000/minute'
_rates['order_create'] = '10000/minute'
_rates['order_create_anon'] = '10000/minute'
_rates['review_create'] = '10000/minute'
_rates['review_create_anon'] = '10000/minute'
_rates['yookassa_webhook'] = '10000/minute'
_rates['password_reset'] = '10000/minute'
_rates['password_reset_confirm'] = '10000/minute'
_rates['guest_access_recover'] = '10000/minute'
_rates['guest_access_recover_confirm'] = '10000/minute'
_REST_FW['DEFAULT_THROTTLE_RATES'] = _rates
REST_FRAMEWORK = _REST_FW

# FUNC-007: по умолчанию выкл.; тесты бонусного начисления включают явно.
BONUS_ENABLED = False

# django-axes: без миграций axes в быстрых тестах (MIGRATION_MODULES отключены)
AXES_ENABLED = False
ADMIN_OTP_ENABLED = False
# OTP apps available for MFA unit-tests (flag still False by default).
_INSTALLED = list(INSTALLED_APPS)
for _otp_app in ('django_otp', 'django_otp.plugins.otp_totp'):
    if _otp_app not in _INSTALLED:
        _INSTALLED.append(_otp_app)
INSTALLED_APPS = _INSTALLED
_rates['auth_mfa_verify'] = '10000/minute'
_REST_FW['DEFAULT_THROTTLE_RATES'] = _rates
REST_FRAMEWORK = _REST_FW
