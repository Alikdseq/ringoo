# RELEASE 19 — ISORT manual batch 1 (LOW_RISK)

**Дата/время:** 2026-11-16 14:14:36 +03:00  
**Основание:** RELEASE 18 = PASS (остаток ~92 tracked CI)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

R18 batch1 сохранён. Конфиг isort **не** менялся.

---

## 2. Актуальная инвентаризация (до партии)

| Метрика | Значение |
|---|---:|
| Полный `isort --check-only .` | **94** fails |
| Tracked CI (без tmp/HOLD) | **92** |
| Исключённые из отбора (banned high-risk list) | 12 путей (часть всё ещё в fails) |
| Кандидаты к анализу (tracked CI − banned) | **83** |

Источник: `backend/var/r11/isort_r19_all_fails.txt`, `isort_r19_tracked_ci_fails.txt`.

### Классификация (анализ diff)

Артефакт: `backend/var/r11/isort_manual_batch2_classification.json`

| Risk | Count (из 83) |
|---|---:|
| LOW_RISK | 52 |
| MEDIUM_RISK | 7 |
| HIGH_RISK | 24 |

---

## 3. Выбранная партия (10) — все `blank_lines_only` tests

Список: `backend/var/r11/isort_batch2_files.txt`

| # | File | Обоснование LOW_RISK |
|---:|---|---|
| 1 | `tests/test_admin_api_auth.py` | только blank между Django↔DRF |
| 2 | `tests/test_func003_price_consistency.py` | то же |
| 3 | `tests/test_func011_func004_color_and_cart.py` | то же |
| 4 | `tests/test_int026_reorder_color_store.py` | то же |
| 5 | `tests/test_onec_field_protection.py` | то же |
| 6 | `tests/test_onec_inbound_order_status.py` | то же |
| 7 | `tests/test_onec_partner_enqueue.py` | то же |
| 8 | `tests/test_onec_sync_log.py` | то же |
| 9 | `tests/test_payment_type_bank_transfer_disabled.py` | то же |
| 10 | `tests/test_rate_limits.py` | то же |

Banned list (celery/settings/signals/orders.views/…) **не** включались.

### Что изменилось в импортах

**Ничего в строках `import`/`from`.**  
Только добавлена пустая строка между секциями (Django → THIRDPARTY).  
`IMPORT_CHANGES=0` по `git diff` партии.

Семантика / порядок выполнения модулей / signals / tasks — без изменений.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия 10) | **PASS** |
| Полный `isort --check-only --diff .` | **84** fails (было 94) |
| Tracked CI remain | **82** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest (10 файлов партии) | **47 passed** |

Циклические импорты: не применимо (только blank lines в tests).

---

## 5. Остаток

`backend/var/r11/isort_remaining_after_batch2.txt` — **84** всего / **82** tracked CI.

Δ tracked CI: 92 → **82** (−10).

### MEDIUM_RISK (примеры, не трогали)

Из classification: app-модули с reorder тех же import-строк (нужен review) — см. JSON (`risk=MEDIUM_RISK`).

### HIGH_RISK / HOLD (не трогали)

Включая banned:

- `config/celery.py`, `config/settings/*`, `config/urls.py`, `config/api_urls.py`
- `apps/bonus/signals.py`, `apps/orders/views.py`, `apps/cart/views.py`
- `integrations/onec/importer.py`, `scripts_sentry_smoke.py`
- HOLD: `scripts/b8_018_zero_smoke.py`
- tmp: `tmp/yk_*.py`

---

## 6. Git

HEAD без коммита. Изменены только 10 test-файлов партии.  
Конфиги/deps/логика — без изменений. Коммитов/push нет.

---

## Вердикт

**PASS** — 10 LOW_RISK test-файлов исправлены (blank lines only), проверки и pytest зелёные; остаётся **82 tracked CI** isort fails.

isort **не закрыт**. Следующая партия — только после согласования.  
**Не** переходить к flake8.  
**Никаких коммитов и push.**
