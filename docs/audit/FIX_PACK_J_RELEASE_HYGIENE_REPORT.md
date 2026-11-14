# FIX-PACK J — B8-017: Git Release Hygiene и подготовка релиза

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Режим:** READ-ONLY аудит + план (без commit / push / deploy / migrate / APPLY / production)  
**`.env` / секреты:** не читались  

---

## 1. Актуальный Git snapshot

| Поле | Значение |
|---|---|
| Branch | `main` |
| HEAD | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| HEAD message | `fix: align staff access cache shape for AdminGuard` |
| Working tree | **грязный** — все BLOCK 1–7 + Fix A–I в uncommitted changes |
| Удаления (`D`) | **0** |
| Секреты / `.env` в status | **не найдены** (скан имён) |

### Recent log (`git log -5 --oneline`)

```
b3a9db4 fix: align staff access cache shape for AdminGuard
cedb65c feat: accept order status and store payment updates from 1C
7877b40 fix: unblock SSR over Docker HTTP without disabling HTTPS redirect
94b472e fix: correct Docker healthchecks for production services
ae693c7 chore: bind production config templates to ringoo15.store
```

### Объёмы

| Категория | Количество |
|---|---|
| `git status --short` строк | **133** |
| Tracked modified (`M`) | **73** (+2820 / −846 по `git diff --stat`) |
| Untracked (`??`) | **60** |
| Deleted | **0** |
| Renamed | **0** |

**Вывод:** HEAD совпадает с исходной точкой аудита BLOCK 8. Принятые изменения **сохранены в working tree**, но **не зафиксированы** в git. Случайных удалений нет.

---

## 2. Наличие BLOCK 1–7 и Fix A–I

| Контур | Присутствует | Ключевые артефакты | Примечание |
|---|---|---|---|
| BLOCK 1 — stock idempotency / ledger | Да | `backend/apps/stores/stock_ops.py` (M), `backend/tests/test_onec_stock_idempotency.py` (??) | |
| BLOCK 2 — reconciliation | Да | `backend/tests/test_onec_stock_reconciliation.py`, `docs/audit/BLOCK2_*` | |
| BLOCK 3 — series / cart | Да | `test_onec_block3_series_cart.py`, importer/parser/catalog_sync (M) | |
| BLOCK 4 — orders / locks / tx | Да | `test_onec_block4_orders_locks.py`, `integrations/onec/orders.py` (M) | Redis lock / atomic APPLY |
| BLOCK 5 — security / integrity | Да | `0008_map_confirmed_onec_warehouses.py`, `0009_stock_product_protect.py`, lifecycle, warehouse_map | Миграции **untracked** |
| BLOCK 6 — performance | Да | `test_onec_block6_performance.py`, `BLOCK6_*` report | |
| BLOCK 7 — reporting / guards | Да | `integrations/onec/reporting.py`, `test_onec_block7_reporting_guards.py` | |
| Fix A — guest success / SEC-006 | Да | `orders/[id]/success/*` (M), `test_fix_pack_a_*` (??) | |
| Fix B — order cancellation FSM | Да | `transitions.py` (M), `order_fsm_assertions.py` (??), Fix B report | FSM в `orders/services/transitions.py` |
| Fix C — auth refresh | Да | `client.ts`, `auth-refresh.ts` (??), Fix C report | |
| Fix D — checkout / payment | Да | checkout idempotency helpers (??), payments stash tests, Fix D report | |
| Fix E — UI integrity | Да | cart/checkout/orders/admin detail, promo/1-click removal tests | |
| Fix F — AdminGuard | Да | `AdminGuard.tsx` (M), staff-access tests (??) | |
| Fix G — FSM v2 tests | Да | обновлённые `test_sec003_*` / INT suites (M), Fix G report | |
| Fix H — API docs | Да | `docs/API.md` (M), Fix H report | |
| Fix I — sitemap / SEO | Да | `public-site-routes.ts` (??), sitemap/robots/site-map (M) | |

### Незапланированный / шум в tree

