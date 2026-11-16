# RELEASE 22 — ISORT batch 5 (LOW_RISK)

**Дата/время:** 2026-11-16 14:24:23 +03:00  
**Основание:** RELEASE 21 = PASS WITH WARNINGS (остаток 62 tracked CI)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort / Black / flake8 / mypy / deps — без изменений.

---

## 2. Инвентаризация до

| Метрика | Значение |
|---|---:|
| Полный isort fails | **64** |
| Tracked CI | **62** |
| Blank-only кандидаты (ещё не в R18–21, не banned) | **19** |

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch5_files.txt`

1. `apps/products/admin.py` — **alpha reorder** двух имён в *локальном* `from …lifecycle import (archive_product, product_hard_delete_blocked)` (один модуль, внутри метода; side effects нет)
2. `apps/products/cache_utils.py` — blank lines only
3. `apps/products/mapping_views.py` — blank lines only (isort)
4. `apps/products/tests.py` — blank lines only (isort)
5. `apps/promotions/tests.py` — blank lines only (isort)
6. `apps/returns/tests.py` — blank lines only (isort)
7. `apps/returns/views.py` — blank lines only (isort)
8. `apps/users/admin_mfa.py` — blank lines only
9. `apps/users/authentication.py` — blank lines only
10. `apps/users/password_reset.py` — blank lines only

Banned / HOLD / tmp / var / migrations / R18–21 files — не включались.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный isort check | **54** fails |
| Tracked CI remain | **52** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import products/users/returns modules | **OK** |
| pytest products + returns | **PASS** |
| pytest promotions validate API (3) | **FAIL** — 403 (как R14) |

---

## 5. WARNING — promotions 403

`TestPromoCodeValidateAPI::*` → `Forbidden: /api/v1/promocodes/validate/` (403 ≠ 200/400).

Причина: throttle/auth окружения (как RELEASE 14), не перестановка импортов. Deps не ставились.

---

## 6. Остаток

| | До | После |
|---|---:|---:|
| All fails | 64 | **54** |
| Tracked CI | 62 | **52** |

- `backend/var/r11/isort_remaining_after_batch5.txt`
- `backend/var/r11/isort_remaining_after_batch5_classification.json`

### MEDIUM / HIGH / HOLD (отложено)

- HIGH/banned: celery, settings/*, urls, api_urls, bonus/signals, orders/cart views, onec/importer, scripts_sentry_smoke
- HOLD: `scripts/b8_018_zero_smoke.py`
- tmp: `tmp/yk_*.py`
- прочие DEFERRED с reorder импортов

---

## Вердикт

**PASS WITH WARNINGS** — партия 5 зелёная по isort/Django/imports; остаётся **52 tracked CI**; promotions validate API даёт 403 в текущем окружении.

**Остановка.** Следующая партия / flake8 — после согласования.  
**Никаких коммитов и push.**
