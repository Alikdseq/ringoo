# RELEASE 33 — ISORT REMAINING BATCH (AUDIT + SAFE FIX)

**Дата/время:** 2026-11-16 15:26:46 +03:00  
**Основание:** RELEASE 32 = PASS (остаток 16/14)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git mutate / mass `isort .` write / Black / deps / production / платежи / 1С APPLY / smoke/drill/benchmark — **не** выполнялись.

---

## 2. Inventory

| Метрика | До | После |
|---|---:|---:|
| Полный isort fails | **16** | **8** |
| Tracked CI | **14** | **6** |
| Исправлено файлов | — | **8** |

Артефакты: `backend/var/r11/isort_batch_r33_files.txt`, `isort_remaining_after_r33.txt`, `isort_remaining_after_r33_classification.json`.

---

## 3. Классификация всех 14 tracked (аудит)

| Файл | Итог аудита | R33 |
|---|---|---|
| `apps/cart/views.py` | **SAFE** — alpha символов в одном `.serializers` import | исправлен |
| `config/api_urls.py` | **SAFE** — `include, path` (символы одного модуля) | исправлен |
| `config/celery.py` | **SAFE** — blank stdlib↔celery; `setdefault`/`Celery()` порядок сохранён | исправлен |
| `apps/bonus/signals.py` | **SAFE WITH RESTRICTIONS** — merge `BonusAccount, BonusTransaction`; models уже загружен до services | исправлен |
| `config/settings/base.py` | **SAFE WITH RESTRICTIONS** — alpha corsheaders/dotenv + blank; `load_dotenv()` вызывается позже (~стр.47+) | исправлен |
| `apps/orders/tasks.py` | **SAFE WITH RESTRICTIONS** — in-function email before `.models.Order`; email_service без цикла на tasks; `@shared_task` не тронут | исправлен |
| `integrations/onec/importer.py` | **SAFE WITH RESTRICTIONS** — in-function alpha `build_issue_counts, partition_issues` | исправлен |
| `scripts_sentry_smoke.py` | **SAFE** — blanks stdlib↔django и settings↔sentry после `django.setup()` | исправлен |
| `config/urls.py` | **HIGH_RISK / DO NOT FIX** — перестановка settings/admin/static/OTPAdminSite/drf | пропуск |
| `apps/orders/views.py` | **HIGH_RISK / DO NOT FIX** — blank + firstparty blank + in-function cart.views/serializers | пропуск |
| `test_celery.py` | **CONDITIONAL** — `apps.users.tasks` перед `config.celery` | пропуск |
| `tests/test_concurrency_postgres.py` | **CONDITIONAL** — pytest-after-django + in-function | пропуск |
| `scripts/b8_018_load_benchmark.py` | **CONDITIONAL** — in-function в benchmark | пропуск |
| `scripts/block4_offsite_minio_drill.py` | **CONDITIONAL** — drill + cryptography | пропуск |
| HOLD `tmp/yk_*`, `b8_018_zero_smoke` | HOLD | не трогались |

---

## 4. Точные изменения (исправленные)

1. **`apps/cart/views.py`** — `CartItemUpdateSerializer` перед `CartSerializer`.
2. **`config/api_urls.py`** — `from django.urls import include, path`.
3. **`config/celery.py`** — blank между `os` и `celery`.
4. **`apps/bonus/signals.py`** — один import `BonusAccount, BonusTransaction`; services ниже.
5. **`config/settings/base.py`** — blank после stdlib; `corsheaders` перед `dotenv` (вызов `load_dotenv` не переносился).
6. **`apps/orders/tasks.py`** — в `send_order_notifications`: email_service, blank, `.models.Order`.
7. **`integrations/onec/importer.py`** — `build_issue_counts, partition_issues`.
8. **`scripts_sentry_smoke.py`** — blanks; порядок setup → settings → sentry сохранён.

Список: `backend/var/r11/isort_batch_r33_files.txt`.

---

## 5. Пропущенные (причины)

- **`config/urls.py`**: затрагивает порядок settings/admin/OTPAdminSite/static/spectacular — риск URL/admin init.
- **`apps/orders/views.py`**: критичный заказовой API + in-function cart imports; сомнение не снято.
- **`test_celery.py`**: возможная зависимость регистрации task от импорта `config.celery` первым.
- **concurrency / load_benchmark / offsite_drill**: in-function и/или drill; drill не запускался.

---

## 6. Проверки

| Проверка | Результат |
|---|---|
| isort check партии (8) | **PASS** |
| Полный isort | **8** fails / **6** tracked CI |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import signals/cart/tasks/api_urls/celery/settings.base/importer | **OK** (без APPLY/email/платежей) |
| pytest bonus + cart + `TestSendOrderNotificationsIdempotent` | **PASS** (37 passed, 5 skipped) |

Sentry smoke / drills / benchmark **не** исполнялись.  
Env-блокеры (`cryptography`, `tenacity`, promotions 403, email status-label) не чинились.

---

## 7. Остаток после R33

| Вердикт | Файлы |
|---|---|
| HIGH_RISK (2) | `apps/orders/views.py`, `config/urls.py` |
| DEFERRED (4) | `test_celery.py`, `tests/test_concurrency_postgres.py`, `scripts/b8_018_load_benchmark.py`, `scripts/block4_offsite_minio_drill.py` |
| HOLD (2) | `tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py` |

---

## 8. Сохранность прежних изменений

Surgical import-only patches; pre-existing Black/wrap в working tree не откатывались. HOLD не открывались.

---

## Вердикт

**PASS** — 8 файлов исправлены после аудита; tracked CI **14 → 6**; Django/import/pytest OK; критичные `config/urls` и `orders/views` оставлены.

**Остановка.** flake8 / mypy — после оценки.  
**Никаких коммитов и push.**
