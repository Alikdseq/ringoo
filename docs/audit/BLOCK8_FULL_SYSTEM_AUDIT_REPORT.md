# BLOCK 8 — полный системный аудит и готовность к запуску Ringoo

**Дата:** 2026-11-14  
**Среда:** локальный репозиторий `C:\ringoo`  
**Production:** не затрагивался (нет APPLY / migrate / restart / платежей / правок `.env`)  
**Режим:** READ-ONLY аудит + прогон безопасных локальных проверок. **Исправления дефектов не выполнялись** (Этап H — после подтверждения).

---

## 1. Состояние Git

| Параметр | Значение |
|---|---|
| Ветка | `main` (tracks `origin/main`) |
| HEAD | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` — *fix: align staff access cache shape for AdminGuard* |
| Незакоммиченные изменения | Да: ~37 modified + untracked (BLOCK 1–7 код, тесты, отчёты, миграции 0008–0009, warehouse map) |
| Коммит в этой сессии | Нет (по ограничению) |

**Содержимое рабочей копии (ключевое, без секретов):**

- Backend: `integrations/onec/*` (importer, catalog_sync, reporting, warehouse_map), `stores/stock_ops.py`, lifecycle Product, cart/orders transitions, admin Stock/Product guards.
- Migrations (untracked): `stores/0008_map_confirmed_onec_warehouses.py`, `stores/0009_stock_product_protect.py`.
- Frontend: StoreSelector / ProductCard / ProductPage / StoresContent — учёт `is_warehouse` UI-only.
- Docs: `docs/audit/BLOCK2`…`BLOCK7`, `RINGOO_ONEC_FULL_TECHNICAL_AUDIT.md`, `docs/integrations/onec_warehouse_mapping.json`.

**Вывод:** функциональность BLOCK 1–7 присутствует локально, но **не зафиксирована отдельным release-коммитом**. Production на `/opt/ringo` этим аудитом не сверялся.

---

## 2. Архитектурная карта

```
Browser (Next.js App Router)
  ├─ публичные: /, /catalog, /products/[slug], /stores, /cart, /checkout
  ├─ auth: /login, /register, /forgot-password, /reset-password
  ├─ заказы: /orders, /orders/[id], /orders/[id]/success, /orders/success,
  │          /orders/[id]/payment/{return|fail}, /order-status
  └─ admin SPA: /admin/* (client AdminGuard + staff-access API)

Next.js  ──HTTP──►  Django/DRF  /api/v1/
  │                   ├─ auth/          JWT access+refresh (+ HttpOnly cookies)
  │                   ├─ products/      каталог, категории, поиск
  │                   ├─ stores/        магазины + stock
  │                   ├─ cart/          сессия/юзер, серии, available
  │                   ├─ orders/        create/detail/cancel/track/guest-access
  │                   ├─ payments/      YooKassa create/status/webhook
  │                   ├─ admin/         RBAC staff groups
  │                   ├─ integrations/  1С inbound + catalog dry-run/apply
  │                   └─ returns/, content/, promocodes/, crm/, wishlist/, legal/
  │
  ├─ PostgreSQL (prod) / SQLite или test DB (локальные тесты)
  ├─ Redis (кэш, idempotency, Redis-lock 1С)
  └─ Celery / Beat (sync, expire payments, 1С enqueue)
```

**Ключевые точки входа**

| Слой | Путь |
|---|---|
| Django root | `backend/config/urls.py` → `/api/v1/`, `/health/`, admin |
| API v1 | `backend/config/api_urls.py` |
| 1С import | `integrations/onec/importer.py`, `catalog_sync.py`, CLI `import_onec_catalog` |
| Склады | `docs/integrations/onec_warehouse_mapping.json` + `warehouse_map.py` (9 confirmed, «Склад» `is_warehouse=true`) |
| Остатки | `apps/stores/stock_ops.py` (upsert, reserved, batch) |
| Заказы FSM | `apps/orders/services/transitions.py` — `closed` + `closure_result` |
| Оплата | `apps/payments/yookassa_service.py` |
| FE API | `frontend/src/lib/api/services/*`, client `lib/api/client.ts` |

**Карта 9 складов (confirmed):** Ардон, БАМ, Беслан, Ватутина, Доватора, Кирова, Коста 199, Коста 288, **Склад** (`tech-sklad`, `is_warehouse: true`, активная точка продаж — UI-флаг, не исключение из availability).

---

## 3. Результаты backend-аудита

### 3.1 Пользователи и авторизация

| Тема | Оценка |
|---|---|
| Регистрация / логин / JWT | Реализованы; cookie-режим и Bearer |
| Refresh | Cookie path OK; Bearer path дефектен (см. B8-002) |
| Password reset | Есть FE pages + throttles |
| Роли / admin | Staff groups + OTP settings; admin API отделён от публичного |
| IDOR заказов | `OrderDetailView` — `IsAuthenticated` + filter `user=request.user` (без staff-bypass) |
| Guest | `guest_access_token` (SEC-006), track/cancel с токеном |

### 3.2 Каталог

Активность / архивирование (BLOCK 5 lifecycle), фильтры (`catalog_filters.py`), изображения, публичные serializers — по коду и тестам BLOCK 5/6/guards выглядят согласованными. N+1 бюджет каталога закрыт в BLOCK 6 (локальные query-budget тесты).

### 3.3 Магазины и остатки

- 9 складов по `onec_warehouse_id`; unknown warehouse → APPLY blocker.
- `available_quantity` / `reserved_quantity`; защита отрицательных и reserved>qty — BLOCK 3–5.
- «Склад» не исключается из публичных остатков (подтверждено отчётами BLOCK 2–5 + FE StoreSelector).
- Full-snapshot zero отсутствующих позиций — BLOCK 2; идемпотентность ledger — BLOCK 1.

### 3.4 Корзина и заказы

- Серии / агрегирование / cart qty — BLOCK 3 (тесты зелёные).
- FSM v2: отмена → `status=closed`, `closure_result=cancelled`; completed → `closed`+`completed`.
- Release резерва идемпотентен (сервисный слой); Redis-lock на sync — BLOCK 4.
- **Регрессия тестов:** 13 старых тестов всё ещё ожидают `status == 'cancelled'` → ложный FAIL (см. B8-010). Логика отмены по коду переведена на FSM v2.

### 3.5 Оплата (без реальных платежей)

- Создание платежа, idempotence_key, webhook → сверка с API ЮKassa (webhook не proof).
- Expire unpaid / refund paths покрыты тестами, но часть падает из‑за assert на legacy status (B8-010).
- Способы: cash / card-on-delivery / online — в модели заказа.
- Реальные callback/prod PSP — **не проверялись**.

### 3.6 Администрирование

- Stock/Product: readonly/protect/archive (BLOCK 5) — локальные тесты зелёные.
- RBAC через staff-access; обход через публичные endpoints для чужих заказов закрыт (SEC-001).
- FE AdminGuard только client-side — опора на API permissions (B8-009).

### 3.7 Интеграция 1С (BLOCK 1–7)

Локальный регресс **89 passed** на:

`test_onec_stock_idempotency`, `test_onec_stock_reconciliation`, `test_onec_block3_series_cart`, `test_onec_block4_orders_locks`, `test_onec_block5_security_integrity`, `test_onec_block6_performance`, `test_onec_block7_reporting_guards`.

| Механизм | Статус по коду/тестам |
|---|---|
| Idempotency key + failed ledger retry | OK |
| Full snapshot + zero missing | OK |
| Unknown warehouse / unknown products / series | OK (blockers) |
| Preserve reserved | OK |
| Batch upsert + atomic snapshot | OK (не дробить) |
| Redis-lock | OK |
| DRY-RUN / APPLY blockers | OK |
| SyncLog planned vs applied + issue classes | OK (BLOCK 7) |
| Production APPLY | **Не выполнялся** |

Ошибка после начала APPLY должна откатывать транзакцию целиком (atomic) — покрыто тестами BLOCK 4/6; mid-apply partial snapshot на prod не проверялся.

---

## 4. Результаты frontend-аудита

### 4.1 Маршруты

~61 `page.tsx`: публичные, ЛК, корзина, checkout, заказы, payment return/fail, admin, docs, 404 через Next. Отдельная страница `/orders/success?order_number=` существует, но **checkout на неё не ведёт**.

### 4.2 API-интеграция

- Сервисы в `frontend/src/lib/api/services` соответствуют `/api/v1/...`.
- `getOrder` → `GET /orders/{id}/` (только auth) — ломает guest success.
- Guest token stash в sessionStorage для pay return — хрупко при очистке/другом браузере.
- `tsc --noEmit` — OK; `npm run build` — OK; ESLint — 0 errors / 120 warnings.

### 4.3 Интерактивность (по коду)

| Проблема | Где |
|---|---|
| Guest cash/COD success → ошибка загрузки | Critical B8-001 |
| «Купить в 1 клик» — заглушка (кнопка только закрывает modal) | High B8-008 |
| Cart «Применить» promo без обработчика | Medium B8-011 |
| Dead «Связаться с поддержкой» | Medium B8-014 |
| Admin detail: риск вечного loading при 404 | High B8-007 |

### 4.4 Адаптивность

Визуальный прогон 360/390/768/1024/1440 **не выполнялся** в этом BLOCK. По коду: intentional `overflow-x-auto` в admin-таблицах; mobile bottom bar на PDP. **Непроверенный риск** — см. §9.

---

## 5. Результаты безопасности

| Область | Наблюдение | Severity |
|---|---|---|
| DEBUG / ALLOWED_HOSTS | `production.py` fail-closed | PASS (код) |
| CORS / CSRF | Prod запрещает `CORS_ALLOW_ALL`; CSRF trusted origins обязательны | PASS (код) |
| HTTPS cookies / HSTS | Prod defaults secure | PASS (код) |
| JWT cookies | Предпочтительный prod-режим | PASS |
| Bearer refresh + `X-Auth-Cookies: 1` всегда | `client.ts:101` → strip tokens | High/Critical вне cookie-режима (B8-002) |
| Order IDOR | Owner filter | PASS |
| Guest PII | guest_token required (SEC-006) | PASS |
| Rate limiting | Scoped throttles auth/orders/payments/webhook | PASS |
| File upload | Не deep-тестировалось | Risk |
| Secrets в git | `.env` не коммитился в этой сессии; значения не читались | PASS (процедура) |
| SQL / XSS | ORM + React; отдельный pentest не делался | Risk |
| Docker prod compose | `config --quiet` требует env (`DATABASE_URL` и др.) — ожидаемо без `.env` | Info |
| Default `docker compose config` | Успешно | PASS |

Destructive / production probes — **не проводились**.

---

## 6. Результаты производительности

Сохраняются ограничения BLOCK 6 (не экстраполировать):

| Утверждение | Статус |
|---|---|
| Catalog/detail query budget (SQLite/test) | Покрыто тестами BLOCK 6 |
| Batch upsert vs row-by-row | Покрыто |
| Postgres EXPLAIN / 50k–100k APPLY | **Не подтверждено** |
| XML DOM parser | Риск на больших снимках |
| Concurrent import + orders load | **Не проверено** |
| Locust / prod-like load | **Не проверено** |

---

## 7. Результаты полного тестирования

| Проверка | Результат |
|---|---|
| `pytest` полный suite | **13 failed, 432 passed, 8 skipped** (~62–67 s) |
| BLOCK 1–7 OneC subset | **89 passed** |
| `manage.py check` (test settings) | OK, 0 issues |
| `makemigrations --check --dry-run` | No changes detected |
| Frontend ESLint | 0 errors, 120 warnings |
| `tsc --noEmit` | OK |
| `npm run build` | OK (exit 0) |
| `docker compose config` | OK |
| `docker compose -f docker-compose.prod.yml config` | FAIL без env (без значений секретов) |
| Production APPLY / migrate / real YooKassa / live 1С | **Не выполнялось** |

**Корневая причина 13 FAIL (подтверждено traceback):**

```
AssertionError: 'closed' != 'cancelled'
```

Пример: `tests/test_sec003_cancel_releases_stock.py:102` — тест ждёт `Order.STATUS_CANCELLED`, сервис пишет FSM v2 `closed` + `closure_result=cancelled`. Затронуты refund/expire/cancel/guest-cancel suites. Это **долг тестов**, а не доказанный runtime-баг отмены (release path в сервисе сохранён).

---

## 8. Таблица дефектов

| ID | Область | Файл / строка | Описание | Воспроизведение | Влияние | Severity | Доказательство | Рекомендуемое исправление | Внешний спец. |
|---|---|---|---|---|---|---|---|---|---|
| B8-001 | FE orders | `checkout/page.tsx:271`; `orders/[id]/success/page.tsx:97-99`; BE `orders/views.py:363` | Guest cash/COD после checkout → success вызывает `getOrder` (IsAuthenticated) → ошибка | Гость: checkout cash/COD → `/orders/{id}/success` | Гость не видит подтверждение заказа | **Critical** | Анализ кода | Redirect на `/orders/success?order_number=` или track+guest_token; не звать auth-only getOrder | Нет |
| B8-002 | FE auth | `lib/api/client.ts:94-101` ↔ `jwt_cookies.py:14-24` | Refresh axios всегда шлёт `X-Auth-Cookies: 1`; в Bearer-режиме JSON без access/refresh | `NEXT_PUBLIC_USE_AUTH_COOKIES=0`, дождаться 401→refresh | Logout / потеря сессии | **Critical** (Bearer) / **Low** (cookie prod) | Анализ кода | Не слать header в Bearer-режиме | Нет |
| B8-003 | FE orders | `orders/[id]/success/page.tsx` params props | Client page берёт `params` из props; siblings используют `useParams` (Next 15/16) | Открыть success под актуальным Next | Возможен пустой `id` у всех | **High** | Анализ | `useParams()` | Нет |
| B8-004 | FE checkout | `checkout/page.tsx` | Новый idempotency key на каждый submit | Двойной клик | Риск дублей заказов при гонке | **High** | Анализ | Стабильный key на попытку + disable submit | Нет |
| B8-005 | FE payments | `payments.service.ts`, return/fail | Guest pay зависит от sessionStorage guest_token | Новый браузер / очистка stash | 403 на status/retry | **High** | Анализ | Persist + recover flow уже есть — связать UI | Нет |
| B8-006 | FE auth | `client.ts` / `auth-mode.ts` | Неуспешный cookie refresh не всегда чистит session hint | Просроченная cookie-сессия | UI «как будто вошёл» | **High** | Анализ | Clear hint/flag на fail refresh | Нет |
| B8-007 | FE admin | `admin/products|users|returns/[id]` | Слабая обработка API 404 → длительный loading/`!data` | Битый deep-link | Спиннер без ошибки | **High** | Анализ | Явный `isError` → сообщение / notFound | Нет |
| B8-008 | FE PDP | `ProductPageClient.tsx:355-366` | «Купить в 1 клик» — stub | Клик → «Отправить» | Ложное ожидание заказа | **High** | Код («заглушка») | Скрыть или реализовать API | Нет |
| B8-009 | FE admin | `AdminGuard.tsx` | Guard только client; нет middleware RBAC | Прямой URL /admin/* | UI мелькает; API должен резать | **High** | Анализ | Ок если API enforce; усилить UX | Нет |
| B8-020 | FE admin auth | `auth.service.ts` `login()`, `admin/login/page.tsx` | `setAuthSessionHint` до завершения MFA | Admin login с MFA | UI может выглядеть авторизованным до MFA | **High** | Анализ ([Frontend BLOCK 8 audit](c524e3f5-9226-46c4-a507-24ab8079162d)) | Ставить hint только после успешного MFA / staff-access | Нет |
| B8-010 | BE tests | `test_sec003_*`, refund/expire/cancel suites | 13 тестов ждут legacy `cancelled` | `pytest` | Ложная красная полоса CI | **Medium** | Тест FAIL | Assert `is_cancelled()` / `closed`+`closure_result` | Нет |
| B8-011 | FE cart | `cart/page.tsx` | Кнопка промо без onClick/API | Клик «Применить» | Ничего не происходит | **Medium** | Анализ FE | Подключить promocodes API или скрыть | Нет |
| B8-012 | FE checkout | `checkout/page.tsx` | Ошибка загрузки корзины ≡ empty | API cart down | Неверный empty state | **Medium** | Анализ | Разделить error / empty | Нет |
| B8-013 | FE orders | `orders/[id]/page.tsx` | 404 как generic error; dead support CTA | Чужой/несуществующий id | Плохой UX | **Medium** | Анализ | notFound + рабочая ссылка | Нет |
| B8-014 | FE auth | `useAuth.ts` | Logout без invalidate cart; stale localStorage hint | Logout | Устаревшая корзина в UI | **Medium** | Анализ | Invalidate cart keys | Нет |
| B8-015 | Docs | `docs/API.md` vs FE | Drift `/categories/` vs `/products/categories/` | Чтение docs | Путаница интеграторов | **Low** | Анализ | Синхронизировать docs | Нет |
| B8-016 | FE SEO | `sitemap.ts` vs `site-map/page.tsx` | Расхождение списков маршрутов | Сравнение страниц | SEO/навигация | **Low** | Анализ | Выровнять | Нет |
| B8-017 | Ops | Uncommitted BLOCK1–7 | Локальные фиксы не в HEAD remote | Deploy с origin/main | Prod без BLOCK1–7 | **High** (release) | Git status | Controlled commit + deploy plan | Ops |
| B8-018 | Perf | BLOCK 6 leftovers | Нет Postgres 50k/100k / concurrent load | — | Риск деградации sync | **Medium** (risk) | BLOCK6 report | Нагрузочный стенд | Ops/1С |
| B8-019 | Responsive | — | Нет визуальной проверки брейкпоинтов | — | Возможен horizontal scroll | **Medium** (unverified) | Не проверено | Ручной/Browser QA | QA |

---

## 9. Непроверенные риски

1. Production parity: `/opt/ringo` vs локальная working tree (миграции 0008–0009, importer).
2. Реальный APPLY полного снимка 1С и время транзакции на Postgres.
3. Конкуренция Celery import ↔ оформление заказов под нагрузкой.
4. End-to-end ЮKassa (sandbox/live) success/fail/duplicate webhook.
5. Визуальная адаптивность 360–1440 и a11y.
6. Полный pentest (XSS stored, upload malware, IDOR fuzz).
7. Поведение при недоступном Redis (lock/idempotency fallback).
8. Compose prod интерполяция — только при заполненном env (значения не проверялись).

---

## 10. Список блокеров запуска

**Блокирующие пользовательский запуск (must-fix до публичного soft-launch):**

1. **B8-001** — страница успеха для гостевого cash/COD сломана.
2. **B8-017** — незакоммиченный/незадеплоенный объём BLOCK 1–7 (иначе prod без сверки остатков/серий/lock/reporting).

**Условно блокирующие (зависят от режима деплоя):**

3. **B8-002** — если staging/prod без cookie-auth (`USE_AUTH_COOKIES=0`).
4. **B8-004 / B8-005** — двойной submit и потеря guest pay token ухудшают оплату.

**Не блокируют код, но блокируют доверие CI:**

5. **B8-010** — 13 красных тестов FSM v2 (починить до merge).

**Не блокеры продукта, но важны:** B8-008 (1-click stub), B8-011 (promo dead), B8-007 (admin 404 UX), B8-018/019 (нагрузка/адаптив).

---

## 11. Общая оценка готовности Ringoo

| Контур | Оценка |
|---|---|
| 1С sync (локально, BLOCK 1–7) | **Готов к controlled dry-run**; APPLY на prod — только по отдельному плану |
| Каталог / магазины / остатки (код) | Высокая |
| Корзина / резервы / FSM заказов (код) | Высокая; тесты частично устарели |
| Оплата | Код выглядит зрелым; E2E PSP не подтверждён |
| Guest checkout UX | **Не готов** (B8-001) |
| Admin | Приемлемо при опоре на API RBAC |
| CI / suite | **Не зелёный** (13 fails) |
| Release hygiene | Working tree ≠ tagged release |

**Вердикт:** Ringoo **не готов к полноценному публичному запуску** в текущем состоянии working tree без устранения B8-001 и контролируемого выката BLOCK 1–7.  
Для **ограниченного internal soft-launch** (только авторизованные покупатели + cookie-auth + без опоры на guest cash success) — возможна условная готовность после фикса тестов и deploy-плана, но это **не** рекомендация к открытию гостевого checkout.

---

## 12. Рекомендуемый следующий этап

**Этап не начинается без вашего подтверждения.**

Предлагаемый порядок исправлений (по одному согласованному блоку):

1. **Fix-pack A — Guest success (B8-001 + B8-003)**  
   Redirect / guest-safe success; `useParams`; тест на guest cash path.
2. **Fix-pack B — Тесты FSM v2 (B8-010)**  
   Обновить 13 asserts → `is_cancelled()` / `closure_result`; полный pytest зелёный.
3. **Fix-pack C — Auth refresh / session hint (B8-002 + B8-006 + B8-020)**  
   Header только в cookie-mode; очистка hint; hint после MFA, не до.
4. **Fix-pack D — Checkout/pay hardening (B8-004, B8-005)**  
   Stable idempotency key; guest token UX.
5. **Fix-pack E — Dead UI (B8-008, B8-011, B8-007, …)**  
   Скрыть stub или реализовать; promo; admin 404.
6. **Release** — отдельное разрешение на commit / PR / deploy; prod APPLY 1С — отдельный runbook.

После каждого pack: точечные тесты + регресс BLOCK 1–7 subset + список изменённых файлов + влияние на BLOCK 1–7.

---

## Приложение A. Что сознательно не делалось

- Правки кода/конфигов/`.env`
- Production SSH / APPLY / migrate / restart
- Реальные платежи
- Коммиты
- Выдача значений секретов

## Приложение B. Сводка прогона

```
pytest (full):     13 failed, 432 passed, 8 skipped
pytest (1C B1–7):  89 passed
django check:      OK
makemigrations:    No changes detected
eslint:            0 errors, 120 warnings
tsc:               OK
next build:        OK
compose (default): OK
compose (prod):    needs env (expected)
```

---

**BLOCK 8 (аудит + отчёт) завершён.**  
Исправления — только после вашего подтверждения по выбранному fix-pack.