| Путь | Статус | Рекомендация |
|---|---|---|
| `промпт.txt` | M | Не включать в release-коммиты (локальный промпт) |
| `Описание работ.txt` | ?? | Вне scope релиза; согласовать отдельно |
| `docs/*.docx` (4 файла) | ?? | Документы объёма работ — отдельный docs-коммит или исключить |
| `docs/integrations/onec_warehouse_mapping.json` | ?? | Нужен для BLOCK 5 map — **включать** с миграцией 0008 |

---

## 3. Таблица готовности контуров

| Контур | Изменения присутствуют | Зависимости | Риски переноса |
|---|---|---|---|
| Миграции BLOCK 5 (+ PROTECT) | Да (0008, 0009 untracked) | 0008 → `stores.0007`; 0009 → `stores.0008` + `products.0009` | Deploy без migrate сломает PROTECT/map; 0008 data migration зависит от mapping JSON |
| Importer / stock ops | Да | Redis, БД, модели Stock/Series | Неверный APPLY без dry-run; нужен Redis для lock/idempotency |
| Backend API ↔ Frontend | Да | Совместный deploy auth/cart/orders/payments | Частичный FE/BE → 403 guest pay, stale cart, AdminGuard mismatch |
| Celery tasks / Beat | Да (код + schedule в settings) | Redis broker, `ONE_C_CATALOG_SYNC_ENABLED`, worker+beat | Beat без worker / без Redis → silent skip или backlog |
| Redis lock / idempotency | Да | `REDIS_URL` / cache backend | Без Redis checkout claim и 1С lock деградируют |
| FSM + резервации | Да | `transitions.py`, stock release на cancel/expire | Старый FE, ожидающий `cancelled`, уже закрыт Fix B/G на BE/tests |
| YooKassa | Да (Fix D + webhook suites) | `YOOKASSA_*`, webhook URL/IP allowlist | Тестовый режим / неверный return URL → pay fail UX |
| AdminGuard + RBAC | Да (Fix F) | staff-access API shape (уже в HEAD `b3a9db4`) + FE Guard | Старый FE на новый API — уже выровнено в HEAD; новый FE обязателен с этим релизом |
| SEO / docs | Да (H, I) | Публичный API для динамического sitemap | Низкий риск; не блокирует commerce |

---

## 4. Миграции

### Список релевантных (локально на диске)

```
stores:   0007_stockmovement → 0008_map_confirmed_onec_warehouses (NEW)
          → 0009_stock_product_protect (NEW)
products: 0009_block10_state_sync (уже в дереве; зависимость 0009 stores)
orders:   0007_order_onec_sync_fields, 0008_order_checkout_cart_id, 0009_order_guest_access_token
payments / users / products: block10 / onec codes — ранее в истории репо
```

### Порядок зависимостей (критично для release)

1. Убедиться, что на целевой БД уже применены миграции до `stores.0007` и `products.0009`.  
2. Применить **`stores.0008`** (RunPython mapping складов 1С).  
3. Применить **`stores.0009`** (`Stock.product` → `PROTECT`).  
4. Production migrate **не выполнялся** в этом pack (запрещено).

### Проверки (локально)

| Команда | Результат |
|---|---|
| `makemigrations --check --dry-run` | **No changes detected** |
| `manage.py check` | **0 issues** |
| Незапланированные авто-миграции | **Нет** |

---

## 5. Тестовая целостность (воспроизведено в Fix J)

| Проверка | Результат | Примечание |
|---|---|---|
| Backend full suite | **459 passed, 8 skipped** | `test_concurrency_postgres` skipped (нет Postgres в этом прогоне) |
| OneC suites (block3–7 + stock) | **89 passed** | |
| Frontend vitest (ключевые) | **20 passed / 4 files** | public-site-routes, auth-refresh, checkout-idempotency, AdminGuard |
| TypeScript `tsc --noEmit` | **exit 0** | |
| ESLint изменённых FE файлов | **0 errors, 5 warnings** | `react-hooks/set-state-in-effect` (checkout ×4?, useAuth); `--max-warnings 0` → exit 1 |
| `npm run build` | **exit 0** | sitemap.xml / robots / site-map в маршрутах |
| Production VPS / реальная 1С / live payments | **пропущено** | запрещено ТЗ |
| Postgres concurrent suite | **skipped** | внешний Postgres не требовался для green gate |

