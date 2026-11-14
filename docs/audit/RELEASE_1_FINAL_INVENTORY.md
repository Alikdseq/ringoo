# RELEASE 1 — Финальная инвентаризация Git и подготовка релиза

**Дата:** 2026-11-14  
**Режим:** READ-ONLY / RELEASE PREPARATION  
**Среда:** локально `C:\ringoo`  
**Git add / commit / push / migrate / production / 1С APPLY / правки кода:** **не выполнялись**

---

## 1. Актуальный Git-срез

| Поле | Значение |
|---|---|
| Branch | `main` |
| HEAD | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| HEAD message | `fix: align staff access cache shape for AdminGuard` |
| Conflicts / unmerged | **нет** |
| Deleted (`D`) | **0** |
| Renamed (`R`) | **0** |
| Tracked modified (`M`) | **76** (+2886 / −868) |
| Untracked (`??`) | **68** |
| `git status --short` строк | **144** |
| `git diff --check` | **2** trailing whitespace в `docs/API.md` (стр. 258–259); остальные — CRLF warnings |

### `git log -5 --oneline`

```
b3a9db4 fix: align staff access cache shape for AdminGuard
cedb65c feat: accept order status and store payment updates from 1C
7877b40 fix: unblock SSR over Docker HTTP without disabling HTTPS redirect
94b472e fix: correct Docker healthchecks for production services
ae693c7 chore: bind production config templates to ringoo15.store
```

### Дельта относительно FIX-PACK J

| Метрика | Fix J | Сейчас |
|---|---:|---:|
| Modified | 73 | **76** |
| Untracked | 60 | **68** |

Новое после J в основном: Fix K/L отчёты и скрипты, responsive (`spacing`/`Footer`/`CartItem`/`checkout` sticky, `responsive-contracts.test.ts`), `frontend/AGENTS.md`.

**Вывод:** HEAD не сдвинулся; весь объём BLOCK 1–7 + Fix A–L по-прежнему **только в working tree**.

---

## 2. Классификация изменений (сводка по контурам)

### 2.1 BLOCK 1–7 / 1С — присутствие ключевых артефактов

| Артефакт | Статус | Обязателен |
|---|---|---|
| `docs/integrations/onec_warehouse_mapping.json` | ?? | **Да** (с stores.0008) |
| `stores/migrations/0008_…`, `0009_…` | ?? | **Да** |
| `products/migrations/0009_block10_state_sync.py` | уже в Git (tracked) | зависимость 0009 stores |
| `stock_ops.py`, `importer.py`, `parser.py`, `catalog_sync.py` | M | **Да** |
| `warehouse_map.py`, `reporting.py`, `lifecycle.py` | ?? | **Да** |
| `integrations/onec/tasks.py` (Celery) | tracked, без локальных правок в status | уже в HEAD |
| OneC test suites block3–7 + stock | ?? | **Да** (качество релиза) |

Признаки потери BLOCK 1–7 **не обнаружены** (ключевые пути на диске, diff присутствует).

### 2.2 Fix Pack A–L — наличие

| Pack | Признаки в tree |
|---|---|
| A guest success | M success pages + ?? FE/BE tests |
| B cancellation / FSM | M `transitions.py` + ?? `order_fsm_assertions` / fix_pack_b tests |
| C auth refresh | M `client.ts` + ?? `auth-refresh.ts` |
| D checkout/payment | M checkout/payments + ?? idempotency/stash |
| E UI integrity | M cart/checkout/orders/admin detail + ?? AdminQueryError |
| F AdminGuard | M AdminGuard + ?? tests |
| G FSM tests | M sec/int tests |
| H API docs | M `docs/API.md` |
| I sitemap | M sitemap/robots + ?? `public-site-routes*` |
| J hygiene | ?? `FIX_PACK_J_…` |
| K load test | ?? report + `b8_018_*.py` scripts |
| L responsive | M spacing/Footer/CartItem/checkout + ?? contracts test + report |

### 2.3 Полный реестр (группы)

Ниже — компактный реестр. Детальный per-file «что изменено» сведён к смыслу diff; полный list = `git status --short`.

#### Backend — обязательный код (A)

