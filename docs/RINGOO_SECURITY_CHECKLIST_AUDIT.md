# Аудит безопасности Ringoo по `docs/SECURITY.txt`

**Дата:** 2026-03-28 (обновление мер в коде: 2026-05-16 — refresh throttle, CSRF cookie-JWT, RBAC Admin API, ConsentRecord, обезличивание заказов, upload hardening)  

**Объект:** репозиторий Ringoo (Django REST + Next.js, Docker, GitHub Actions).  
**Метод:** сопоставление реализации в коде и конфигурациях с пунктами чек-листа `docs/SECURITY.txt`.

## Краткая оценка

**Базовый уровень:** Argon2/PBKDF2, prod HTTPS/HSTS/secure cookies, CORS в prod, blacklist refresh (SimpleJWT), идемпотентность заказа, фильтрация заказов по пользователю, CSP (Next + выборочно Django), Sentry с фильтрацией, Celery JSON, Bandit + pip-audit в backend CI, npm audit (high) во frontend CI, DRF throttling по scope (в т.ч. `/auth/token/`), тесты rate limit и IDOR.

**Доработки в коде (этапы 1–10):** django-axes (блокировка перебора), опциональная TOTP для Django admin (`ADMIN_OTP_ENABLED`, см. `docs/DJANGO_ADMIN_OTP.md`), JWT `iss`/`aud` и проверка при decode, access JWT по умолчанию **30 мин**, фронт: в **production** по умолчанию режим HttpOnly-кук (`src/lib/auth-mode.ts`), override Compose без портов БД/Redis на хост (`docker-compose.no-host-db-redis-ports.yml`), workflow Trivy для образа backend (`exit-code: 1`), ручной workflow нагрузки (`load-test-manual.yml` + `docs/LOAD_TESTING.md`), `eslint-plugin-security`, ZAP baseline (ручной dispatch).

**Май 2026:** throttle `/auth/token/refresh/`, `JwtCookieCsrfMiddleware`, RBAC Admin API (`ringoo_*` + `seed_admin_groups`), `ConsentRecord`, обезличивание заказов при `delete-account`, лимиты upload/zip-slip, расширенный `AuditLog`, `docs/SECURITY_BASELINE.md`.

**Вне репозитория (эксплуатация / юристы):** TLS ≥1.2 только на балансировщике, политика секретов и доступа к админке по VPN, актуальность текстов политик, внешний пентест перед публичным запуском, read-only rootfs контейнеров — по политике хостинга.

---

## Неприменимые пункты чек-листа (пропущены по вашему правилу)

Следующие блоки **в текущем коде не реализованы** — пункты про них из `SECURITY.txt` здесь не дублируются как «нарушения»:

- **§1.1 SMS-аутентификация** — нет отправки/проверки SMS-кодов в кодовой базе.
- **§5.1** (интеграция с платёжным шлюзом, webhooks, PAN/CVV) — в проекте есть способы оплаты как поля заказа (`cash`, `card_on_delivery`, …); отдельного приёма карт и webhooks нет (см. `docs/PAYMENTS.md`).
- **§1.3.5** «забыли пароль» — отдельного флоу не видно (логин по телефону + пароль).
- **§8.4.1** возраст 18+ — нет явной категории товаров/проверки в коде.

При появлении этих функций нужно заново прогнать соответствующие подразделы чек-листа.

---

## 1. Аутентификация и управление сессиями

