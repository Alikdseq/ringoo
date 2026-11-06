"""
Base settings for Ringoo project.

Django settings for Ringoo project.
"""

import os
import re
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# На Windows libpq строит пути через %APPDATA%\postgresql — кириллица в пути даёт UnicodeDecodeError.
# Перенаправляем пути в каталог проекта и подменяем APPDATA (только ASCII).
if sys.platform == "win32":
    os.environ.setdefault("PGCLIENTENCODING", "UTF8")
    pgconfig = BASE_DIR / "pgconfig"
    tmpdir = BASE_DIR / "tmp"
    pgconfig.mkdir(parents=True, exist_ok=True)
    tmpdir.mkdir(parents=True, exist_ok=True)
    pgpass_path = (BASE_DIR / ".pgpass").as_posix()
    pgconfig_path = pgconfig.as_posix()
    tmp_path = tmpdir.as_posix()
    if "PGPASSFILE" not in os.environ:
        os.environ["PGPASSFILE"] = pgpass_path
    if "PGSYSCONFDIR" not in os.environ:
        os.environ["PGSYSCONFDIR"] = pgconfig_path
    if "PGSERVICEFILE" not in os.environ:
        os.environ["PGSERVICEFILE"] = (pgconfig / "pg_service.conf").as_posix()
    os.environ["TEMP"] = tmp_path
    os.environ["TMP"] = tmp_path
    os.environ["APPDATA"] = pgconfig_path

# Load environment variables (UTF-8 to avoid UnicodeDecodeError on Windows).
# Production НЕ загружает .env.development — только явный process env / .env.production.
_settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
_is_production_settings = (
    _settings_module.endswith(".production") or _settings_module.endswith("production")
)
if not _is_production_settings:
    # Dev/test: сначала backend/.env.development, затем корень репозитория
    for env_path in (BASE_DIR / ".env.development", BASE_DIR.parent / ".env.development"):
        if env_path.exists():
            load_dotenv(env_path, encoding="utf-8")
            break
    else:
        for env_path in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
            if env_path.exists():
                load_dotenv(env_path, encoding="utf-8")
                break
else:
    # Production: опционально только .env.production (не development), если файл есть
    # (обычно секреты задаёт оркестратор / Docker env_file явно).
    for env_path in (BASE_DIR / ".env.production", BASE_DIR.parent / ".env.production"):
        if env_path.exists():
            load_dotenv(env_path, encoding="utf-8", override=False)
            break

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# Путь админки: задайте DJANGO_ADMIN_URL=секретный-префикс (буквы, цифры, -, _)
_admin_candidate = (os.getenv('DJANGO_ADMIN_URL', 'admin') or 'admin').strip().strip('/')
if not _admin_candidate or not re.fullmatch(
    r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}', _admin_candidate
):
    _admin_candidate = 'admin'
ADMIN_SITE_URL_PATH = f'{_admin_candidate}/'

# TOTP для Django admin. В production settings — по умолчанию включено (см. production.py).
_otp_raw = os.getenv('ADMIN_OTP_ENABLED', '').strip().lower()
if _is_production_settings:
    # Fail-closed: OTP on unless explicitly disabled (production.py then raises).
    ADMIN_OTP_ENABLED = _otp_raw not in ('0', 'false', 'no')
else:
    ADMIN_OTP_ENABLED = _otp_raw in ('1', 'true', 'yes')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'axes',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    
    # Local apps
    'apps.users',
    'apps.products',
    'apps.orders',
    'apps.payments',
    'apps.stores',
    'apps.content',
    'apps.cart',
    'apps.bonus',
    'apps.promotions',
    'apps.crm',
    'apps.wishlist',
    'apps.admin_api',
    'apps.audit',
    'apps.backups',
    'apps.returns',
]

if ADMIN_OTP_ENABLED:
    INSTALLED_APPS.extend(
        [
            'django_otp',
            'django_otp.plugins.otp_totp',
        ]
    )

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF для сессий; JWT-эндпоинты не требуют токена
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]
if ADMIN_OTP_ENABLED:
    MIDDLEWARE.append('django_otp.middleware.OTPMiddleware')