| Path | Git | Pack/Block | Include | Deps |
|---|---|---|---|---|
| `integrations/onec/{importer,parser,catalog_sync,orders}.py` | M | B1–7 | Да | stock_ops, warehouse_map |
| `integrations/onec/{warehouse_map,reporting}.py` | ?? | B2/B7 | Да | mapping JSON |
| `apps/stores/stock_ops.py` (+ models/views/serializers/admin/tests) | M | B1–5 | Да | migrations 0008–0009 |
| `apps/stores/migrations/0008_*`, `0009_*` | ?? | B5 | Да | products.0009 |
| `apps/products/services/lifecycle.py` | ?? | B5 | Да | products admin/views |
| `apps/products/{admin,serializers,views,catalog_filters,product_images,import_*,diagnose_*}` | M | B3–6 | Да | lifecycle |
| `apps/orders/{transitions,views,serializers,tests,…}` | M | B4 + Fix B/D | Да | stock_ops, FSM |
| `apps/cart/*` | M | B3 + Fix D/E | Да | orders |
| `apps/admin_api/views/{orders,products,stock}.py` | M | B5–7 / admin | Да | RBAC |
| `apps/users/tests.py` | M | Fix G | Да | — |
| `backend/tests/test_onec_*` + helpers | ?? | B1–7 | Да | onec code |
| `backend/tests/test_fix_pack_*`, `order_fsm_assertions.py` | ?? | A/B/G | Да | transitions |
| `backend/tests/test_sec*`, `test_int*`, payment suites (M) | M | B/D/G | Да | FSM/idempotency |

#### Frontend — обязательный код (A)

| Path | Git | Pack | Include |
|---|---|---|---|
| guest success / payment return-fail / payments.service | M + ?? tests | A/D | Да |
| `client.ts`, `auth-refresh*`, `auth.service`, `auth-mode`, `useAuth*` | M/?? | C/E | Да |
| `checkout*`, `checkout-idempotency*`, `checkout-success-path*` | M/?? | D/L | Да |
| cart / ProductPageClient / ProductCard / StoreSelector | M | E/L | Да |
| AdminGuard*, AdminQueryError*, admin detail pages, admin login | M/?? | E/F | Да |
| `public-site-routes*`, sitemap, robots, site-map | M/?? | I | Да |
| `spacing.ts`, `Footer.tsx`, `CartItem.tsx` | M | L | Да |
| `responsive-contracts.test.ts` + UI state tests | ?? | E/F/L | Да (тесты) |
| `types/api.ts`, `errors*` | M/?? | C/E | Да |

#### Документация (B)

Все `docs/audit/BLOCK2–8_*.md`, `FIX_PACK_A–L_*.md`, `RINGOO_ONEC_FULL_TECHNICAL_AUDIT.md`, `docs/API.md` (M) — включать в docs-коммит(ы).

#### Вспомогательные (C)

| Path | Рекомендация |
|---|---|
| `backend/scripts/b8_018_load_benchmark.py` | Опционально: полезен для повтора B8-018; можно в docs/tools commit |
| `backend/scripts/b8_018_rerun_dryrun.py`, `b8_018_zero_smoke.py` | Опционально / или исключить как одноразовые |
| `backend/var/b8_018_results.json` + fixtures | **Не в Git** — игнорируется `var/` (проверено `git check-ignore`) |
| `frontend/AGENTS.md` | Опционально (локальные AI-инструкции FE) |

#### Не включать (D)

| Path | Причина |
|---|---|
| `промпт.txt` (M) | Локальный промпт оператора |
| `Описание работ.txt` (??) | Внешний объём работ, не код |
| `docs/*.docx` (4 шт.) | Бинарные коммерческие/объёмные документы — только по явному ОК; не блокируют runtime |

---

## 3. Категории A / B / C / D (итог)

### A. Обязательные файлы релиза

- Весь backend M/?? по 1С, stores, products lifecycle, orders/cart/admin_api, связанные tests.  
- Миграции stores 0008–0009 + `onec_warehouse_mapping.json`.  
- Весь frontend M/?? по auth/cart/checkout/orders/admin/SEO/responsive (кроме опциональных).  
- FE/BE тесты Fix A–G/I/L.

### B. Документация релиза