Код ради зелёного результата **не менялся**.

---

## 6. Предлагаемая структура коммитов (НЕ выполнено)

> Требует отдельного подтверждения перед любым `git add` / `commit`.

| # | Тема коммита | Состав (ориентир) |
|---|---|---|
| 1 | `feat(onec): stock ops, importer guards, warehouse map + migrations` | `integrations/onec/*`, `stores/stock_ops.py`, models/admin/views stores, `0008`+`0009`, `warehouse_map.py`, `lifecycle.py`, mapping JSON, onec tests block1–7 |
| 2 | `feat(orders): FSM v2 transitions, cancel/reserve integrity` | `orders/services/transitions.py`, serializers/views orders, related BE tests + `order_fsm_assertions.py` |
| 3 | `fix(checkout): idempotency claim + guest pay stash (SEC-006)` | BE order idempotency + FE checkout/payments/success (Fix A/D) |
| 4 | `fix(auth): cookie refresh client + logout cart invalidation` | `client.ts`, `auth-refresh*`, `useAuth*`, auth.service (Fix C/E logout) |
| 5 | `fix(admin): AdminGuard + query error UX` | AdminGuard, AdminQueryError, admin pages, staff-access tests (Fix E/F) |
| 6 | `fix(ui): cart/checkout/orders integrity (dead UI removal)` | cart/checkout/orders/product 1-click/promo (Fix E) |
| 7 | `docs(api): sync categories path + audit reports A–J / BLOCK2–8` | `docs/API.md`, `docs/audit/*` |
| 8 | `fix(seo): shared public indexable routes for sitemap` | `public-site-routes*`, sitemap/robots/site-map (Fix I) |

**Исключить из релизных коммитов без явного ОК:** `промпт.txt`, `Описание работ.txt`, бинарные `.docx` (или отдельный chore-коммит).

---

## 7. План релиза (подготовлен, не выполнен)

### 7.1 Pre-flight (требует подтверждения)

1. Согласовать структуру коммитов §6.  
2. Backup БД + media + `.env` **имена/наличие** (значения не копировать в git).  
3. Убедиться, что Redis / Celery worker / beat доступны на стенде.  
4. Проверить имена переменных (без чтения секретов):

**Backend / infra (имена):**  
`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_API_ORIGIN`, `FRONTEND_URL`, `ONEC_INCOMING_TOKEN`, `ONE_C_CATALOG_SYNC_ENABLED`, `YOOKASSA_ENABLED`, `YOOKASSA_TEST_MODE`, `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_RETURN_URL`, `YOOKASSA_WEBHOOK_URL`, `YOOKASSA_WEBHOOK_IP_ALLOWLIST`, `JWT_COOKIE_*`, `ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS`

**Frontend (имена):**  
`NEXT_PUBLIC_API_V1_URL` / `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_USE_AUTH_COOKIES`, `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED`, `NEXT_PUBLIC_JWT_COOKIE_*`

### 7.2 Порядок deploy

1. **Backend** (код + новые миграции) → `migrate` (отдельное подтверждение) → restart API.  
2. **Celery worker + beat** restart (чтобы подхватить sync/lock код).  
3. **Frontend** build/deploy (auth/cart/checkout/AdminGuard/SEO вместе).  
4. Smoke: login/refresh, guest checkout, staff admin, sitemap.xml.  
5. **1С DRY-RUN** только после smoke (отдельный план §7.4).  
6. **1С APPLY** — только после успешного DRY-RUN и явного ОК.

Не деплоить FE без BE (и наоборот) для контуров auth/orders/payments/admin.

### 7.3 Backup и rollback

