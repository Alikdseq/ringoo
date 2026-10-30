# Security audit report — Ringo (локальный аудит, без deploy)

**Статус:** этапы 1–2 + **этап 3 (npm critical)** — локально; **без** commit / push / deploy.  
**Дата:** 2026-10-29  
**Объём:** backend Django/DRF; frontend npm deps; deps audit; git pattern-scan; prod checklist.  
**Ограничения:** без реальных платежей/POST в 1С/production; без commit/push/deploy; секреты в отчёте не приводятся.

---

## A. Executive summary

| Метрика | Значение |
|--------|----------|
| Критические области проверены | Оплата, IDOR, секреты, 1С HTTP/XML, mass assignment, staff escalation, rate limits, admin Payment, callback oracle |
| Найдено подтверждённых проблем | 10 (SEC-01…SEC-10); Critical path «клиент ставит paid» — **не найден** |
| Исправлено в коде | 10 |
| Осталось (residual) | См. раздел G / Stage 2 |
| Блокеры production | Владелец: callback token; owner checklist; Postgres concurrency; ручная smoke UI на staging |
| Stage 2 tooling | `pip-audit`: OK; Postgres races: **не доказаны**; gitleaks/trufflehog: не установлены |
| Stage 3 npm | **`npm audit`: 0 vulnerabilities** после обновлений (было 29–38 с critical) |

**Ключевой вывод по оплате:** клиентский `paid=true` / success URL / callback body сами по себе **не** переводят заказ в оплаченный. Единственный путь к `Payment.STATUS_PAID` — `sync_payment_from_bank` после `getOrderStatusExtended` с fail-closed сверкой суммы, `orderNumber` и валюты.

---

## B. Реестр уязвимостей

### SEC-01 — Подтверждение оплаты без обязательной сверки amount/orderNumber (High → закрыто)

- **Категория:** Payment integrity  
- **Критичность:** High (до фикса); после фикса — mitigated  
- **Файлы:** `backend/apps/payments/services.py`  
- **Первопричина:** при `orderStatus=paid` отсутствие `amount` в ответе банка пропускалось; `orderNumber`/`currency` не сверялись.  
- **Сценарий:** скомпрометированный/ошибочный ответ статуса (или неполный mock в staging) мог отметить paid без привязки к merchant order.  
- **Влияние:** ложное подтверждение оплаты → товар/1С.  
- **Исправление:** `_reject_untrusted_paid_payload` — fail-closed до paid/needs_review.  
- **Тест:** `tests/test_payment_security.py` (`test_missing_bank_amount_*`, `test_foreign_order_number_*`, `test_currency_mismatch_*`) — **passed**.  
- **Остаточный риск:** зависит от полноты полей в реальном ответе Sber; при их отсутствии оплата останется failed до ручной сверки.

### SEC-02 — Клиентский `delivery_cost` влиял на `total_amount` (High → закрыто)

- **Категория:** Amount tampering  
- **Endpoints:** create order  
- **Файлы:** `backend/apps/orders/serializers.py`  
- **Первопричина:** `delivery_cost` из тела участвовал в расчёте итога (цены товаров уже брались с сервера).  
- **Сценарий:** при появлении платной доставки клиент мог занизить/завысить сумму. Сейчас checkout шлёт `0`, но доверие к клиенту опасно.  
- **Исправление:** сервер принудительно `delivery_cost=0` и пересчитывает total.  
- **Тест:** `test_client_cannot_set_order_paid_via_create_fields` — **passed**.  
- **Остаточный риск:** при вводе платной доставки нужен серверный тариф, не возврат доверия клиенту.

### SEC-07 — Callback `found` oracle (High → закрыто)

- **Категория:** Information disclosure  
- **Исправление:** ответ всегда `{"ok": true}`; `found` только в логах.  
- **Тест:** `test_callback_unknown_mdorder_still_200_no_oracle`  

### SEC-08 — Unthrottled payment status → bank amplification (High → закрыто)

- **Исправление:** throttle `payment_status_*` + debounce 5s по `last_status_checked_at`.  

### SEC-09 — Admin editable `Payment.status=paid` (Medium → закрыто)

