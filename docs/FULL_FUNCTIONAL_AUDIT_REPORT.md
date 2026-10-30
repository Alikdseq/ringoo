# Полный функциональный аудит — Ringo (перед тестовым развёртыванием)

**Дата:** 2026-10-29  
**Объём:** frontend Next.js + backend Django/DRF + Celery + интеграции 1С / Сбер / онлайн-касса (код)  
**Ограничения аудита:** без commit / push / deploy; без реальных платежей и POST в боевую/тестовую 1С; без миграций, очищающих данные; секреты в отчёт не выводятся.  
**Связанный документ:** `docs/SECURITY_AUDIT_REPORT.md` (не перезаписывался).

---

## A. Executive summary

| Метрика | Значение |
|--------|----------|
| Общее состояние | Ядро магазина (каталог → корзина → checkout с фильтром магазинов по остаткам → заказ → оплата Сбер → синк 1С) **реализовано и покрыто backend-тестами**. Security-hardening оплаты уже выполнен ранее. |
| Можно ли начинать тестовое развёртывание? | **Да, на изолированный staging**, при выполнении условий из раздела H. |
| Вердикт | **READY FOR STAGING** |
| P0 (критические) | **0** подтверждённых незакрытых |
| P1 (блокирующие / высокий риск) | **1** операционный: warehouse mapping не в FE Admin API (Django Admin — OK после фикса fieldsets) |
| P2 (существенные) | **5** (is_warehouse публичный список — **исправлен 2026-10-30**) |
| P3 (косметика / tooling) | **4** |

**Ключевые риски перед staging:** незаполненные `Store.onec_warehouse_id`; незавершённая онлайн-касса; отсутствие живого smoke с тестовой 1С и Sber; Admin UI не редактирует `onec_warehouse_id`; склады-флаг `is_warehouse` не исключаются из выбора покупателем.

**Исправлено локально в этой сессии (без commit):**
1. Конфликт `apps/orders/services.py` ↔ пакет `services/` ломал `anonymize` и удаление аккаунта — модуль перенесён в `services/__init__.py`.
2. Фикстура `Category(name=…)` → `title` в `apps/users/tests.py` (2 падавших теста JWT на публичном каталоге).

---

## B. Архитектура

### Frontend
- Next.js App Router (`frontend/src/app`), ~53 `page.tsx`.
- API-клиент: `frontend/src/lib/api/client.ts` (axios, CSRF/cookies или Bearer, refresh, timeout 10s).
- Сервисы: `frontend/src/lib/api/services/*`.
- Состояние: TanStack Query + хуки корзины/авторизации.
- Admin UI: `/admin/*` через `AdminGuard` + `GET /auth/staff-access/`.

### Backend
- Django 5.1 + DRF, префикс `/api/v1/` (`config/api_urls.py`).
- Apps: users, products, stores, cart, orders, payments, content, promotions, crm, wishlist, admin_api; bonus смонтирован **выкл**.
- Celery: уведомления заказов, sync/cancel 1С (`orders/tasks.py`, `integrations/onec/tasks.py`).
- Health: `GET /health/`.

### База данных
- PostgreSQL (prod/staging); локальные pytest — Django test DB (SQLite/settings.test).  
- Конкурентные тесты Postgres: **skipped** без `RINGOO_TEST_POSTGRES=1` (6 skip).

### Внешние системы
| Система | Статус кода | Живая проверка |
|---------|-------------|----------------|
| 1С УТ 11 (каталог, регистрация, заказы) | `integrations/onec/*`, моки/фикстуры XML, pytest | **Не выполнена** (запрет POST без разрешения) |
| Сбер интернет-эквайринг | `payments/services.py`, callback token fail-closed | **Не выполнена** (запрет реальных платежей) |
| Онлайн-касса | `integrations/fiscal/` — **placeholder** `FiscalNotConfigured` | Не подключена |

### Схема обмена (критический путь)

```
UI catalog/PDP → GET products → cart POST items
→ checkout: GET stores + GET products/{id}/stock → filter stores
→ POST /orders/ (from_cart, store) → reserve only at store
→ on_commit enqueue_order_sync(paid=False)
→ online: POST /orders/{id}/pay → Sber formUrl
→ return/callback → sync_payment_from_bank (getOrderStatusExtended)
→ paid → enqueue_order_sync(paid=True)
→ warehouseId = Store.onec_warehouse_id
```

---

## C. Реестр страниц и маршрутов

Статус: **код + production build** (маршруты собраны Next). Браузерный E2E / живой HTTP к локальному backend в этой сессии **не запускались** (серверы не подняты; Playwright не настроен).

