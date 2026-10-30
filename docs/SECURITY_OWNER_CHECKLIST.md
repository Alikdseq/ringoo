# Checklist владельца инфраструктуры (production / staging)

Статический аудит кода **не** подтверждает эти пункты. Выполните на сервере/панели хостинга. Не подключайте Cursor к production без отдельного разрешения.

## 1. Django / приложение

| Проверка | Ожидание | Как проверить | Исправление |
|----------|----------|---------------|-------------|
| `DEBUG` | `False` | `echo %DEBUG%` / env панели; или Django shell: `settings.DEBUG` | `DEBUG=False` |
| `SECRET_KEY` | ≥48 символов, не `django-insecure-*` | длина env; production settings падают при слабом ключе | сгенерировать новый, ротировать JWT |
| `ALLOWED_HOSTS` | только ваши домены | env; пустой список → ImproperlyConfigured | задать CSV хостов |
| `CSRF_TRUSTED_ORIGINS` | https-origins фронта | env | добавить `https://shop…` |
| `CORS_ALLOW_ALL_ORIGINS` | запрещён в prod | код `production.py` + env | не ставить true |
| HTTPS cookies | `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` / `JWT_COOKIE_SECURE` = true | env | включить |
| HSTS | включён за reverse proxy / Django | заголовки ответа | TLS на proxy + `SECURE_HSTS_*` |

## 2. Sber

| Проверка | Ожидание |
|----------|----------|
| `SBER_ECOM_CALLBACK_TOKEN` | задан; совпадает с URL в кабинете |
| `SBER_ECOM_CALLBACK_URL` | HTTPS + `?token=…` |
| `SBER_ECOM_ALLOW_PRODUCTION` | `true` только для боевого epay после явного решения |
| `SBER_ECOM_ENABLED` | без токена в production → приложение не стартует |

Инструкция: `docs/integrations/SBER_CALLBACK_STAGING.md`. Вопросы к банку: `docs/integrations/SBER_CONTRACT_QUESTIONS.md`.

## 3. 1С

| Проверка | Ожидание |
|----------|----------|
| `ONE_C_API_BASE_URL` | только `/razrab/hs/`, не ut11_test |
| Сеть | 1С недоступна из интернета; только app-сервер / VPN |
| Учётка | минимальные права HTTP-сервисов Site* / Catalog* |
| `ONE_C_API_ENABLED` / `ONE_C_ORDER_SYNC_ENABLED` | false до готовности; пароль только env |

## 4. PostgreSQL / Redis

| Проверка | Ожидание |
|----------|----------|
| Слушают | не `0.0.0.0` без firewall |
| Auth | пароль, не trust извне |
| Backup | шифрование / ограниченный доступ к dump |
| Redis | ACL/пароль; не публичный |

Пример команд на хосте (адаптируйте):

```bash
ss -lntp | findstr ":5432"
ss -lntp | findstr ":6379"
```

## 5. Docker / CI

| Проверка | Ожидание |
|----------|----------|
| Секреты в образе | нет `.env` в слоях |
| CI secrets | masked; не echo в логах |
| Права runner | минимальные |

## 6. Логи

| Проверка | Ожидание |
|----------|----------|
| Нет паролей/токенов | выборка логов после тестового callback |
| Ротация | size/time limits |
| Доступ | только ops |

## Конкурентные тесты (когда есть тестовый Postgres)

```bash
set RINGOO_TEST_POSTGRES=1
set DATABASE_URL=postgres://USER:PASS@127.0.0.1:5432/ringoo_test
set DJANGO_SETTINGS_MODULE=config.settings.test_postgres
cd backend
pytest tests/test_concurrency_postgres.py -q --no-cov
```