- **Исправление:** `status`/`amount`/`order` readonly в Django admin; ops-action только `needs_review`→`failed`.  

### SEC-10 — IntegrityError на гонке двух paid (Medium → закрыто)

- **Исправление:** savepoint + catch `IntegrityError` → duplicate `FAILED`.  

### SEC-03 — Публичный Sber callback без разделяемого секрета (Medium → усилено на этапе 2)

- **Категория:** Webhook authenticity  
- **Endpoint:** `POST /api/v1/payments/sber/callback/`  
- **Исправление этап 1:** `SBER_ECOM_CALLBACK_TOKEN` (`?token=` / `X-Sber-Callback-Token`).  
- **Исправление этап 2:** fail-closed при `DEBUG=False` / `SBER_ECOM_CALLBACK_TOKEN_REQUIRED`; в `production.py` — `ImproperlyConfigured`, если `SBER_ECOM_ENABLED` и токен пуст.  
- **Тесты:** wrong/missing/required-unset/header/query — **passed** (`test_payment_security.py`).  
- **Владелец:** выставить секрет на staging — `docs/integrations/SBER_CALLBACK_STAGING.md`.  
- **Остаточный риск:** checksum банка — `docs/integrations/SBER_CONTRACT_QUESTIONS.md`.

### SEC-04 — Staff может назначать `is_staff` (High → закрыто)

- **Категория:** Privilege escalation  
- **Endpoint:** `PATCH /api/v1/admin/users/{id}/patch/`  
- **Исправление:** менять `is_staff` может только `is_superuser`.  
- **Тест:** `StaffEscalationSecurityTests` — **passed**.

### SEC-05 — XML каталога 1С через stdlib ET (Medium → закрыто)

- **Категория:** XXE / unsafe XML  
- **Файлы:** `integrations/onec/parser.py`  
- **Исправление:** `defusedxml.ElementTree` + перевод `DefusedXmlException` → `OneCParseError`.  
- **Тест:** `test_xxe_dtd_rejected` — **passed**.

### SEC-06 — Redirect/SSRF и безлимитное чтение ответа 1С (Medium → закрыто)

- **Категория:** SSRF / resource exhaustion  
- **Файлы:** `integrations/onec/client.py`  
- **Исправление:** `_SameHostRedirectHandler`, лимит 20 MiB, `_http_open` для тестов.  
- **Тесты:** существующие HTTP-моки обновлены — **passed**.  
- **Остаточный риск:** URL 1С только из settings (не от клиента) — ок; DNS rebinding не закрыт на уровне сокета.

### Informational / принятые риски

- Гостевой доступ к оплате: UUID заказа + телефон. UUID непредсказуем; телефон — knowledge factor. Rate limit на pay/track есть.  
- Admin может менять `Order.status` по allowlist переходов без платежа (операционный процесс) — не баг оплаты.  
- `NEXT_PUBLIC_YANDEX_*` — публичные ключи карт, не серверные секреты эквайринга.  
- Локальные `.env` / `backend/.env` существуют, в `.gitignore` — не коммитить; значения не аудировались в отчёт.

---

## C. Изменённые файлы (этот аудит)

| Файл | Суть |
|------|------|
| `backend/apps/payments/services.py` | Fail-closed binding; IntegrityError на dual-paid |
| `backend/apps/payments/views.py` | Callback token; без `found`; status throttle+debounce |
| `backend/apps/payments/admin.py` | status/amount/order readonly |
| `backend/apps/orders/serializers.py` | Server-side delivery_cost/total |
| `backend/apps/admin_api/views/users.py` | is_staff только superuser |
| `backend/config/settings/base.py` | `SBER_ECOM_CALLBACK_TOKEN`, payment_status rates |
| `backend/config/settings/test.py` | тестовые лимиты status |
| `backend/config/throttling.py` | PaymentStatus*Throttle |
| `backend/.env.example` | Документация callback token |
| `backend/integrations/onec/parser.py` | defusedxml |
| `backend/integrations/onec/client.py` | same-host redirect + size limit |
| `backend/tests/test_payment_security.py` | **новый** набор атак |
| `backend/tests/test_sber_payments.py` | orderNumber/currency; no oracle |
| `backend/tests/test_onec_http.py` / `test_onec_orders.py` | patch `_http_open`, XXE test |
| `backend/pyproject.toml`, `requirements.txt` | `defusedxml` |
| `backend/config/settings/production.py` | callback token required if Sber enabled |
| `backend/config/settings/test_postgres.py` | Postgres concurrency settings |
| `backend/tests/test_concurrency_postgres.py` | concurrent scenarios (skip without PG) |
| `docs/integrations/SBER_CALLBACK_STAGING.md` | staging token how-to |
| `docs/integrations/SBER_CONTRACT_QUESTIONS.md` | questions for Sber |
| `docs/SECURITY_OWNER_CHECKLIST.md` | infra owner checklist |
| `docs/SECURITY_AUDIT_REPORT.md` | этот отчёт |