| Маршрут | Назначение | Auth | Проверка | Примечание |
|---------|------------|------|----------|------------|
| `/` | Главная | — | build | SSR products |
| `/catalog`, `/catalog/category/[slug]` | Каталог | — | build + BE products tests | |
| `/products/[slug]` | Карточка | — | build | stock + add to cart |
| `/cart` | Корзина | — | build + cart service | |
| `/checkout` | Оформление | optional | static+orders tests | фильтр магазинов по остаткам |
| `/orders`, `/orders/[id]` | Заказы | yes | IDOR tests | |
| `/orders/[id]/payment/return\|fail`, `/success` | Оплата UX | — | payment tests (BE) | success ≠ paid |
| `/order-status`, `/order-rate` | Трекинг / оценка | — | build | |
| `/stores`, `/stores/[slug]`, `/staff/[slug]` | Магазины / менеджеры | — | stores tests | |
| `/login`, `/register`, `/profile`, `/wishlist` | Auth / ЛК | mixed | users tests | |
| `/blog`, `/news`, `/[slug]` | Контент | — | build | **detail — placeholder**, BE detail unused |
| `/docs/*`, `/about`, `/promotions`, `/installment` | Инфо | — | build | |
| `/admin/*` | Админка FE | staff | admin_api_auth tests | warehouse 1C не в API |

Прямое открытие URL: App Router dynamic routes в build — OK. Отдельный 404 UI — не прогонялся в браузере.

---

## D. Реестр API (сжатый)

Полная карта FE↔BE собрана в ходе аудита (53 страницы, все `urls.py`, сервисы). Ниже — критические и расхождения.

Инвентаризация FE↔BE ([Functional audit inventory](e9ffd443-000d-4ba6-9d69-cc1210c7cb69), [FE-BE API contract map](7d803029-2215-41c7-884a-458544d587e6)): **жёстких опечаток method/path в активных вызовах FE не найдено**; пробелы те же (promocode validate, blog/news detail, reviews, bonus off, admin без `onec_warehouse_id`).

### Совпадающие критические контракты

| Метод | URL | Handler | FE | Тесты | Результат |
|-------|-----|---------|----|-------|-----------|
| GET/POST | `/cart/`, `/cart/items/`… | cart views | `cart.service.ts` | косвенно orders from_cart | **OK** контракт |
| GET | `/stores/` | StoreListView | checkout/stores | stores tests | **OK** |
| GET | `/products/products/<uuid>/stock/` | ProductStockView | checkout `getProductStock` | stores tests | **OK** |
| POST | `/orders/` | OrderListCreateView | checkout | orders tests 30p | **OK** (stock/store) |
| POST | `/orders/<id>/pay/` | OrderPayView | payments.service | sber + security | **OK** (моки) |
| GET | `/orders/<id>/payment/` | OrderPaymentStatusView | return page | security | **OK** |
| POST | `/payments/sber/callback/` | SberCallbackView | только банк | security | **OK** |
| JWT/auth | `/auth/*` | users views | auth.service | users tests | **OK** после фикса Category |

### Расхождения / неиспользуемое

| Находка | Оценка |
|---------|--------|
| `POST /promocodes/validate/` — нет FE на checkout | P2 (промокоды не в UX оформления) |
| `GET /stores/<uuid>/stock/` — FE не вызывает (использует product stock) | OK альтернатива |
| Blog/news detail endpoints не подключены к FE | P2 placeholder |
| Bonus API отключён в `api_urls` | ожидаемо |
| `StoreAdminSerializer` **не отдаёт** `onec_warehouse_id` | **P1 ops** |
| Public list не фильтрует `is_warehouse=True` | P2 |

---

## E. Функциональные сценарии

### Каталог
- List/detail/brands/models/autocomplete — реализованы; `apps/products/tests.py` passed.
- Пустой поиск / удалённые — частично unit; E2E не запускался.

### Корзина
- CRUD через session/user; checkout шлёт `items` + `from_cart` из‑за риска расхождения cookie/origin (комментарий в checkout).
- Итог на UI из `cart.total_amount`; на создании заказа **сервер пересчитывает** цены и `delivery_cost=0`.

### Оформление заказа
- Обязательны ФИО, телефон, магазин (pickup **и** delivery), адрес при delivery, согласие ПДн.
- FE блокирует магазины без полного наличия корзины; BE повторно резервирует **только** в выбранном `store_id` (`plan_and_reserve_at_store`).
- Идемпотентность: `Idempotency-Key` + cache.
- Доказано тестами: чужой остаток не используется; multi-item; insufficient → 400 `INSUFFICIENT_STOCK`.

