# RELEASE 25 — ISORT batch 8 (LOW_RISK + точечный MEDIUM)

**Дата/время:** 2026-11-16 14:39:56 +03:00  
**Основание:** RELEASE 24 = PASS WITH WARNINGS (остаток 32 tracked CI)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort / Black / flake8 / mypy / deps — без изменений.  
git add / commit / push / pull / fetch / смена ветки / reset / clean / checkout / production / платежи / 1С APPLY / smoke-drill — не выполнялись.

---

## 2. Инвентаризация до

Повторный полный `python -m isort --check-only --diff .` + сверка с `isort_remaining_after_batch7.*` и списками R18–R24.

| Метрика | Значение |
|---|---:|
| Полный isort fails | **34** |
| Tracked CI | **32** |

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch8_files.txt`  
Правки — **только импорты** (surgical от HEAD; без wrap-форматирования тела).

| # | Файл | Характер | Риск | Обоснование |
|---|---|---|---|---|
| 1 | `apps/admin_api/views/content.py` | merge/alpha DRF (`serializers, status`; parsers; response) | LOW | один third-party пакет; без side effects |
| 2 | `apps/cart/tests.py` | blank django↔DRF; `Stock, Store`; serializers alpha; services после serializers | MEDIUM→OK | только тестовый модуль; импорты top-level; merge_guest / serializers без init-порядка |
| 3 | `apps/orders/tests.py` | blank django↔DRF; `Stock, Store`; relative alpha delivery→models→serializers→tasks | LOW | тестовый модуль |
| 4 | `apps/payments/management/commands/report_ops_alerts.py` | django alpha (`cache`/`BaseCommand`); payments `locks` before `models` | LOW | management command; константы locks |
| 5 | `apps/products/services/bulk_import.py` | firstparty alpha models→services→utils; убран лишний blank | LOW | сервис без AppConfig/signals |
| 6 | `apps/products/views.py` | relative alpha `cache_utils` before `catalog_filters` | LOW | оба локальных модуля без циклической зависимости на порядок |
| 7 | `apps/stores/tests.py` | DRF-секция; `Stock, Store`; blank-группы | LOW | тесты |
| 8 | `apps/stores/views.py` | `apps.orders` before `apps.products`; `Stock, Store` | LOW | алфавит firstparty + models symbols |
| 9 | `tests/test_onec_block6_performance.py` | django alpha + blank↔DRF | LOW | тесты |
| 10 | `tests/test_onec_stock_reconciliation.py` | blank django↔DRF; warehouse_map alpha | LOW | тесты; importer не reorder |

### MEDIUM рассмотрены, **не** включены

| Файл | Причина пропуска |
|---|---|
| `apps/admin_api/urls.py` | merge двух `.views` импортов + multiline; порядок загрузки view-модулей не доказан безопасным |
| `apps/orders/models.py` | правка **внутри функции** (`import random` / django) — запрет без отдельного согласования |
| `apps/orders/tasks.py` | правка **внутри task-функции**; Celery/email порядок |
| `apps/users/views.py` | сложный merge auth/JWT/DRF + перенос `transaction` — сомнения |

Также не трогались: HIGH_RISK/HOLD, in-function imports в security/concurrency/sec005/drills, R18–R24 файлы.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный isort check | **24** fails |
| Tracked CI remain | **22** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import затронутых app-модулей | **OK** |
| pytest cart + orders + stores + onec block6/stock | **PASS** (91) |

---

## 5. Блокеры окружения (без правок)

1. отсутствует **`cryptography`**  
2. отсутствует **`tenacity`**  
3. Promotions validate API → **403**  
4. email status-label: «Подтверждён» vs «В обработке»

Deps не ставились; тесты/код ради обхода не менялись. Новых блокеров нет.

---

## 6. Остаток

| | До | После |
|---|---:|---:|
| All fails | 34 | **24** |
| Tracked CI | 32 | **22** |

Артефакты:

- `backend/var/r11/isort_batch8_files.txt`
- `backend/var/r11/isort_remaining_after_batch8.txt`
- `backend/var/r11/isort_remaining_after_batch8_classification.json`

### Классификация остатка (24)

| Вердикт | Count |
|---|---:|
| HIGH_RISK | **9** |
| MEDIUM | **4** |
| DEFERRED | **9** |
| HOLD (`tmp/yk_*.py`) | **2** |

**HIGH_RISK:** celery, settings/base, urls, api_urls, bonus/signals, orders/views, cart/views, onec/importer, scripts_sentry_smoke  

**MEDIUM:** `apps/admin_api/urls.py`, `apps/orders/models.py`, `apps/orders/tasks.py`, `apps/users/views.py`  

**HOLD:** `scripts/b8_018_zero_smoke.py` (вне remain), `tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py`

---

## Вердикт

**PASS WITH WARNINGS** — партия 8: 10 файлов (9 LOW + 1 проанализированный MEDIUM `cart/tests.py`); только импорты; pytest 91 PASS; остаток **22 tracked CI**.

**Остановка.** Следующая партия / flake8 — после согласования.  
**Никаких коммитов и push.**