Коммит/push **не** выполнялись. Прочие незакоммиченные изменения репозитория (1С этап B, frontend и т.д.) **не** удалялись.

---

## D. Результаты тестирования

Команды (локально, `DJANGO_SETTINGS_MODULE=config.settings.test`):

```text
pytest tests/test_payment_security.py tests/test_sber_payments.py \
  tests/test_onec_http.py tests/test_onec_orders.py \
  apps/orders/tests.py apps/users/tests_security_data.py \
  tests/test_admin_api_auth.py tests/test_rate_limits.py -q --no-cov
```

**Результаты (финал аудита):**

- Security-relevant suite: **128 passed, 1 skipped** (ранее); после follow-up (oracle/throttle/admin/IntegrityError): `test_sber_payments` + `test_payment_security` → **51 passed**.  
- БД тестов: Django test settings (обычно SQLite) — **не** полный proof гонок PostgreSQL.  
- Bandit (`-ll` на payments/sber/onec): High+ не выведено.  
- `pip-audit`: недоступен.  
- `npm audit`: ошибка lock-tree (не валидный результат CVE).  
- Frontend: `NEXT_PUBLIC_*` секретов эквайринга/1С нет; return page только читает серверный статус.

---

## E. Проверка защиты оплаты

| Сценарий | Результат | Тест |
|----------|-----------|------|
| Подтвердить оплату только через браузер / `paid=true` | Нет | `test_client_cannot_set_*`, `test_pay_endpoint_ignores_*`, `test_payment_status_get_does_not_accept_paid_query` |
| Подмена ID платежа/заказа в API | Нет доступа / нет paid | IDOR suite + binding |
| Подмена суммы клиентом | Сумма с БД/каталога | pay amount + delivery_cost force 0 |
| Чужой payment/orderNumber банка | Reject → failed | `test_foreign_order_number_*` |
| Повторный callback | Идемпотентно, один paid | `test_repeat_callback_idempotent_*` + unique constraint `payments_one_paid_per_order` |
| Недоступный Sber (timeout/500) | Не paid | `test_sber_timeout_*`, `test_sber_http_500_*` |
| Callback status=1 без банка paid | Не paid | `test_callback_payload_status_alone_*` |
| Поздняя оплата отменённого | `needs_review` (manual) | `test_late_payment_on_cancelled_*` |
| Success return page | Только читает API | frontend `payment/return` — UI |

---

## F. Проверка утечек

| Область | Статус |
|---------|--------|
| Исходный код (паттерны ключей/AWS/sk_live) | Совпадений не найдено |
| Git history глубокий dump | Не выполнялся полностью |
| `.env` / `backend/.env` | Есть локально, gitignored |
| Backend logs (код) | Клиент 1С/Sber санитизирует password/PAN; callback логирует mdOrder без секретов |
| Frontend `NEXT_PUBLIC_*` секреты эквайринга | Не найдены |
| API serializers Payment | read_only, без register_response в публичных fields |
| Docker/CI secrets | Точечно не верифицировались в runtime |
| Production config | Вне репозитория — блокер владельца |

**Если какой-либо пароль 1С/Sber когда-либо попадал в Git/чаты/логи — нужна ротация владельцем; удаление из файла недостаточно.**