- `docs/API.md`  
- `docs/audit/*` BLOCK2–8 + FIX_PACK_A–L + RINGOO_ONEC audit  

### C. Вспомогательные

- `backend/scripts/b8_018_*` — по желанию  
- `frontend/AGENTS.md` — по желанию  
- `backend/var/*` — **не коммитить** (уже ignore)

### D. Не включать

- `промпт.txt`, `Описание работ.txt`, четыре `.docx` (пока нет явного «включить»)

---

## 4. Безопасность перед коммитом

### Имена файлов

`.env` / credentials / `.pem` / `id_rsa` среди status/untracked: **не найдены**.

### Скан содержимого (значения замаскированы)

Совпадения `password=` / `SECRET_KEY=` в **тестах** и поле `password` в `auth.service.ts` — **ложные срабатывания** (фикстуры Django/`set_password`, API-поля). Риск: **Low / false positive**.

Реальных API keys / JWT / connection strings с паролями / private keys в diff **не выявлено**.

### `.gitignore`

Покрывает: `.env*`, `venv`, `node_modules`, `.next`, `db.sqlite3`, `var/`, `htmlcov/`, логи, media/static.  
`backend/var/b8_018_*` корректно игнорируется корневым `var/`.  
`.docx` / `промпт.txt` **не** игнорируются — нужна ручная дисциплина exclude (раздел D).  
**`.gitignore` не изменялся.**

---

## 5. Миграции Django

### Статический граф (по файлам)

```
products.0008 → products.0009_block10_state_sync   [уже в Git]
stores.0007_stockmovement → stores.0008_map_confirmed_onec_warehouses  [NEW ??]
stores.0008 + products.0009 → stores.0009_stock_product_protect        [NEW ??]
```

Циклов в просмотренном графе stores/products **нет**.  
Порядок apply: убедиться что на цели есть ≥ `stores.0007` и `products.0009`, затем `stores.0008`, затем `stores.0009`.

### Команды

| Команда | Результат |
|---|---|
| `makemigrations --check --dry-run` (default manage.py → development) | **No changes detected** |
| `manage.py check` | **0 issues** |
| `showmigrations` под `config.settings.test` | **неинформативно**: `MIGRATION_MODULES = DisableMigrations()` |
| `showmigrations` под base/без БД | нет ENGINE / recorder — prod DB **не трогали** |

**Риск:** 0008 — data migration (RunPython) зависит от корректности mapping JSON и уже существующих Store rows. Не применять на prod без backup и подтверждения.

---

## 6. Актуальность тестов

| Результат | Источник | Актуален к текущему tree? |
|---|---|---|
| Backend 459 passed / 8 skipped | Fix J (до K/L UI/scripts) | **Частично устарел** — после J добавлены Fix L FE + K scripts; BE OneC ядро не переписывалось ради L |
| OneC 89 passed | Fix J / K context | Вероятно актуален для BE OneC; полный suite после L **не перегонялся** |
| Vitest 20 / later 18 contracts | I / L | L contracts зелёные; полный FE suite после всех packs — **точечно**, не полный |
| tsc / Next build | Fix L | **OK** на состоянии с responsive fixes |
| ESLint | Fix L | 0 errors; warnings `set-state-in-effect` в checkout (известные) |
| Django check / makemigrations check | этот отчёт | **OK** |

### Ограничения (не считать пройденными)

- PostgreSQL concurrency  
- Redis lock end-to-end в Django cache settings (prod)  
- Production 1С APPLY / DRY-RUN  
- Полный checkout → payment → order на живом backend  
- Полноценный Playwright responsive suite  

---

## 7. Предлагаемый план коммитов (НЕ выполнен)

> Требует вашего подтверждения состава файлов перед любым `git add`.

