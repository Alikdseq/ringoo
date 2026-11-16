# RELEASE 24 — ISORT batch 7 (LOW_RISK)

**Дата/время:** 2026-11-16 14:35:00 +03:00  
**Основание:** RELEASE 23 = PASS WITH WARNINGS (остаток 42 tracked CI)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort / Black / flake8 / mypy / deps — без изменений.  
git add / commit / push / pull / fetch / смена ветки / production / платежи / 1С — не выполнялись.

---

## 2. Инвентаризация до

Повторный полный `python -m isort --check-only --diff .` + сверка с `isort_remaining_after_batch6.txt` / classification / списками R18–R23.

| Метрика | Значение |
|---|---:|
| Полный isort fails | **44** |
| Tracked CI | **42** |

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch7_files.txt`

Все diffs **только импорты** (посторонние wrap-изменения от первого прогона isort откатены к HEAD + точечные правки импортов).

| # | Файл | Характер правки | Обоснование безопасности |
|---|---|---|---|
| 1 | `apps/admin_api/views/promotions.py` | alpha в одном import: `PromoCode, Promotion` | один модуль models; без side effects |
| 2 | `apps/backups/offsite.py` | alpha: `_sha256_file, resolve_archive_path` | один модуль services; символы без init-эффектов |
| 3 | `apps/content/urls.py` | alpha `include, path` + blank django↔DRF | app urls (не config); router/views порядок не менялся |
| 4 | `apps/products/management/commands/seed_catalog.py` | alpha `Stock, Store` | один models-import; команда не запускалась |
| 5 | `apps/promotions/admin.py` | alpha `PromoCode, Promotion` | простой ModelAdmin; регистрация по декораторам |
| 6 | `apps/promotions/views.py` | blank django↔DRF + alpha serializers | относительные serializers; validate API не вызывался |
| 7 | `apps/stores/admin.py` | alpha `Stock, Store, StoreImage` | простой admin |
| 8 | `apps/stores/serializers.py` | alpha `Stock, Store, StoreImage` | тот же models-import |
| 9 | `apps/users/serializers.py` | blank django↔DRF + alpha `DeliveryAddress, UserProfile` | локальные models; без signals |
| 10 | `apps/wishlist/tests.py` | alpha django `TestCase`/`reverse` + blank↔DRF | тестовый модуль |

### Пропущены (не в партии)

Сложный reorder / setup / tasks / banned / HOLD, в т.ч.:  
`orders/models|tasks|views`, `cart/views|tests`, `users/views`, `admin_api/urls`, celery/settings/urls, `onec/importer`, drills с `cryptography`, `tmp/*`, R18–R23 файлы.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный isort check | **34** fails |
| Tracked CI remain | **32** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import затронутых app-модулей | **OK** |
| pytest `apps/wishlist/tests.py` | **PASS** (2) |

---

## 5. Блокеры окружения (без правок)

Прежние, deps не ставились:

1. отсутствует **`cryptography`** (backups-тесты);
2. отсутствует **`tenacity`** (maps_service);
3. Promotions validate API → **403**;
4. email status-label: ожидает «Подтверждён», получает «В обработке».

Новых блокеров партия не добавила.

---

## 6. Остаток

| | До | После |
|---|---:|---:|
| All fails | 44 | **34** |
| Tracked CI | 42 | **32** |

Артефакты:

- `backend/var/r11/isort_batch7_files.txt`
- `backend/var/r11/isort_remaining_after_batch7.txt`
- `backend/var/r11/isort_remaining_after_batch7_classification.json`

### Классификация остатка (34)

| Вердикт | Count |
|---|---:|
| HIGH_RISK (banned) | **9** |
| MEDIUM | **5** |
| DEFERRED | **18** |
| HOLD (`tmp/yk_*.py`) | **2** |

**HIGH_RISK:** celery, settings/base, urls, api_urls, bonus/signals, orders/views, cart/views, onec/importer, scripts_sentry_smoke  

**MEDIUM (отложено):** `apps/admin_api/urls.py`, `apps/cart/tests.py`, `apps/orders/models.py`, `apps/orders/tasks.py`, `apps/users/views.py`  

**HOLD:** `scripts/b8_018_zero_smoke.py` (вне remain isort), `tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py`

---

## Вердикт

**PASS WITH WARNINGS** — партия 7: 10 LOW_RISK, только импорты; Django/wishlist зелёные; остаток **32 tracked CI**. Env-блокеры без изменений.

**Остановка.** Следующая партия / flake8 — после согласования.  
**Никаких коммитов и push.**