---

## G. Остаточные риски (после этапа 2)

### Исправлено и подтверждено тестами

| Риск | Доказательство |
|------|----------------|
| Callback token fail-closed вне DEBUG / required | `test_callback_rejected_when_token_required_but_unset`, wrong/header/query tests — **55 passed** в payment suite (+5 skip Postgres) |
| Prod не стартует с Sber без токена | `config/settings/production.py` ImproperlyConfigured |
| pip Python CVE (requirements.txt) | `pip-audit -r requirements.txt` → **No known vulnerabilities found** |

### Проверено без замечаний (в пределах метода)

| Область | Результат |
|---------|-----------|
| `.env` в Git index | не отслеживаются; gitignored |
| Паттерн-скан истории | нет AWS keys / private keys / hardcoded SBER/ONE_C password assign; есть placeholder `django-insecure-dev-key-…` в старых коммитах (отклоняется production settings) |
| package-lock согласованность | `npm ls --package-lock-only` успешен (Node 22 / npm 10.9.3) |

### Не проверено / блокер среды

| Область | Причина |
|---------|---------|
| Гонки PostgreSQL | Нет `DATABASE_URL` / `RINGOO_TEST_POSTGRES`; тесты написаны, **5 skipped**. Команда: см. `docs/SECURITY_OWNER_CHECKLIST.md` |
| Gitleaks / TruffleHog | Не установлены; pattern `git grep` по истории — не полный entropy-scan |
| Live prod DEBUG/firewall/1С ACL | Только статический checklist владельца |

### Требует действия владельца

1. Выставить `SBER_ECOM_CALLBACK_TOKEN` + URL в кабинете — `docs/integrations/SBER_CALLBACK_STAGING.md`.  
2. Пройти `docs/SECURITY_OWNER_CHECKLIST.md`.  
3. Ответы банка — `docs/integrations/SBER_CONTRACT_QUESTIONS.md`.  
4. ~~Оценить npm critical~~ → **сделано на этапе 3** (`npm audit` = 0).  
5. При использовании реального `SECRET_KEY`/`django-insecure` только в dev — убедиться, что prod key другой и сильный.  
6. Ручной smoke UI после Next 16.4.3 (каталог, корзина, checkout return URL).

### Блокирует production (пока не сделано владельцем)

- Callback token на боевом/staging API.  
- Owner checklist (DEBUG, hosts, DB/Redis exposure, 1С сеть).  
- (Рекомендуется) прогон `test_concurrency_postgres` на тестовом Postgres.  
- Ручной smoke фронта на staging после bump Next.

---

## H. Этап 2 — артефакты

| Артефакт | Назначение |
|----------|------------|
| `docs/integrations/SBER_CALLBACK_STAGING.md` | Настройка токена staging |
| `docs/integrations/SBER_CONTRACT_QUESTIONS.md` | Вопросы к Сберу |
| `docs/SECURITY_OWNER_CHECKLIST.md` | Infra checklist |
| `backend/config/settings/test_postgres.py` | Postgres test settings |
| `backend/tests/test_concurrency_postgres.py` | Concurrent proofs (skip без флага) |

### npm audit (этап 2 → этап 3)

- Этап 2: 29 vuln (2 critical). Повторный JSON перед фиксом: до **38** (4 critical, вкл. vitest).  
- Этап 3: адресные обновления → **`npm audit`: found 0 vulnerabilities**.

### pip-audit (факт прогона)

- `python -m pip_audit -r requirements.txt` → **No known vulnerabilities found**.

---

## I. Этап 3 — npm critical / frontend deps

### Диагностика

| Параметр | Значение |
|----------|----------|
| Каталог | `frontend/` |
| Package manager | npm 10.9.3 (Node 22.20.0); установка через **npx npm@11.6.2** из‑за бага npm10 `edgesOut` |
| Sentry `tunnelRoute` | **не задан** в `next.config.ts` |
| Sentry `sendDefaultPii` | **не задан** (только `dsn` + `tracesSampleRate`) |
| Applicability GHSA-mchm-gjx6-7h55 | Низкая без `tunnelRoute`; пакет всё равно поднят ≥10.75.2 |

