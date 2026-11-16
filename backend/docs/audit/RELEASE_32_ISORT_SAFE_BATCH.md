# RELEASE 32 — ISORT SAFE BATCH (MULTI-FILE)

**Дата/время:** 2026-11-16 15:11:44 +03:00  
**Основание:** RELEASE 31 = PASS (остаток 19/17)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git add/commit/push/pull/fetch / смена ветки / Black / deps / mass `isort .` write / production / платежи / 1С APPLY / smoke — **не** выполнялись.

---

## 2. Inventory до

| Метрика | Значение |
|---|---:|
| Полный isort fails | **19** |
| Tracked CI | **17** |

Исходный tracked список: `backend/var/r11/isort_r32_tracked_before.txt`.

---

## 3. Классификация каждого tracked-файла (до fix)

| Файл | Класс | Решение R32 |
|---|---|---|
| `apps/users/tests_security_data.py` | SAFE WITH RESTRICTIONS | **исправлен** (in-method django↔apps) |
| `tests/test_sec005_order_idempotency.py` | SAFE WITH RESTRICTIONS | **исправлен** (blank + in-method) |
| `tests/test_online_cart_retention.py` | SAFE WITH RESTRICTIONS | **исправлен** (top alpha + in-method) |
| `apps/orders/tasks.py` | MEDIUM / CONDITIONAL | **пропуск** — in-function Celery task; явный запрет автоправки |
| `test_celery.py` | CONDITIONAL | **пропуск** — порядок `apps.users.tasks` vs `config.celery` после setup |
| `tests/test_concurrency_postgres.py` | CONDITIONAL | **пропуск** — необычный pytest-after-django + in-function |
| `scripts/b8_018_load_benchmark.py` | CONDITIONAL | **пропуск** — in-function в benchmark; drill-подобное |
| `scripts/block4_offsite_minio_drill.py` | CONDITIONAL | **пропуск** — drill + in-function + `cryptography` |
| `apps/bonus/signals.py` | HIGH_RISK | **пропуск** |
| `apps/cart/views.py` | HIGH_RISK | **пропуск** |
| `apps/orders/views.py` | HIGH_RISK | **пропуск** |
| `config/api_urls.py` | HIGH_RISK | **пропуск** |
| `config/celery.py` | HIGH_RISK | **пропуск** |
| `config/settings/base.py` | HIGH_RISK | **пропуск** |
| `config/urls.py` | HIGH_RISK | **пропуск** |
| `integrations/onec/importer.py` | HIGH_RISK | **пропуск** |
| `scripts_sentry_smoke.py` | HIGH_RISK | **пропуск** |
| `tmp/yk_*.py` | HOLD | **пропуск** |
| `scripts/b8_018_zero_smoke.py` | HOLD | вне remain; не трогать |

Чистых **SAFE** (только blank без reorder / без in-function) среди остатка **не** осталось.

---

## 4. Исправленные файлы (3)

Список: `backend/var/r11/isort_batch_r32_files.txt`

### 4.1 `apps/users/tests_security_data.py`
В `test_log_admin_action_called_from_export_pattern`: django (`get_user_model`, `RequestFactory`) перед `apps.audit.*` + blank.  
Без смены scope; side effects нет.

### 4.2 `tests/test_sec005_order_idempotency.py`
- blank django↔DRF на top-level;
- in-method: `RequestFactory` перед `apps.orders.views._order_idempotency_cache_key`.

### 4.3 `tests/test_online_cart_retention.py`
- blank django↔DRF; `PaymentError` алфавитно среди `apps.payments.*`;
- in-method: `APIRequestFactory` перед cart/users imports.

Переносов module↔function **нет**. Тела тестов/логика — без изменений.

---

## 5. Пропущенные (причины)

См. таблицу §3. Кратко: HIGH_RISK без аудита; `orders/tasks.py` по запрету; celery/concurrency/drills — сомнение в порядке init или in-function в не-test scripts.

---

## 6. Проверки

| Проверка | Результат |
|---|---|
| isort check партии (3 файла) | **PASS** |
| Полный isort | **16** fails |
| Tracked CI | **14** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest security_data + sec005 + online_cart_retention | **PASS** (28) |

Известные env-блокеры (`cryptography`, `tenacity`, promotions 403, email status-label) в прогон не входили / не чинились.

---

## 7. Inventory после

| | До | После |
|---|---:|---:|
| All fails | 19 | **16** |
| Tracked CI | 17 | **14** |
| Исправлено файлов | — | **3** |

Артефакты: `isort_remaining_after_r32.txt`, `isort_remaining_after_r32_classification.json`.

### Классификация остатка (16)

| Вердикт | Count |
|---|---:|
| HIGH_RISK | **9** |
| MEDIUM (`orders/tasks.py`) | **1** |
| DEFERRED | **4** (`test_celery`, concurrency, load_benchmark, offsite_drill) |
| HOLD (`tmp/yk_*`) | **2** |

---

## 8. Сохранность прежних изменений

- Surgical patch только согласованных import-блоков.
- Ранее незакоммиченные Black/wrap в других файлах и `orders/tasks.py` / HIGH_RISK **не** откатывались и **не** переформатировались этим релизом.

---

## Вердикт

**PASS** — 3 SAFE WITH RESTRICTIONS исправлены; tracked CI **17 → 14**; Django/pytest OK; HIGH_RISK/HOLD/`orders/tasks` не тронуты.

**Остановка.** flake8 / mypy / следующий этап — после оценки отчёта.  
**Никаких коммитов и push.**
