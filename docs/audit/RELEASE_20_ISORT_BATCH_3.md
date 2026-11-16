# RELEASE 20 — ISORT batch 3 (LOW_RISK blank lines)

**Дата/время:** 2026-11-16 14:18:10 +03:00  
**Основание:** RELEASE 19 = PASS (остаток 82 tracked CI)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort не менялся. R18–R19 правки сохранены.

---

## 2. Инвентаризация до партии

| Метрика | Значение |
|---|---:|
| Полный isort fails | **84** |
| Tracked CI | **82** |
| Уже исправлены R18–R19 | 26 |
| Blank-only кандидаты (ещё fails, не banned) | 39 |

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch3_files.txt`

### tests/ (7)
1. `tests/test_sec001_staff_order_access.py`
2. `tests/test_sec002_public_reviews.py`
3. `tests/test_sec004_review_throttle.py`
4. `tests/test_sec007_yookassa_webhook.py`
5. `tests/test_sec008_bonus_permissions.py`
6. `tests/test_sec009_password_reset.py`
7. `tests/test_yookassa_payments.py`

### apps/ (3)
8. `apps/admin_api/views/dashboard.py`
9. `apps/admin_api/views/onec_sync.py`
10. `apps/admin_api/views/reports.py`

**Обоснование:** все 10 — `blank_lines_only` (пустая строка между Django и rest_framework).  
`IMPORT_CHANGES=0`. Импорты не переставлялись, не удалялись, не переносились в/из функций.

Banned high-risk / HOLD / tmp / var / migrations — не включались.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный `isort --check-only --diff .` | **74** fails |
| Tracked CI remain | **72** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest (7 test-файлов) | **71 passed** |
| import admin_api views (dashboard/onec_sync/reports) | **OK** |

---

## 5. После / остаток

| | До | После |
|---|---:|---:|
| All fails | 84 | **74** |
| Tracked CI | 82 | **72** |

Список: `backend/var/r11/isort_remaining_after_batch3.txt`.

### Отложено (ручной разбор)

- Banned: `config/celery.py`, `config/settings/*`, `config/urls.py`, `config/api_urls.py`, `apps/bonus/signals.py`, `apps/orders/views.py`, `apps/cart/views.py`, `integrations/onec/importer.py`, `scripts_sentry_smoke.py`
- HOLD: `scripts/b8_018_zero_smoke.py`
- MEDIUM/HIGH из classification (reorder импортов в app-коде / сложные diffs)
- tmp: `tmp/yk_*.py`

---

## 6. Git

HEAD без коммита. Изменены только 10 файлов партии.  
Логика / deps / configs — без изменений. Коммитов/push нет.

---

## Вердикт

**PASS** — партия 3 (10 blank-only) зелёная; остаётся **72 tracked CI** isort fails.

**Остановка.** Следующая партия / flake8 — только после согласования.  
**Никаких коммитов и push.**