| № чек-листа | Статус | Комментарий и риск | Рекомендация |
|-------------|--------|-------------------|--------------|
| 1.2.1 | ✅ | Бэкенд: HttpOnly JWT-куки (`JWT_COOKIE_*`, `JWTCookieAuthentication`). Фронт: `authCookiesMode()` — в **production** по умолчанию куки (если не `NEXT_PUBLIC_USE_AUTH_COOKIES=false`); `apiClient` с `withCredentials`. В dev можно Bearer + `localStorage`. | Для staging задать `NEXT_PUBLIC_USE_AUTH_COOKIES=1` явно. |
| 1.2.2 | ✅ | `ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION` в `config/settings/base.py`. | — |
| 1.2.3 | ✅ | Подключён `rest_framework_simplejwt.token_blacklist`. | Периодически чистить устаревшие записи blacklist при росте БД. |
| 1.2.4 | ⚠️ | **HS256**, ключ = `SECRET_KEY`. В **production** — проверка длины и запрет `django-insecure` (`production.py`). | RS256 + vault — по мере зрелости. |
| 1.2.5 | ✅ | Access по умолчанию **30 мин** (`JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `base.py`), refresh 7 дней. | При политике 15 мин — только env. |
| 1.2.6 | ✅ | `SIMPLE_JWT`: `ISSUER` / `AUDIENCE` → в токене `iss`/`aud`; `TokenBackend.decode` проверяет `aud` при ненулевой audience (`rest_framework_simplejwt.backends`). | В prod задать уникальные `JWT_ISSUER` / `JWT_AUDIENCE`. |
| 1.3.1 | ✅ | Регистрация: уникальный нормализованный телефон, дубликат отклоняется (`RegisterSerializer`). | Учитывать политику «подтверждение владения номером», если позже появится SMS. |
| 1.3.2 | ✅ | `min_length=8` в регистрации + стандартные `AUTH_PASSWORD_VALIDATORS` в `base.py`. | При желании усилить политику (сложность) на бэкенде теми же валидаторами. |
| 1.3.3 | ✅ | **django-axes**: lockout по связке username+IP, JSON 429 через `AXES_LOCKOUT_CALLABLE`; в тестах `AXES_ENABLED=False`. После обновления: `python manage.py migrate`. | За reverse-proxy: `AXES_IPWARE_PROXY_COUNT` и доверенные заголовки. |
| 1.3.4 | ✅ | Поле `last_login_ip`, письмо при смене IP (`record_successful_password_login` → `send_new_login_alert`). | — |

---

## 2. Безопасность API (DRF)

| № чек-листа | Статус | Комментарий и риск | Рекомендация |
|-------------|--------|-------------------|--------------|
| 2.1.1 | ⚠️ | Заказы + избранное: фильтрация по пользователю; добавлены регресс-тесты `wishlist/tests.py`, заказы уже в `orders/tests.py`. | Продолжать IDOR-тесты для новых ресурсов. |
| 2.1.2 | ✅ | Каталог, магазины и **контент** (статьи/новости/теги): read-only ViewSet’ы с `AllowAny` + read throttles (`content/views.py`, `products`, `stores`). | При новых публичных GET — сохранять явный `AllowAny`. |
| 2.1.3 | ⚠️ | Admin API: `IsStaff` (`admin_api/permissions.py`). Детальные роли внутри staff чек-лист не подтверждает из кода. | Группы Django + разделение прав на уровне моделей/админки. |
| 2.1.4 | ⚠️ | Celery-задачи принимают id (`send_order_notifications`, CRM stub) — ок; при добавлении задач «от имени пользователя» нужны проверки. | Продолжать передавать только ID, проверять сущности в задаче. |
| 2.2.1–2.2.4 | ✅ | `delivery_address`: модуль `orders/delivery_address.py` — только разрешённые ключи, лимиты длины, запрет вложенных структур; `OrderCreateSerializer.validate_delivery_address`. | — |
| 2.2.5 | ✅ | Самовывоз: обязателен `store`, проверка `Store` с `is_active=True`; доставка: поле `store` запрещено (сброс в `None`). | Политика «магазин доступен пользователю» при появлении ограничений по региону — отдельно. |
| 2.3.1–2.3.3 | ✅ | Не обнаружено `raw()` / `extra()` с пользовательскими данными в выборке. | Запретить в code review. |
| 2.3.4 | ⚠️ | Индексы — по моделям частично есть (аудит, пользователь); полный аудит индексов вне scope. | Профилирование медленных запросов под нагрузкой. |
| 2.4.1–2.4.3 | ✅ | Нет `fields = '__all__'` в сериализаторах; заказ: `user` выставляется в view, не из тела. | Сохранять дисциплину `read_only_fields`. |

---

## 3. Данные и конфиденциальность

| № чек-листа | Статус | Комментарий | Рекомендация |
|-------------|--------|-------------|--------------|
| 3.1.1 | ✅ | Argon2 + PBKDF2 в `PASSWORD_HASHERS`. | — |
| 3.1.2–3.1.3 | ⚠️ | ПДн в БД открыто (норма для доставки); Sentry — `before_send`. В **консоль и файлы** добавлен `RedactPIIFilter` (`config/logging_filters.py`) в `development.py` и `production.py`. | Политика ретенции логов на стороне хостинга. |
| 3.1.4 | ⚠️ | Команда `python manage.py cleanup_deactivated_users` (`--min-days`, без `--execute` = dry run): удаление **уже деактивированных** обычных пользователей с устаревшим `updated_at`. Периодический запуск — cron/Celery beat по политике компании. | Не удаляет активных; не трогает staff/superuser. |
| 3.1.5 | ✅ | Нет хранения карт в коде. | При интеграции ПС — только токены провайдера. |
| 3.2.1–3.2.2 | ✅ (prod) | `production.py`: `SECURE_SSL_REDIRECT`, HSTS, secure session/CSRF cookies. | Включить только за корректным TLS-терминатором. |
| 3.2.3 | ⚠️ | Next.js: CSP в `next.config.ts` (есть `unsafe-inline` / `unsafe-eval` под Яндекс.Карты). Django: CSP для HTML и docs (`SecurityHeadersMiddleware`). JSON-ответы API без CSP — ожидаемо. | Ужесточить по мере отказа от inline. |
| 3.2.4 | ⚠️ | TLS на стороне **инфраструктуры** (nginx/ingress), не в репозитории. | Явно отключить TLS ≤1.1 на балансировщике. |
| 3.3.1 | ⚠️ | Префикс админки: **`DJANGO_ADMIN_URL`** → `ADMIN_SITE_URL_PATH` в `base.py`, маршрут в `config/urls.py` (по умолчанию `admin`). | В проде — неочевидный префикс + ограничение доступа на reverse-proxy (VPN/IP). |
| 3.3.2 | ✅ (опц.) | **django-otp** + TOTP: `ADMIN_OTP_ENABLED=1`, `migrate`, см. `docs/DJANGO_ADMIN_OTP.md`; `OTPAdminSite` через замену класса `admin.site` в `config/urls.py`. По умолчанию выкл. | SSO с MFA для крупных команд. |
| 3.3.3 | ⚠️ | `OrderAdmin`: аудит смены статуса (`save_model`), массового «Подтверждён», экспорта CSV через `log_admin_action`. | Продолжить для других чувствительных моделей. |
| 3.3.4 | ⚠️ | Зависит от настройки групп в проде. | Матрица прав по ролям. |

---

## 4. OWASP Top 10 (фрагмент чек-листа)

| № | Статус | Комментарий |
|---|--------|-------------|
| 4.1.x | ⚠️ | React/Next по умолчанию экранирует; не найдено `dangerouslySetInnerHTML` в `src` (кроме необходимости перепроверить сторонние виджеты). CSP на фронте смягчена под карты. |
| 4.2.1–4.2.3 | ⚠️ | JWT-эндпоинты с `csrf_exempt` — осознанная схема для SPA; при **cookie-only** авторизации нужен CSRF для state-changing запросов. Документировано в `users/views.py`. |
| 4.2.4 | ✅ | Изменение состояния через POST/PUT/PATCH (типичный DRF). |
| 4.4.1 | ✅ | Celery: `CELERY_ACCEPT_CONTENT = ['json']`, сериализаторы json. |
| 4.4.2 | ✅ | Нет `eval`/`exec` от пользовательских данных в просмотренных путях. |
| 4.5.x | ⚠️ | UUID заказов; защита — **проверка владельца** в `OrderDetailView` — реализована. |
| 4.6.1 | ✅ (prod) | `DEBUG` из env, `ALLOWED_HOSTS` обязателен при `DEBUG=False`. |
| 4.6.2 | ⚠️ | В `base.py` fallback для dev; в **production** — проверка длины/префикса. В **development.py** при слабом ключе и `DEBUG` — `warnings.warn`. |
| 4.6.3–4.6.4 | ⚠️ | Compose: предупреждение в шапке; опционально **`REDIS_PASSWORD`** (`requirepass`) + **`REDIS_URL`** через env (`redis://:пароль@redis:6379/0`); Celery берёт тот же Redis из `CELERY_BROKER_URL` fallback в `base.py`. Порты на хост — для локалки; в проде не экспонировать. Сильные **`DB_*`**. |
| 4.6.5 | ⚠️ | Медиа в DEBUG отдаются статикой Django; в prod обычно nginx/S3 — настраивать ACL. | |
| 4.7.1 | ✅ | Sentry при `SENTRY_DSN`. | |
| 4.7.2 | ⚠️ | Логгер **`ringoo.security.auth`**: `auth_login_failed` (неверный пароль), `auth_refresh_failed`; идентификатор маскируется, пароль не пишется. Настроен в `development.py` / `production.py`. | Алерты в SIEM/Sentry по этому логгеру. |
| 4.7.3 | ⚠️ | Зависит от настройки Sentry/мониторинга вне репо. | Алерты на 5xx и spike `auth_login_failed`. |
| 4.7.4 | ⚠️ | `RedactPIIFilter` на handlers + события security с маской телефона. |

---

## 5. Платежи и интеграции

| № | Статус | Комментарий |
|---|--------|-------------|
| 5.1.* | — | Нет живого шлюза; ориентир — `docs/PAYMENTS.md` при внедрении. |
| 5.2.1 | ✅ | Ключи геокодера и т.д. из env (`YANDEX_GEOCODER_API_KEY`). |
| 5.2.2 | ✅ | `EXTERNAL_API_TIMEOUT`; геокодер: проверка структуры JSON (`_validate_yandex_geocode_response` в `integrations/maps_service.py`). |
| 5.2.3 | ⚠️ | Повторы при 429/502–504 через **tenacity** (`maps_service.py`); отдельный circuit breaker (напр. Redis) — при высокой нагрузке на геокодер. |
| 5.2.4 | ✅ | CRM stub: телефон через `mask_phone`, имя товара до 80 симв. (`apps/crm/tasks.py`). |

---

## 6. Фронтенд (Next.js)

| № | Статус | Комментарий |
|---|--------|-------------|
| 6.1.1 | ✅ | Нет опасного `dangerouslySetInnerHTML` в основном `src`. |
| 6.1.3 | ✅ | CSP в `next.config.ts`. |
| 6.2.1–6.2.2 | ✅ | Cookie-режим в prod по умолчанию (`auth-mode.ts`); dev — localStorage при отключённых куках. |
| 6.2.3 | ⚠️ | При переходе на cookie-JWT — обеспечить CSRF (Double Submit или SameSite + строгая политика). |
| 6.3.1 | ✅ | `frontend-ci.yml`: `npm audit --omit=dev --audit-level=high` после `npm ci`. |
| 6.3.2 | ⚠️ | Внешние скрипты карт — проверить SRI где возможно (у динамических loader’ов часто нет). |
| 6.4.1 | ✅ | `orders/[id]`: проверка UUID перед запросом (`src/lib/validation/route-params.ts`). |
| 6.4.2 | ⚠️ | `middleware.ts`: при **cookie-режиме** (`authCookiesMode`) редирект без `ringoo_access`/`ringoo_refresh`; иначе — только клиент (`useAuth`). Публично: `/orders/success`, `…/orders/<id>/success`. |
| 6.4.3 | ⚠️ | Middleware не заменяет проверку прав на API; для `/admin/*` — по-прежнему `AdminGuard` + API. |

---

## 7. Инфраструктура и DevOps

| № | Статус | Комментарий |
|---|--------|-------------|
| 7.1.1 | ⚠️ | **Production** `Dockerfile`: пользователь `django` — ✅. **Dockerfile.dev** / compose web: без `USER` — root (допустимо для dev). |
| 7.1.2 | ⚠️ | Read-only rootfs/tmpfs — политика оркестратора (Kubernetes `securityContext`, не в dev compose). | Задать в prod-чартах / у провайдера. |
| 7.1.3 | ⚠️ | Dev compose публикует порты для удобства; для закрытого контура: второй файл **`docker-compose.no-host-db-redis-ports.yml`** (override без `ports` у db/redis). |
| 7.1.4 | ⚠️ | Образы с тегами `15-alpine`, `7-alpine` — не `:latest`, но без pin по digest. |
| 7.2.1 | ⚠️ | Секреты в GH Actions через `secrets` — ок; не логировать значения. |
| 7.2.2 | ✅ | **Bandit** + **`pip-audit`** (job security) в `backend-ci.yml`. |
| 7.2.3 | ⚠️ | **Trivy** для образа backend: `.github/workflows/container-trivy.yml` (при необходимости смените `exit-code` на `1` после устранения базовых находок). |
| 7.2.4 | ⚠️ | Нет manual approval для production в workflow (зависит от политики org). |
| 7.3.* | ⚠️ | Бэкапы/ротация логов — в `docs/BACKUP.md` и эксплуатации, не в коде. |

---

## 8. Юридические требования (152-ФЗ / GDPR)

| № | Статус | Комментарий |
|---|--------|-------------|
| 8.1.1 | ✅ | Регистрация: обязательный чекбокс + ссылки на `/docs/privacy`, `/docs/offer`; API `consent_personal_data` + `privacy_policy_accepted_at` в `CustomUser`. Заказ по-прежнему с `consent_personal_data`. |
| 8.1.2 | ✅ | Опциональный чекбокс маркетинга при регистрации; поля `marketing_opt_in` / `marketing_opt_in_at`. |
| 8.1.3 | ✅ | ЛК: отзыв маркетинга (чекбокс + `PATCH /auth/me/`), удаление аккаунта (`POST /auth/delete-account/` + UI). |
| 8.1.4 | ⚠️ | Ссылки в футере и в формах; актуальность текста политики — зона юриста. |
| 8.2.1–8.2.3 | ⚠️ | Экспорт JSON: `GET /auth/me/export/` + кнопка в профиле. Удаление: `delete-account` + очистка корзины/избранного/адресов; заказы остаются привязанными к записи пользователя для учёта — при необходимости донастроить политику хранения. |
| 8.3.x | ⚠️ | Контент на главной (доставка/оферта) — проверка юристом вне кода. |

---

## 9. Celery и фоновые задачи

| № | Статус | Комментарий |
|---|--------|-------------|
| 9.1.1 | ⚠️ | По умолчанию Redis без `requirepass` (локалка). В `docker-compose.yml`: при `REDIS_PASSWORD` — `requirepass` + `REDIS_URL` с паролем; порты наружу — только в dev. |
| 9.1.2 | ✅ | Базовый класс `RingooTask` в `config/celery.py`: `autoretry_for` (сеть/OSError), backoff + jitter, `max_retries=5`. |
| 9.1.3 | ⚠️ | `Dockerfile.dev`: root для web/celery — ожидаемо для dev; prod — отдельный образ с `USER` (см. `Dockerfile`). |
| 9.1.4 | ✅ | Задачи по ID сущностей; нет произвольных действий от «сырого» user input. |
| 9.2.1 | ✅ | Не передаются пароли/карты в аргументах задач. |
| 9.2.2 | ✅ | Логирование; CRM — маскирование ПДн (§5.2.4). |
| 9.2.3 | ✅ | `Order.confirmation_email_sent_at` + проверка в `send_order_notifications`; тест `TestSendOrderNotificationsIdempotent`. |

---

## 10. Тестирование безопасности

| № | Статус | Комментарий |
|---|--------|-------------|
| 10.1.1 | ✅ | Bandit в CI; flake8-bandit — по желанию. |
| 10.1.2 | ✅ | `pip-audit` в job security `backend-ci.yml` (`--fail-on=high` или по политике проекта). |
| 10.1.3 | ✅ | `eslint-plugin-security` в `frontend/eslint.config.mjs` (recommended, warn). |
| 10.2.1 | ⚠️ | DAST: `dast-zap-baseline.yml` (ручной dispatch); не в каждом PR. |
| 10.2.2 | ✅ | Заказы + IDOR списка (`test_get_list_idor_excludes_other_users_orders`). |
| 10.2.3 | ✅ | `backend/tests/test_rate_limits.py`: 429 для `/auth/token/`, POST заказа anon/user. |
| 10.3.* | ⚠️ | Сценарии и k6 в `docs/LOAD_TESTING.md` / `scripts/`; в Actions — ручной **`load-test-manual.yml`** (фиксация прогона, без автоматического k6 в каждом PR). |

---

## Критичные и высокоприоритетные действия (до публичного продакшена)
1. **Инфраструктура:** не публиковать PostgreSQL/Redis в интернет; `REDIS_PASSWORD` и URL с паролем; сильные `DB_*`; при необходимости — `docker-compose.no-host-db-redis-ports.yml`.  
2. **Секреты:** уникальный длинный `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`; TLS ≥1.2 на балансировщике.  
3. **Токены:** в staging/prod явно `NEXT_PUBLIC_USE_AUTH_COOKIES=1` и `JWT_COOKIE_SECURE` при HTTPS; при желании RS256.  
4. **Брутфорс:** throttle на `/auth/token/` уже в `REST_FRAMEWORK`; дополнительно **django-axes** (после `migrate`).  
5. **Админка:** неочевидный `DJANGO_ADMIN_URL`, VPN/IP; опционально **`ADMIN_OTP_ENABLED=1`** (`docs/DJANGO_ADMIN_OTP.md`).  
6. **152-ФЗ / юристы:** актуальность политик; политика хранения заказов после удаления аккаунта.  
7. **CI:** ужесточить Trivy (`exit-code: 1` в `container-trivy.yml` после разбора); периодически ZAP и нагрузка по `docs/LOAD_TESTING.md`.

---

## Улучшение процесса разработки

- Включить **зависимостный аудит** (Python + Node) в каждый PR.  
- Периодически **сканировать Docker-образы** и обновлять базовые образы.  
- Добавить **интеграционные тесты** на авторизацию и изоляцию данных.  
- Перед запуском — **внешний пентест** и ручной прогон чек-листа OWASP для новых фич (платежи, SMS, загрузка файлов).  
- Зафиксировать **политику логирования** (что маскируем, срок хранения, кто имеет доступ).

---

## Дополнительные наблюдения (вне таблицы чек-листа)

- **Документация угроз** в `apps/users/views.py` по JWT и CSRF — полезно для онбординга; стоит продублировать кратко в `docs/SECURITY.md` для команды фронта.  
- **Идемпотентность заказа** через `X-Idempotency-Key` — сильная практика; распространить на другие критичные POST при появлении.

---

*Отчёт составлен по состоянию репозитория на дату указанная выше; после значимых изменений в auth, платежах или инфраструктуре аудит следует обновить.*