| # | Предлагаемое сообщение | Файлы (ориентир) | Почему вместе | Зависит от |
|---|---|---|---|---|
| 1 | `feat(onec): warehouse map, stock batch/snapshot guards, stores 0008–0009` | onec importer/parser/catalog_sync/orders/reporting/warehouse_map; stores stock_ops/models/…; products lifecycle + related; mapping JSON; migrations 0008/0009; onec tests + onec_test_utils | Атомарный контур 1С+остатки+миграции | — |
| 2 | `feat(orders): FSM v2 transitions and cancel/reserve integrity` | orders transitions/services/views/serializers/tests; related INT/SEC cancel tests; order_fsm_assertions; fix_pack_b tests | FSM отдельно от 1С импорта | желательно после 1 (stock) |
| 3 | `fix(checkout): idempotency, guest success, pay stash (SEC-006)` | orders/cart BE idempotency bits; FE checkout/success/payments + helpers/tests | Commerce path | 2 |
| 4 | `fix(auth): cookie refresh client and logout cart invalidation` | client, auth-refresh, auth.service, auth-mode, useAuth + tests | Auth контур | — / parallel after 1 |
| 5 | `fix(admin): AdminGuard, query error UX, staff access handling` | AdminGuard*, AdminQueryError*, admin pages, staff-access tests | Admin UX | 4 полезен |
| 6 | `fix(ui): cart/checkout/orders integrity and mobile responsive` | cart/PDP/ProductCard/StoreSelector/Footer/spacing/checkout sticky + related tests | Storefront UX + B8-019 | 3 |
| 7 | `fix(seo): shared public routes for sitemap/robots/site-map` | public-site-routes*, sitemap, robots, site-map | SEO | — |
| 8 | `docs: API sync and audit reports BLOCK2–8 / Fix A–L` | docs/API.md, docs/audit/*.md | Документация | после кода |
| 9 *(optional)* | `chore: add OneC load benchmark scripts` | `backend/scripts/b8_018_*` | Не runtime | 1 |
| 10 *(optional)* | `docs: add commercial scope docx / AGENTS` | docx, frontend/AGENTS.md | Только по ACK | — |

**Исключить из всех коммитов:** `промпт.txt`, `Описание работ.txt` (и docx без ACK).

Альтернатива: объединить 4+5 или 6+7 при желании меньшего числа коммитов — допустимо, если история важнее атомарности SEO.

Один mega-commit **не рекомендуется**: миграции 1С и FE auth/checkout смешивают rollback и review.

---

## 8. Порядок следующих этапов (только план)

1. Завершить инвентаризацию — **этот отчёт**.  
2. **Ваше подтверждение** состава A/B/C/D и плана коммитов.  
3. `git add` + commits по утверждённым группам.  
4. Проверить `git log` / чистое дерево (кроме намеренных excludes).  
5. Отдельное разрешение на **push**.  
6. Push в remote.  
7. Подготовка сервера.  
8. Backup БД/файлов.  
9. Сверка prod SHA и миграций.  
10. Deploy после отдельного разрешения.  
11. Smoke-тесты.  
12. 1С **DRY-RUN** отдельно.  
13. 1С **APPLY** — только после отдельного разрешения.

**Сейчас шаги 3–13 не выполнялись.**

---

## 9. Блокеры и риски

### Блокеры к коммитам

| # | Статус |
|---|---|
| Секреты в tree | Не найдены |
| Потеря BLOCK 1–7 | Не обнаружена |
| Миграции без файла / цикл | Не обнаружено (static graph) |
| Неподтверждённый состав D (docx/промпт) | Нужно ваше решение — не блокер кода |

**Неблокирующие замечания:** trailing whitespace в `docs/API.md`; полный backend suite не перегонялся после Fix L; `showmigrations` в test settings отключён.

### Риски релиза (после коммитов)

- stores.0008 data migration на prod  
- длинный atomic APPLY 1С / plan report size (Fix K)  
- Redis lock обязателен в prod cache  
- FE/BE должны выкатываться согласованно для auth/checkout/admin  

---

## 10. Итоговая оценка готовности к коммитам

| Критерий | Оценка |
|---|---|
| Working tree целостен относительно принятых packs | **Да** |
| Обязательные 1С/миграции на месте | **Да** |
| Секреты в коммитируемом наборе | **Не обнаружены** |
| План коммитов подготовлен | **Да** |
| Можно делать `git add`/`commit` без вашего ACK | **Нет** |
| Готовность к push/deploy | **Нет** — отдельные этапы |

**Вердикт:** репозиторий **готов к контролируемым коммитам после вашего подтверждения** списков A/B/C/D и порядка §7. Код, Git write и сервер **не трогались**.

---

## Остановка

Ожидаю проверку отчёта и подтверждение состава релиза.