MIDDLEWARE += [
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.csrf_api.JwtCookieCsrfMiddleware',
    'config.middleware.SecurityHeadersMiddleware',  # Custom security headers
    'axes.middleware.AxesMiddleware',
]

# Политика конфиденциальности (версия для ConsentRecord)
POLICY_VERSION = (os.getenv('POLICY_VERSION', '2026-11-03') or '2026-11-03').strip()

# Лимиты загрузки (защита от oversized body)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(5 * 1024 * 1024)))

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# Вход по телефону и паролю: SimpleJWT передаёт phone=..., ModelBackend ждёт username=...
# Наш бэкенд ищет пользователя по полю phone.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'apps.users.backends.PhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# django-axes: блокировка после серии неудачных входов (API + сессионная админка)
AXES_FAILURE_LIMIT = int(os.getenv('AXES_FAILURE_LIMIT', '8'))
AXES_COOLOFF_TIME = timedelta(hours=int(os.getenv('AXES_COOLOFF_HOURS', '1')))
AXES_USERNAME_CALLABLE = 'apps.users.axes_integration.axes_get_username'
AXES_LOCKOUT_CALLABLE = 'apps.users.axes_integration.axes_lockout_response'
AXES_RESET_ON_SUCCESS = True
# username + IP: не блокировать весь NAT по одному «логину» с разных телефонов
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# Иначе middleware не подменит ответ при lockout (DRF + JSON)
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
# За N прокси до Django: задайте AXES_IPWARE_PROXY_COUNT в env (см. django-axes / django-ipware)
_axes_proxy = os.getenv("AXES_IPWARE_PROXY_COUNT", "").strip()
if _axes_proxy.isdigit():
    AXES_IPWARE_PROXY_COUNT = int(_axes_proxy)

# Password hashing: Argon2 (устойчив к перебору), fallback — PBKDF2
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'ru-ru')
TIME_ZONE = os.getenv('TIME_ZONE', 'Europe/Moscow')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv('STATIC_URL', '/static/')
STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR / 'staticfiles')

MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
MEDIA_ROOT = os.getenv('MEDIA_ROOT', BASE_DIR / 'media')

# Admin downloadable backups (DB + media). Never put secrets in archives.
BACKUP_STORAGE_ROOT = Path(
    os.getenv('BACKUP_STORAGE_ROOT', str(BASE_DIR / 'var' / 'backups'))
)
BACKUP_DOWNLOAD_TTL_HOURS = int(os.getenv('BACKUP_DOWNLOAD_TTL_HOURS', '24') or '24')
BACKUP_CREATE_LOCK_TTL_SECONDS = int(
    os.getenv('BACKUP_CREATE_LOCK_TTL_SECONDS', '900') or '900'
)
BACKUP_STALE_ALERT_HOURS = int(os.getenv('BACKUP_STALE_ALERT_HOURS', '48') or '48')