### Магазины и остатки (бизнес-правила)
| Правило | Статус |
|---------|--------|
| Выбор только магазина с полным наличием | **FE + BE** (доказано) |
| Согласование pickup/delivery с store | store обязателен для обоих | 
| `warehouseId` из `Store.onec_warehouse_id` | **код** `resolve_warehouse_id`; без дефолтного склада |
| Нет автосмены магазина / перемещений | **соблюдено** |
| Нет оформления сверх остатка | **BE reserve** |
| Frontend не источник истины цены/итога | **OK** (serializer) |
| Серийные/несерийные | логика в `integrations/onec/orders.py` + тесты onec_orders |

### Пользователи
- Register/login/logout/me/export/delete + anonymize заказов — после фикса `services/` импорт работает; users tests passed.
- IDOR заказов: list/detail чужих → 404/исключение — passed.

### Платежи Сбер
- Paid только через bank status + сверка amount/orderNumber/currency (см. security report).
- Callback token fail-closed в non-DEBUG.
- Живой эквайринг **не проверялся**.

### 1С
- Каталог/HTTP/orders — моки XML и unit: `test_onec_*.py` passed (1 skip).
- Реальная тестовая база 1С — **блокер подтверждения интеграции**, не блокер деплоя кода на staging с `ONE_C_*` выкл. или mock URL.

### Онлайн-касса
- **Не реализована** (`FiscalNotConfigured`). Не считать подключённой.

### Админка
- Django Admin + FE `/admin/*` + `/api/v1/admin/*`.
- Staff escalation закрыт (security).
- Управление `onec_warehouse_id` — через Django Admin / БД, **не** через FE Admin API.

---

## F. Ошибки и исправления

### P1-FIX-01 — Shadowing `orders.services` (исправлено)

| Поле | Значение |
|------|----------|
| Файлы | было `apps/orders/services.py` + `services/anonymize.py`; стало `services/__init__.py` + `anonymize.py` |
| Воспроизведение | `from apps.orders.services.anonymize import …` → ModuleNotFoundError; delete-account падал бы в runtime |
| Ожидание | пакет `services` с cancel + anonymize |
| Факт | `services.py` перекрывал пакет |
| Риск | удаление аккаунта / 152-ФЗ anonymize |
| Исправление | содержимое cancel перенесено в `__init__.py`, файл-модуль удалён |
| Тест | `apps/users/tests.py` + `test_onec_orders` + orders — **passed** |

### P1-FIX-02 — Category fixture `name` (исправлено)

| Поле | Значение |
|------|----------|
| Файл | `apps/users/tests.py` `TestLenientJWTOnPublicCatalog` |
| Причина | модель `Category.title`, тест создавал `name=` |
| Исправление | `title="Phones"` |
| Тест | 2 кейса JWT на публичном каталоге — **passed** |

### P1-OPEN-01 — Admin API без `onec_warehouse_id`

| Поле | Значение |
|------|----------|
| Файлы | `admin_api/views/stores.py` StoreAdminSerializer; FE `adminStores.service.ts` |
| Риск | на staging склады 1С не настроить из FE admin → sync blocked |
| Рекомендация | добавить поля в admin serializer + UI **или** чеклист: заполнять в Django Admin до включения `ONE_C_ORDER_SYNC_ENABLED` |
| Не исправлялось | требует продуктового решения по поверхности admin |

### P2 реестр

| ID | Суть | Риск |
|----|------|------|
| P2-01 | ~~`is_warehouse` в публичном списке~~ | **Исправлено 2026-10-30:** StoreList/Detail/BySlug/ProductStock + OrderCreateSerializer; тесты stores/orders |
| P2-02 | Blog/news `[slug]` без API detail | контент-страницы заглушки |
| P2-03 | Промокоды не в checkout UX | скидки недоступны покупателю |
| P2-04 | Онлайн-касса placeholder | чеки не бьются |
| P2-05 | Vitest нестабилен (jsdom/undici) | 77p ранее / 10 fail+errors повторно | tooling |
| P2-06 | `pyproject.toml` `testpaths=["tests"]` — apps-тесты не в дефолтном прогоне CI, если CI не расширяет path | ложное «всё зелёное» |

### P3

| ID | Суть |
|----|------|
| P3-01 | ESLint: 0 errors, 103 warnings |
| P3-02 | Нет Playwright/E2E в репо |
| P3-03 | Postgres concurrency 6 skipped |
| P3-04 | `getDashboardStats` без страницы |

---

## G. Результаты тестирования

### Команды (локально)

