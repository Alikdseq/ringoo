# RELEASE 18 — ISORT: инвентаризация + безопасная партия 1

**Дата/время:** 2026-11-16 14:08:35 +03:00  
**Основание:** RELEASE 10 inventory; RELEASE 17 Black CI scope PASS  
**Вердикт:** **PASS** (партия) — isort **не** закрыт целиком

---

## 1. Branch / HEAD / isort

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиги R8 (`.isort.cfg` / `[tool.isort]`) **не менялись**.

---

## 2. Свежая инвентаризация (до партии)

Команда: `python -m isort --check-only --diff .`

| Метрика | Значение |
|---|---:|
| Файлов с нарушениями | **110** (не старые 116) |
| Список | `backend/var/r11/isort_remaining_before_batch1.txt` |
| Классификация | `backend/var/r11/isort_batch1_classification.json` |

Из 110: почти все tracked CI; 2 = `tmp/yk_*.py` (вне CI). HOLD `zero_smoke` в fails не попал.

Black R12–R17 снизил число относительно R10 (116→110) за счёт части blank-line drift, но большинство isort fails осталось.

---

## 3. Кандидаты R10 AUTO_OK — повторная проверка

| Исход | Count | Файлы |
|---|---:|---|
| Уже PASS (не трогали) | 2 | `tests/test_block8_catalog_guards.py`, `tests/test_int001_int002_order_fsm.py` |
| AUTO_OK blank-only → исправлены | **16** | см. §4 |
| MANUAL из списка кандидатов | 0 | — |
| not tracked / вне CI | 0 | — |

У всех 16 diff isort: только `+` пустая строка между блоками Django и rest_framework / FIRSTPARTY. **Строки `import`/`from` не менялись** (`IMPORT_CHANGES=0`).

---

## 4. Исправленные файлы (партия 1)

Список: `backend/var/r11/isort_batch1_files.txt`

1. `apps/admin_api/views/orders.py`
2. `apps/admin_api/views/products.py`
3. `apps/admin_api/views/stock.py`
4. `apps/users/tests.py`
5. `tests/test_admin_integrity.py`
6. `tests/test_func001_expire_yookassa_sync.py`
7. `tests/test_func002_func009_cancel_policy.py`
8. `tests/test_order_repay.py`
9. `tests/test_payment_security.py`
10. `tests/test_sber_payments.py`
11. `tests/test_sec003_cancel_releases_stock.py`
12. `tests/test_sec006_guest_access_token.py`
13. `tests/test_fix_pack_a_guest_success.py`
14. `tests/test_fix_pack_b_order_cancellation.py`
15. `tests/test_onec_block3_series_cart.py`
16. `tests/test_onec_block5_security_integrity.py`

Применение: `isort <16 files>` — **не** `isort .`.

---

## 5. После исправлений

| Метрика | Значение |
|---|---:|
| isort fails всего | **94** |
| Tracked CI remain | **92** |
| tmp/untracked remain | **2** (`tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py`) |
| Список остатка | `backend/var/r11/isort_remaining_after_batch1.txt` |

Δ: 110 → 94 (−16).

---

## 6. MANUAL / чувствительные (не трогали)

Примеры из fail-set (вердикт MANUAL в JSON):

- `config/celery.py`, `config/settings/base.py`, `config/urls.py`, `config/api_urls.py`
- `apps/bonus/signals.py`
- `apps/orders/views.py`, `apps/cart/views.py`, `integrations/onec/importer.py`
- `scripts_sentry_smoke.py` / setup-после-импортов
- остальные ~90 tracked fails — требуют перестановки импортов или ручной проверки; **не** входили в эту партию

HOLD: `scripts/b8_018_zero_smoke.py` — не трогали.

---

## 7. Проверки

| Проверка | Результат |
|---|---|
| isort `--check-only` (партия 16) | **PASS** |
| Полный `isort --check-only --diff .` | exit 1; **94** fails |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest (12 test-файлов партии) | **160 passed** |

Конфиги / deps / Black / flake8 / mypy — не менялись.  
Набор и порядок строк импортов в партии — без изменений (только blank lines между секциями).

Примечание: `git diff --stat` vs HEAD для части файлов включает ранее грязный Black (R12+); вклад isort партии — пустые строки между секциями.

---

## 8. Git

HEAD без коммита. Изменены только 16 файлов §4 (isort blank lines поверх существующего dirty).  
Коммитов / push нет.

---

## Вердикт

**PASS** — свежая инвентаризация (110), безопасная партия 1 (16 blank-only) применена, проверки зелёные; остаётся **92 tracked CI** isort fails.

isort **не закрыт**. Следующая партия / MANUAL — только после согласования.  
**Не** переходить к flake8.  
**Никаких коммитов и push.**