# Offsite S3-compatible storage (Yandex / Selectel / AWS / MinIO). Secrets only via env.
BACKUP_OFFSITE_ENABLED = os.getenv('BACKUP_OFFSITE_ENABLED', '').strip().lower() in (
    '1',
    'true',
    'yes',
)
BACKUP_S3_ENDPOINT_URL = os.getenv('BACKUP_S3_ENDPOINT_URL', '').strip()
BACKUP_S3_REGION = os.getenv('BACKUP_S3_REGION', 'ru-central1').strip()
BACKUP_S3_BUCKET = os.getenv('BACKUP_S3_BUCKET', '').strip()
BACKUP_S3_ACCESS_KEY = os.getenv('BACKUP_S3_ACCESS_KEY', '').strip()
BACKUP_S3_SECRET_KEY = os.getenv('BACKUP_S3_SECRET_KEY', '').strip()
BACKUP_S3_PREFIX = os.getenv('BACKUP_S3_PREFIX', 'ringoo/backups').strip()
BACKUP_S3_PROVIDER_LABEL = os.getenv('BACKUP_S3_PROVIDER_LABEL', 's3-compatible').strip()
# AES-256 key material (base64 or hex of 32 bytes). NEVER commit real values.
BACKUP_ENCRYPTION_KEY_ID = os.getenv('BACKUP_ENCRYPTION_KEY_ID', '').strip()
BACKUP_ENCRYPTION_KEY = os.getenv('BACKUP_ENCRYPTION_KEY', '').strip()
BACKUP_ENCRYPTION_KEYS_PREVIOUS = os.getenv('BACKUP_ENCRYPTION_KEYS_PREVIOUS', '').strip()
BACKUP_RETENTION_DAILY_DAYS = int(os.getenv('BACKUP_RETENTION_DAILY_DAYS', '14') or '14')
BACKUP_RETENTION_WEEKLY_WEEKS = int(os.getenv('BACKUP_RETENTION_WEEKLY_WEEKS', '8') or '8')
BACKUP_RETENTION_MONTHLY_MONTHS = int(
    os.getenv('BACKUP_RETENTION_MONTHLY_MONTHS', '12') or '12'
)
BACKUP_SCHEDULED_ENABLED = os.getenv('BACKUP_SCHEDULED_ENABLED', '').strip().lower() in (
    '1',
    'true',
    'yes',
)

# Абсолютные URL в API для браузера (не docker-host web:8000)
PUBLIC_API_ORIGIN = os.getenv('PUBLIC_API_ORIGIN', 'http://localhost:8000').rstrip('/')

# Корень `frontend/public` для команды import_public_catalog (Samsung / Iphone).
RINGOO_PUBLIC_CATALOG_ROOT = Path(
    os.getenv('RINGOO_PUBLIC_CATALOG_ROOT', str(BASE_DIR.parent / 'frontend' / 'public'))
)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.users.authentication.LenientJWTAuthentication',
        'apps.users.authentication.JWTCookieAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Throttling (задача 2.6.2): общие лимиты + разные для read-only
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'anon_read': '300/hour',   # read-only: каталог, категории, магазины
        'user_read': '2000/hour',
        'order_create': '20/hour',       # создание заказа (авторизованный)
        'order_create_anon': '10/hour',  # создание заказа (гость по IP)
        'order_track': '5/minute',       # отслеживание заказа по номеру+телефону (гость)
        'order_rate': '30/hour',         # оценка заказа (гость)
        'auth_login': '5/minute',        # вход по паролю (anon, по IP)
        'auth_register': '5/hour',       # регистрация (anon, по IP)
        'auth_refresh': '30/minute',     # обновление access (anon, по IP)
        'auth_mfa_verify': '5/minute',   # TOTP verify (подбор кода)
        'crm_create': '10/hour',         # заявка «нет в наличии» (anon)
        'legal_analytics': '30/hour',    # согласие на cookie аналитики (anon)
        'cart_read': '600/hour',         # GET корзины
        'cart_write': '600/hour',        # PATCH/DELETE корзины (user)
        'cart_write_anon': '300/hour',   # POST в корзину (guest)
        'payment_pay_anon': '20/hour',   # инициация оплаты (гость)
        'payment_pay_user': '60/hour',   # инициация оплаты (user)
        'payment_callback': '120/minute',  # callback Сбера (по IP шлюза)
        'payment_status_anon': '30/minute',  # polling статуса (гость)
        'payment_status_user': '60/minute',  # polling статуса (user)
        'review_create_anon': '10/hour',     # SEC-004: создание отзыва (гость)
        'review_create': '20/hour',          # SEC-004: создание отзыва (user)
        'yookassa_webhook': '60/minute',     # SEC-007: webhook ЮKassa (по IP)
        'password_reset': '5/hour',          # SEC-009: запрос reset по IP
        'password_reset_confirm': '10/hour', # SEC-009: confirm по IP
        'guest_access_recover': '5/hour',    # SEC-006: recover guest order по IP
        'guest_access_recover_confirm': '10/hour',
    },
}

