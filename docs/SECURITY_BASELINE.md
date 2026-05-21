# Security baseline — Ringoo

Чек-лист перед выкладкой в production. Подробный аудит: [`RINGOO_SECURITY_CHECKLIST_AUDIT.md`](RINGOO_SECURITY_CHECKLIST_AUDIT.md), реализация: [`SECURITY.md`](SECURITY.md).

## Обязательные переменные окружения (backend)

| Переменная | Требование |
|------------|------------|
| `DEBUG` | `False` |
| `SECRET_KEY` | ≥ 48 символов, не `django-insecure` |
| `ALLOWED_HOSTS` | Список доменов через запятую |
| `CORS_ALLOWED_ORIGINS` | Только фронтенд (https) |
| `CSRF_TRUSTED_ORIGINS` | Те же origin, что и CORS |
| `JWT_COOKIE_SECURE` | `True` при HTTPS |
| `DJANGO_ADMIN_URL` | Неочевидный префикс (не `admin`) |
| `ADMIN_OTP_ENABLED` | `1` для TOTP в Django Admin |
| `AXES_IPWARE_PROXY_COUNT` | Число прокси перед Django (если есть) |
| `REDIS_URL` | С паролем в prod (`redis://:pass@host:6379/0`) |
| `DB_PASSWORD` | Сильный пароль, БД не в интернете |
| `POLICY_VERSION` | Версия текста политики ПДн (для ConsentRecord) |
| `SENTRY_DSN` | Без `send_default_pii` в коде |

## Обязательные переменные (frontend)

| Переменная | Требование |
|------------|------------|
| `NEXT_PUBLIC_USE_AUTH_COOKIES` | `1` на staging и production |
| `NEXT_PUBLIC_API_V1_URL` | HTTPS URL API |
| `NEXT_PUBLIC_SITE_URL` | Канонический сайт (https://ringoo.ru) |

См. [`frontend/.env.example`](../frontend/.env.example).

## Инфраструктура (вне репозитория)

- TLS 1.2+ на балансировщике / Nginx
- `client_max_body_size` согласован с `DATA_UPLOAD_MAX_MEMORY_SIZE` Django
- PostgreSQL и Redis **не** опубликованы на хост (см. `docker-compose.no-host-db-redis-ports.yml`)
- Бэкапы БД: `pg_dump` + шифрование (GPG), хранение отдельно от приложения
- Ограничение доступа к `/admin/` и Admin SPA по VPN/IP на reverse-proxy
- Ключи Яндекс.Карт: ограничение по HTTP Referer в консоли

## Runbook: подозрение на утечку ПДн

1. Зафиксировать время обнаружения, затронутые системы и типы данных.
2. Остановить дальнейшую утечку (ротация ключей, блокировка IP, отключение скомпрометированных учёток).
3. Уведомить ответственного за ИБ и юриста (срок уведомления Роскомнадзора — по 152-ФЗ, обычно 72 часа).
4. Сохранить логи (`ringoo.security.auth`, Nginx, Sentry) без изменения.
5. После инцидента — обновить пароли staff, ротация `SECRET_KEY` / JWT blacklist, постмортем.

## Проверка после деплоя

```bash
curl -sI https://ringoo.ru | grep -iE 'strict-transport|content-security|x-frame'
curl -sI https://api.ringoo.ru/api/v1/health/  # при наличии health endpoint
```

- Ручной smoke: регистрация → checkout с согласием → logout → delete-account (обезличивание заказов).
- Периодически: ZAP baseline workflow, `pip-audit`, Trivy образов.

## Текущий статус кода (кратко)

| Область | Статус |
|---------|--------|
| JWT HttpOnly + blacklist | ✅ |
| django-axes + DRF throttles | ✅ |
| CSRF для cookie-JWT API | ✅ (`JwtCookieCsrfMiddleware`) |
| Admin API RBAC (группы) | ✅ (`seed_admin_groups`) |
| Обезличивание заказов при удалении аккаунта | ✅ |
| ConsentRecord (IP, версия политики) | ✅ |
| IDOR-тесты orders/wishlist | ✅ |
| 152-ФЗ: политика, согласия, cookie-баннер, Метрика по согласию | ✅ (см. `docs/RKN_OPERATOR_REGISTRATION.md`) |

## Утечка ПДн: шаблон уведомления (черновик для юриста)

**Кому:** Роскомнадзор (в срок, установленный 152-ФЗ и подзаконными актами; уточнить у юриста актуальный срок — часто 24–72 часа с момента выявления).

**От кого:** ООО «Рингу», контакт: (email из `NEXT_PUBLIC_PRIVACY_EMAIL` / реквизиты).

**Суть:** краткое описание инцидента, категории затронутых ПДн, примерное число субъектов, принятые меры по локализации, контакт для субъектов.

**Вложения:** хронология, список скомпрометированных систем, копии логов (без избыточной передачи самих ПДн в открытом виде).

Перед отправкой — обязательная вычитка юристом.