| Шаг | Действие | Подтверждение |
|---|---|---|
| Backup | DB dump + media snapshot + запись текущего git SHA на сервере | Да |
| App rollback | Вернуть предыдущий image/SHA FE+BE, restart | Да |
| Migration rollback | 0009 reverse относительно безопасно (AlterField); 0008 RunPython имеет `reverse_mapping` — проверить на staging | **Отдельное** подтверждение |
| Data | APPLY 1С не откатывается «кнопкой» — только компенсирующий sync / ручная сверка | Да |
| Payments | Не включать live YooKassa cutover в тот же шаг, что APPLY | Да |

### 7.4 Контролируемый 1С DRY-RUN / APPLY

| Этап | Действие | Подтверждение |
|---|---|---|
| 0 | Убедиться `ONE_C_CATALOG_SYNC_ENABLED` и токен заданы по именам | Ops |
| 1 | Запуск **DRY-RUN** на копии/staging (не prod APPLY) | **Да** |
| 2 | Сверка SyncLog planned vs applied / issue classes (BLOCK 7) | Да |
| 3 | Проверка warehouse map (0008) и series aggregation | Да |
| 4 | Узкий **APPLY** (ограниченный каталог/склад) в maintenance window | **Да (явный)** |
| 5 | Мониторинг lock/Redis, отсутствие mid-apply partial | Да |
| 6 | Полный APPLY — только после узкого успеха | **Да** |

### 7.5 Контрольные проверки после будущего deploy

- [ ] `migrate` status: `stores.0009` applied  
- [ ] Health / Django check  
- [ ] JWT cookie login + refresh (Fix C)  
- [ ] Guest order success без token в URL (Fix A / SEC-006)  
- [ ] Checkout double-submit → один заказ (Fix D)  
- [ ] Cancel → `closed` + reserve release (Fix B)  
- [ ] AdminGuard: 403 vs 5xx vs retry (Fix F)  
- [ ] Cart error ≠ empty; promo UI отсутствует; no 1-click stub (Fix E)  
- [ ] `/sitemap.xml` содержит blog/news hubs; cart/checkout отсутствуют (Fix I)  
- [ ] `docs/API.md` categories path совпадает с FE (Fix H)  
- [ ] Celery beat `onec-catalog-sync` не APPLY’ит без политики  
- [ ] YooKassa webhook test-mode / allowlist  

---

## 8. Действия, требующие отдельного подтверждения

1. Любые `git add` / `git commit` / группировка §6.  
2. `git push` / PR / merge в protected `main`.  
3. Deploy на staging или production.  
4. `migrate` на любой не-local БД (особенно 0008/0009).  
5. Restart Celery/beat/API на VPS.  
6. Изменение/проверка **значений** секретов (имена — OK).  
7. 1С **DRY-RUN** против реальной базы 1С.  
8. 1С **APPLY** (полный или частичный).  
9. Live платежи / отключение `YOOKASSA_TEST_MODE`.  
10. Включение rollback миграций на prod.  
11. Коммит локального шума (`промпт.txt`, docx, `Описание работ.txt`).

---

## 9. Вердикт

| Критерий | Статус |
|---|---|
| Все принятые BLOCK 1–7 сохранены локально | **Да** |
| Все Fix A–I сохранены локально | **Да** |
| Случайные удаления | **Нет** |
| Секреты в diff/untracked | **Не обнаружены** |
| Миграции согласованы / makemigrations clean | **Да** |
| Тесты воспроизводимы (BE + OneC + FE key + tsc + build) | **Да** |
| Готовность к немедленному commit/deploy без согласования | **Нет** — нужен controlled commit plan + ops confirm |
| B8-017 | **Закрыт на уровне hygiene/plan**; исполнение релиза — следующий согласованный шаг |

**Итог:** working tree целостен относительно принятых работ; зависимости и риски понятны; релиз подготовлен документально. Коммиты, push и deploy **не выполнялись**.

---

## 10. Остановка

Fix-pack J завершён отчётом. Дальнейшие git/deploy/1С действия — только по отдельному запросу.