# SEC-007: лимит размера JSON webhook и debounce re-fetch одного платежа
YOOKASSA_WEBHOOK_MAX_BODY_BYTES = int(
    os.getenv('YOOKASSA_WEBHOOK_MAX_BODY_BYTES', '65536') or '65536'
)
YOOKASSA_WEBHOOK_SYNC_DEBOUNCE_SECONDS = int(
    os.getenv('YOOKASSA_WEBHOOK_SYNC_DEBOUNCE_SECONDS', '2') or '2'
)

# SEC-006: срок жизни guest access token (дни)
ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS = int(
    os.getenv('ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS', '90') or '90'
)

# HttpOnly-куки с JWT (дублируют JSON; фронт может перейти на NEXT_PUBLIC_USE_AUTH_COOKIES)
JWT_COOKIE_ENABLED = os.getenv('JWT_COOKIE_ENABLED', 'True') == 'True'
JWT_COOKIE_ACCESS_NAME = os.getenv('JWT_COOKIE_ACCESS_NAME', 'ringoo_access')
JWT_COOKIE_REFRESH_NAME = os.getenv('JWT_COOKIE_REFRESH_NAME', 'ringoo_refresh')
JWT_COOKIE_PATH = os.getenv('JWT_COOKIE_PATH', '/')
JWT_COOKIE_SAMESITE = os.getenv('JWT_COOKIE_SAMESITE', 'Lax')
# False в base: для локального HTTP; в production.py включается Secure по умолчанию
JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
if os.getenv('JWT_COOKIE_SECURE') is None:
    JWT_COOKIE_SECURE = False

# JWT Settings
_jwt_access_minutes = int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '30'))
_jwt_issuer = (os.getenv('JWT_ISSUER', 'ringoo') or 'ringoo').strip()
_jwt_audience = (os.getenv('JWT_AUDIENCE', 'ringoo-clients') or 'ringoo-clients').strip()

# iss/aud попадают в payload и проверяются при decode (SimpleJWT TokenBackend + PyJWT)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=_jwt_access_minutes),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'ISSUER': _jwt_issuer,
    'AUDIENCE': _jwt_audience,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Settings (задача 2.6.3: только нужные домены)
_cors_origins_raw = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_raw.split(',') if origin.strip()]

CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True') == 'True'
CORS_PREFLIGHT_MAX_AGE = 86400
# Кастомные заголовки SPA (preflight): идемпотентность заказов, HttpOnly JWT, CSRF в cookie-режиме.
CORS_ALLOW_HEADERS = [
    *default_headers,
    'x-idempotency-key',
    'x-auth-cookies',
    'x-csrftoken',
]

# API Documentation (drf-spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Ringoo API',
    'DESCRIPTION': 'API для интернет-магазина Ringoo',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Периодическая отмена неоплаченных online (нужен celery beat). Иначе — cron manage.py.
CELERY_BEAT_SCHEDULE = {
    'expire-unpaid-online-orders': {
        'task': 'apps.payments.tasks.expire_unpaid_online_orders_task',
        'schedule': 60.0 * 5,  # каждые 5 минут
    },
    'reconcile-open-payments': {
        'task': 'apps.payments.tasks.reconcile_open_payments_task',
        'schedule': 60.0 * 3,  # каждые 3 минуты — пропущенный callback
    },
}
if BACKUP_SCHEDULED_ENABLED:
    CELERY_BEAT_SCHEDULE['scheduled-offsite-backup'] = {
        'task': 'apps.backups.tasks.create_and_upload_offsite_backup_task',
        'schedule': 60.0 * 60 * 24,  # раз в сутки
    }
    CELERY_BEAT_SCHEDULE['backup-retention'] = {
        'task': 'apps.backups.tasks.apply_backup_retention_task',
        'schedule': 60.0 * 60 * 24,
    }

