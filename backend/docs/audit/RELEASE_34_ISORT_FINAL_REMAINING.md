# RELEASE 34 — ISORT FINAL REMAINING AUDIT + SAFE FIX

**Дата/время:** 2026-11-16 15:30:20 +03:00  
**Основание:** RELEASE 33 = PASS (остаток 8/6)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git mutate / mass `isort .` write / Black / deps / production / платежи / 1С / smoke/drill/benchmark — **не** выполнялись.

---

## 2. Inventory

| Метрика | До | После |
|---|---:|---:|
| Полный isort fails | **8** | **3** |
| Tracked CI | **6** | **1** |
| Исправлено файлов | — | **5** |

Остаток tracked CI: только `test_celery.py`.  
Полный остаток: `test_celery.py` + HOLD `tmp/yk_*.py`.

Артефакты: `backend/var/r11/isort_batch_r34_files.txt`, `isort_remaining_after_r34.txt`, `isort_remaining_after_r34_classification.json`.

---

## 3. Классификация 6 tracked

| Файл | Класс | Решение |
|---|---|---|
| `apps/orders/views.py` | **SAFE WITH RESTRICTIONS** | исправлен |
| `config/urls.py` | **SAFE WITH RESTRICTIONS** | исправлен |
| `tests/test_concurrency_postgres.py` | **SAFE WITH RESTRICTIONS** | исправлен |
| `scripts/b8_018_load_benchmark.py` | **SAFE WITH RESTRICTIONS** | исправлен (скрипт не запускался) |
| `scripts/block4_offsite_minio_drill.py` | **SAFE WITH RESTRICTIONS** | исправлен (drill не запускался) |
| `test_celery.py` | **CONDITIONAL / DO NOT FIX** | пропуск |

HOLD не трогались.

---

## 4. Обоснование и точные diff

### 4.1 `apps/orders/views.py` — исправлен
- blank django↔DRF;
- убран blank между firstparty `apps.users.services` и `config.throttling`;
- in-function: `CartSerializer` перед `_get_cart_queryset` (alpha `apps.cart.*`).
- `apps/cart/views.py` не импортирует `orders.views` → цикла нет.
- Логика заказов/idempotency/API не менялась.

### 4.2 `config/urls.py` — исправлен
- `settings` до `admin`/`urls` (нужно для `ADMIN_OTP_ENABLED`);
- `include, path` alpha;
- `static` перед `RedirectView`;
- blanks перед spectacular и `config.views`.
- Блок `OTPAdminSite` по-прежнему **до** `urlpatterns`; path names / namespace не менялись.

### 4.3 `tests/test_concurrency_postgres.py` — исправлен
- При `known_django` + секции `DJANGO` перед `THIRDPARTY` isort корректно ставит `pytest` после django;
- in-function: `timedelta` перед `timezone`.
- Модуль без `RINGOO_TEST_POSTGRES` skip’ается — destructive concurrency не запускалась.

### 4.4 `scripts/b8_018_load_benchmark.py` — исправлен
- blanks django↔firstparty в `lock_tests`;
- `Decimal` перед `Product` (stdlib↔firstparty).
- Benchmark **не** исполнялся.

### 4.5 `scripts/block4_offsite_minio_drill.py` — исправлен
- `import secrets` перед `cryptography` (stdlib↔thirdparty) внутри try.
- Drill **не** исполнялся.

### 4.6 `test_celery.py` — ПРОПУСК
- Diff: `time` в stdlib + `apps.users.tasks` **перед** `config.celery` после `django.setup()`.
- Текущий порядок celery-app → tasks может быть намеренным для регистрации; сомнение не снято → **не меняли**.

---

## 5. Проверки

| Проверка | Результат |
|---|---|
| isort check партии (5) | **PASS** |
| Полный isort | **3** fails (1 tracked + 2 HOLD) |
| Tracked CI | **1** (`test_celery.py`) |
| `git diff --check` | **PASS** |
| Django check | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import `orders.views` / `config.urls` | **OK** |
| pytest order create + sec005 + concurrency module | **9 passed, 7 skipped** |

Env-блокеры / drill / benchmark / celery script — не обходились и не запускались.

---

## 6. Остаток

| Вердикт | Count | Файлы |
|---|---:|---|
| CONDITIONAL | **1** | `test_celery.py` |
| HOLD | **2** | `tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py` |

`scripts/b8_018_zero_smoke.py` — HOLD, вне remain.

---

## 7. Сохранность прежних изменений

Только согласованные import-правки; прежние Black/wrap не откатывались.

---

## Вердикт

**PASS** — 5 из 6 tracked закрыты; tracked CI **6 → 1**; единственный осознанный остаток — `test_celery.py` (порядок celery vs tasks). HOLD нетронуты.

**Остановка.** flake8 в этот релиз не входит.  
**Никаких коммитов и push.**