| Команда | Результат |
|---------|-----------|
| `pytest apps/orders apps/users apps/products apps/stores apps/users/tests_security_data.py tests` | **201 passed, 6 skipped** |
| в т.ч. orders 30, stores 11, payment_security, sber_payments, onec_* | OK |
| `npm run type-check` | **exit 0** |
| `npm run build` | **exit 0** (все маршруты выше) |
| `npm audit` | **0 vulnerabilities** |
| `npm run lint` | **0 errors**, 103 warnings |
| `npx vitest run` | **нестабильно**: ранее 77 passed; повтор — 14 files failed / jsdom `UND_ERR_INVALID_ARG` |
| Playwright / browser E2E | **не запускалось** (нет конфига / нет поднятых серверов) |
| Live 1С / Sber | **запрещено политикой аудита** |
| pip-audit | выполнен на этапе security (OK) |

### Что не удалось проверить и почему

1. Живой UI checkout в браузере — backend/frontend не были запущены в terminals.  
2. Реальная 1С (folders/products/registrate/orders) — нужен тестовый контур и явное разрешение.  
3. Реальный Sber staging payment + callback URL — нужны учётные данные и token.  
4. Онлайн-касса — нет провайдера.  
5. Postgres race tests — нет `RINGOO_TEST_POSTGRES`.  
6. Полный стабильный vitest — окружение jsdom/undici.

---

## H. Блокеры / условия перед тестовым сервером

**Не блокируют выкладку кода на изолированный staging, но блокируют «полноценную проверку интеграции с 1С»:**

1. Заполнить `Store.onec_warehouse_id` для всех магазинов, участвующих в продаже (Django Admin).  
2. Выставить env: `ONE_C_API_*`, флаги sync **только** на тестовую базу 1С; не слать в бой.  
3. Sber: test merchant + `SBER_ECOM_CALLBACK_TOKEN` + HTTPS callback URL (`docs/integrations/SBER_CALLBACK_STAGING.md`).  
4. `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_API_V1_URL` на staging **не** localhost (клиент уже защищает Vercel fallback на `/api/v1`).  
5. CORS/CSRF/ALLOWED_HOSTS/SESSION cookie domain под домены staging.  
6. Celery + Redis/broker на staging для sync заказов.  
7. Явное решение по онлайн-кассе (или принять, что чеки на этапе 1С-интеграции не проверяются).  
8. Smoke-чеклист вручную: каталог → корзина → checkout → заказ cash/pickup → online pay test → статусы.

**Блокеры production (не staging):** фискализация, живой Sber+1С UAT, owner security checklist (`docs/SECURITY_OWNER_CHECKLIST.md`).

---

## I. План дальнейших действий

1. **Сейчас (без commit, по желанию владельца):** review diff фикса `orders/services` + users test.  
2. **Перед staging deploy:** env checklist (п. H), данные магазинов/складов, staff-аккаунт.  
3. **На staging:** ручной smoke UI; включить 1С **read** (каталог) → затем controlled order sync на тестовую ИБ.  
4. **Код (следующий спринт):** Admin API/UI для `onec_warehouse_id`; фильтр `is_warehouse`; стабилизация vitest; расширить CI `pytest apps tests`; blog/news detail или скрыть маршруты; промокоды на checkout или явно «не в MVP».  
5. **Фискализация:** выбрать схему (Сбер orderBundle vs отдельная касса) — сейчас блокер чеков, не блокер staging сайта.  
6. **Postgres concurrency:** прогнать `tests/test_concurrency_postgres.py` на staging-like DB.

---

## J. Финальный вердикт

### **READY FOR STAGING**

Можно разворачивать на **изолированный тестовый сервер** и начинать проверку интеграции с 1С **при соблюдении условий раздела H**.

Не объявляется готовым к production: нет живой проверки 1С/Sber, нет онлайн-кассы, нет E2E UI, security owner checklist и Postgres races ещё на стороне владельца.

Альтернативные уровни **не** выбраны:
- BLOCKED — нет незакрытых P0 в коде магазина после фикса services.  
- READY FOR LOCAL TESTING only — избыточно: backend suite и build уже зелёные.  
- READY FOR PRODUCTION REVIEW — рано.

---

## Приложение: что проверено / исправлено / осталось (для владельца)

| | |
|--|--|
| **Реально проверено** | Архитектура и маршруты; FE↔BE контракты критического пути; 201 backend-тестов (заказы/магазины/оплата/1С-моки/IDOR); type-check; production build; npm audit 0; security-отчёт учтён |
| **Исправлено** | Пакет `apps.orders.services` (anonymize/cancel); фикстура Category в JWT-тестах |
| **Осталось неисправным / неполным** | Admin без warehouse fields; `is_warehouse` filter; placeholders blog/news; fiscal; flaky vitest; нет E2E |
| **Не удалось** | Browser smoke; live 1С/Sber; Postgres races |
| **Можно staging?** | **Да**, с условиями H |
| **Дальше от вас** | Доступы staging + тестовая 1С + Sber test + заполненные `onec_warehouse_id`; разрешение на commit фикса services; разрешение на POST в тестовую 1С |