# Email (integrations 2.4.2): используется в dev (console) и prod (SMTP)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@ringoo.local')
# Куда слать уведомление при оценке менеджера (ТЗ EPIC 2)
MANAGER_RATING_NOTIFY_EMAIL = os.getenv('MANAGER_RATING_NOTIFY_EMAIL', '')
# Email менеджера для уведомлений о заявках «Не нашли товар» (раздел E.3)
MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', '')
# Базовый URL фронтенда (для ссылок в письмах, напр. форма оценки заказа)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')

# FUNC-007: бонусный модуль выключен по умолчанию (signals/checkout spend).
_bonus_raw = os.getenv('BONUS_ENABLED', '').strip().lower()
BONUS_ENABLED = _bonus_raw in ('1', 'true', 'yes')

# Yandex Maps (integrations 2.4.3)
YANDEX_GEOCODER_API_KEY = os.getenv('YANDEX_GEOCODER_API_KEY', '')

# Таймаут для внешних API (геокодер и т.д.) — чтобы не вешать сайт при их недоступности
EXTERNAL_API_TIMEOUT = int(os.getenv('EXTERNAL_API_TIMEOUT', '10'))

# 1С:УТ 11 HTTP-сервисы (integrations/onec). По умолчанию выключены.
# Единая публикация: /razrab/hs/ (не смешивать с /ut11_test/ и UUID других баз).
# Методы: CatalogFolders/folders, CatalogProducts/products,
# SiteRegistration/registrate, SiteOrders/orders, SiteOrders/orders/cancel.
# localhost в ONE_C_API_BASE_URL — только если сервис доступен из окружения сайта.
# Секреты: предпочтительно ONE_C_LOGIN / ONE_C_PASSWORD (инструкция 1С);
# ONE_C_API_USER / ONE_C_API_PASSWORD — совместимость с этапом 1.
# Хост сервера не выдумывать: подтвердить у администратора 1С перед реальными POST.
ONE_C_API_BASE_URL = os.getenv(
    'ONE_C_API_BASE_URL', 'http://localhost/razrab/hs'
).rstrip('/')
ONE_C_LOGIN = os.getenv('ONE_C_LOGIN', '') or os.getenv('ONE_C_API_USER', '')
ONE_C_PASSWORD = os.getenv('ONE_C_PASSWORD', '') or os.getenv('ONE_C_API_PASSWORD', '')
ONE_C_API_USER = ONE_C_LOGIN  # alias
ONE_C_API_PASSWORD = ONE_C_PASSWORD  # alias
ONE_C_API_TIMEOUT = int(os.getenv('ONE_C_API_TIMEOUT', '60'))
ONE_C_API_ENABLED = os.getenv('ONE_C_API_ENABLED', '').strip().lower() in (
    '1',
    'true',
    'yes',
    'on',
)
# Не вызывать регистрацию партнёра из signup без явного флага (сервисный слой готов).
ONE_C_SYNC_PARTNER_ON_REGISTER = os.getenv(
    'ONE_C_SYNC_PARTNER_ON_REGISTER', ''
).strip().lower() in ('1', 'true', 'yes', 'on')
# Асинхронная отправка заказов в 1С (Celery). Без флага задачи no-op.
ONE_C_ORDER_SYNC_ENABLED = os.getenv(
    'ONE_C_ORDER_SYNC_ENABLED', ''
).strip().lower() in ('1', 'true', 'yes', 'on')
# Устарело как обязательный склад доставки: warehouseId берётся из
# Store.onec_warehouse_id выбранного магазина заказа. Переменная сохранена
# только для совместимости env и не используется в sync.
ONE_C_DEFAULT_WAREHOUSE_ID = os.getenv('ONE_C_DEFAULT_WAREHOUSE_ID', '').strip()
# Ограниченные повторы при сети/500 (не для 400/409/422).
ONE_C_ORDER_SYNC_MAX_ATTEMPTS = int(os.getenv('ONE_C_ORDER_SYNC_MAX_ATTEMPTS', '5'))