### Версии до → после (установленное дерево)

| Пакет | До | После |
|-------|-----|--------|
| `next` | 16.2.1 | **16.4.3** |
| `eslint-config-next` / `@next/bundle-analyzer` | 16.2.1 | **16.4.3** |
| `@sentry/nextjs` | 10.75.3 (^10.46) | **10.78.0** (^10.75.3) |
| `axios` | (tree ~1.13.x) | **1.21.0** |
| `zod` | ^4.3.6 | **4.6.7** |
| `vitest` / coverage-v8 | 4.0.x | **4.1.12** / ^4.1.11 |

### Устранённые advisory (ключевые)

- **next 16.2.1 → 16.4.3:** GHSA-673q-mjm6-r5xr, GHSA-2464-fhr4-w9xw, GHSA-vcvr-r3jv-pc5j, middleware/DoS/SSRF advisories из диапазона `<16.4.1` / `<16.3.x` (полный список в npm advisory для `next@16.2.1`).  
- **@sentry/nextjs ≥10.75.2:** GHSA-mchm-gjx6-7h55 (tunnel middleware bypass).  
- **axios ≥1.20:** high SSRF/prototype-pollution GHSA из audit.  
- **zod ≥4.6.6:** GHSA-mrhx-c7xc-m3w5.  
- **vitest ≥4.1.11:** critical tooling advisories.  
- Транзитивы `sharp`/`postcss`/`source-map-js`/`fflate` закрыты через next bump + `npm audit fix` (**без** `--force`).

### Изменённые файлы этапа 3

- `frontend/package.json`, `frontend/package-lock.json`  
- `frontend/tsconfig.json` — exclude `*.test.ts(x)` (Next 16.4.3 typecheck падал на vitest globals в тестах; `npm run type-check` уже исключал их)

### Проверки

| Команда | Результат |
|---------|-----------|
| `npm ls next @sentry/nextjs …` | next@16.4.3, @sentry/nextjs@10.78.0 |
| `npm audit` | **0 vulnerabilities** |
| `npm run type-check` | OK |
| `npm run lint` | 0 errors, 103 warnings (pre-existing) |
| `npx vitest run` | **30 files / 77 tests passed** |
| `npm run build` | **OK** (Next.js 16.4.3 Turbopack) |

### Ограничения / не проверялось вручную в браузере

- Главная, каталог, корзина, checkout, Sentry DSN на staging — **не** открывались в браузере в этом прогоне.  
- Deprecation: `withSentryConfig` из `@sentry/nextjs` → рекомендовать `@sentry/nextjs/config` до v11 (не блокер).  
- Для локального `npm install` на npm 10.9.x возможен `edgesOut`; prefer **npm ≥11.6** или `npx npm@11.6 install`.

### Готовность npm-части

| Вопрос | Ответ |
|--------|--------|
| Готово к staging (deps)? | **Да**, при условии smoke UI + callback token (этап 2). |
| Блокирует production? | Нет по CVE-счёту npm; остаются infra checklist и ручной smoke. |
| Риски | Регрессии Next 16.2→16.4 (proxy/middleware, image); проверить nested routes и оплату return URL вручную. |

---

## Критерии готовности (чеклист)

- [x] Этап 1: оплата / IDOR / 1С XML / admin (см. выше)  
- [x] Этап 2: callback fail-closed + тесты + staging doc  
- [x] Этап 2: concurrent tests подготовлены; Postgres недоступен → skip/blocker зафиксирован  
- [x] Этап 2: pattern secret scan истории + gitignore `.env`  
- [x] Этап 2: pip-audit выполнен; npm audit выполнен без force-fix  
- [x] Этап 2: production static checklist для владельца  
- [x] Этап 2: вопросы к Sber без смены протокола  
- [x] Этап 3: critical npm устранены; `npm audit` = 0; build/tests/typecheck OK  
- [x] Нет реальных платежей / 1С POST / commit / push / deploy  

**Система не объявляется «полностью защищённой».** Production-блокеры: owner checklist, callback token, ручной UI smoke; npm CVE-счётчик сейчас чист.