# --- Сбербанк ecom (интернет-эквайринг). По умолчанию тест, выключен. ---
# Бой: https://epay.sberbank.ru — только после явного подтверждения, не переключать автоматически.
SBER_ECOM_BASE_URL = os.getenv(
    'SBER_ECOM_BASE_URL', 'https://ecomtest.sberbank.ru'
).rstrip('/')
SBER_ECOM_USERNAME = os.getenv('SBER_ECOM_USERNAME', '')
SBER_ECOM_PASSWORD = os.getenv('SBER_ECOM_PASSWORD', '')
SBER_ECOM_TIMEOUT = int(os.getenv('SBER_ECOM_TIMEOUT', '30'))
SBER_ECOM_ENABLED = os.getenv('SBER_ECOM_ENABLED', '').strip().lower() in (
    '1',
    'true',
    'yes',
    'on',
)
# Явный флаг для https://epay.sberbank.ru — без него клиент откажется от боевого URL
SBER_ECOM_ALLOW_PRODUCTION = os.getenv(
    'SBER_ECOM_ALLOW_PRODUCTION', ''
).strip().lower() in ('1', 'true', 'yes', 'on')
# Шаблоны URL возврата; плейсхолдеры {order_id}, {order_number}. Пусто → FRONTEND_URL/...
SBER_ECOM_RETURN_URL = os.getenv('SBER_ECOM_RETURN_URL', '')
SBER_ECOM_FAIL_URL = os.getenv('SBER_ECOM_FAIL_URL', '')
# Публичный HTTPS callback для ЛК Сбера / dynamicCallbackUrl (опционально)
SBER_ECOM_CALLBACK_URL = os.getenv('SBER_ECOM_CALLBACK_URL', '')
# Shared secret для callback (?token= / X-Sber-Callback-Token).
# Не заменяет getOrderStatusExtended. Значение — только env, не логировать.
SBER_ECOM_CALLBACK_TOKEN = os.getenv('SBER_ECOM_CALLBACK_TOKEN', '')
# Требовать токен: True/False явно; пусто → True при DEBUG=False (fail-closed вне разработки).
_sber_cb_req = os.getenv('SBER_ECOM_CALLBACK_TOKEN_REQUIRED', '').strip().lower()
if _sber_cb_req in ('1', 'true', 'yes', 'on'):
    SBER_ECOM_CALLBACK_TOKEN_REQUIRED = True
elif _sber_cb_req in ('0', 'false', 'no', 'off'):
    SBER_ECOM_CALLBACK_TOKEN_REQUIRED = False
else:
    SBER_ECOM_CALLBACK_TOKEN_REQUIRED = None  # derive: not DEBUG
# Неоплаченные online-заказы: отмена + снятие резерва (минуты)
ONLINE_PAYMENT_TIMEOUT_MINUTES = int(
    os.getenv('ONLINE_PAYMENT_TIMEOUT_MINUTES', '20')
)
# INT-007: TTL distributed lock для Celery expire/reconcile (сек.)
PAYMENTS_EXPIRE_LOCK_TTL_SECONDS = int(
    os.getenv('PAYMENTS_EXPIRE_LOCK_TTL_SECONDS', '240') or '240'
)
PAYMENTS_RECONCILE_LOCK_TTL_SECONDS = int(
    os.getenv('PAYMENTS_RECONCILE_LOCK_TTL_SECONDS', '180') or '180'
)
# Ops: включать только для внутреннего мониторинга (не публичный LB probe).
OPS_HEALTH_DETAILS = os.getenv('OPS_HEALTH_DETAILS', '').strip().lower() in (
    '1',
    'true',
    'yes',
)
# Оплата после cancel: manual | revive | reverse
LATE_ONLINE_PAYMENT_POLICY = (
    os.getenv('LATE_ONLINE_PAYMENT_POLICY', 'manual') or 'manual'
).strip().lower()

# --- ЮKassa (основной онлайн-эквайринг). Тест по умолчанию. ---
YOOKASSA_ENABLED = os.getenv('YOOKASSA_ENABLED', '').strip().lower() in (
    '1',
    'true',
    'yes',
    'on',
)
_yk_test = os.getenv('YOOKASSA_TEST_MODE', '1').strip().lower()
YOOKASSA_TEST_MODE = _yk_test not in ('0', 'false', 'no', 'off')
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '').strip()
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', '').strip()
YOOKASSA_API_URL = (
    os.getenv('YOOKASSA_API_URL', 'https://api.yookassa.ru/v3') or 'https://api.yookassa.ru/v3'
).rstrip('/')
YOOKASSA_RETURN_URL = os.getenv('YOOKASSA_RETURN_URL', '').strip()
YOOKASSA_WEBHOOK_URL = os.getenv('YOOKASSA_WEBHOOK_URL', '').strip()
YOOKASSA_TIMEOUT = int(os.getenv('YOOKASSA_TIMEOUT', '30'))

# Redis Cache Configuration (задача 2.5.1)
CACHE_TIMEOUT_PRODUCTS_LIST = 60  # список товаров; сигналы инвалидируют при сохранении в админке
CACHE_TIMEOUT_CATEGORIES = 600      # 10 минут — дерево категорий

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ringoo',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ringoo_sessions',
        'TIMEOUT': 1209600,  # 2 weeks
    },
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# Sentry Configuration (if DSN is provided)
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        sentry_sdk = None
    else:
        _sentry_integrations = [
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
            ),
            LoggingIntegration(
                level=None,
                event_level=None,
            ),
        ]
        try:
            from sentry_sdk.integrations.celery import CeleryIntegration

            _sentry_integrations.append(CeleryIntegration())
        except ImportError:
            pass
    
    # Фильтрация чувствительных данных
    def before_send(event, hint):
        """
        Фильтрует чувствительные данные перед отправкой в Sentry.
        """
        # Удалить чувствительные поля из request data
        if 'request' in event:
            # Список чувствительных полей для удаления
            sensitive_fields = [
                'password', 'password1', 'password2',
                'secret', 'secret_key', 'api_key', 'api_secret',
                'token', 'access_token', 'refresh_token',
                'authorization', 'auth',
                'credit_card', 'card_number', 'cvv',
                'ssn', 'social_security_number',
                'phone', 'email', 'full_name', 'delivery_address',
                'address', 'city', 'street', 'house', 'apartment', 'postal_code',
            ]
            
            # Фильтрация cookies
            if 'cookies' in event.get('request', {}):
                for field in sensitive_fields:
                    event['request']['cookies'].pop(field, None)
            
            # Фильтрация data (POST/PUT данные)
            if 'data' in event.get('request', {}):
                for field in sensitive_fields:
                    event['request']['data'].pop(field, None)
            
            # Фильтрация query string
            if 'query_string' in event.get('request', {}):
                query_string = event['request']['query_string']
                if isinstance(query_string, str):
                    # Простая фильтрация query string
                    for field in sensitive_fields:
                        if f'{field}=' in query_string:
                            # Заменить значение на [FILTERED]
                            import re
                            event['request']['query_string'] = re.sub(
                                f'{field}=[^&]*',
                                f'{field}=[FILTERED]',
                                query_string
                            )
        
        # Фильтрация user данных
        if 'user' in event:
            # Не отправлять email и другие чувствительные данные
            if 'email' in event['user']:
                event['user']['email'] = '[FILTERED]'
            if 'username' in event['user']:
                event['user']['username'] = '[FILTERED]'
        
        # Фильтрация extra данных
        if 'extra' in event:
            for field in sensitive_fields:
                event['extra'].pop(field, None)
        
        return event
    
    if sentry_sdk is not None:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=_sentry_integrations,
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,  # Не отправлять PII по умолчанию
            before_send=before_send,  # Фильтрация чувствительных данных
            environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
            release=os.getenv('SENTRY_RELEASE', None),  # Версия приложения (опционально)
            max_breadcrumbs=50,
            attach_stacktrace=True,
            ignore_errors=[
                KeyboardInterrupt,
                'django.http.Http404',
                'django.http.Http403',
            ],
        )
