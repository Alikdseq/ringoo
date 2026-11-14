# FIX-PACK G — FSM v2: обновление устаревших тестов (B8-010)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production:** не затрагивался  
**Коммит / push:** не создавались  
**`.env` / секреты:** не читались  
**Миграции / FSM / stock runtime:** не менялись  

---

## 1. Первоначальные падения (BLOCK 8)

На момент BLOCK 8 полный suite:

- **13 failed**, 432 passed, 8 skipped  
- Корневая traceback: `AssertionError: 'closed' != 'cancelled'`  
- Пример: `tests/test_sec003_cancel_releases_stock.py` ждал `Order.STATUS_CANCELLED`, сервис писал FSM v2 `closed` + `closure_result=cancelled`

### Таблица (диагностика актуального working tree)

| Тест / группа | Старое ожидание | Фактическое состояние после cancel | Причина FAIL (BLOCK 8) | Состояние до Fix G | Требуемое изменение |
|---|---|---|---|---|---|
| `test_sec003_*` (cancel releases) | `status == cancelled` | `closed` + `closure_result=cancelled` | Legacy assert | Уже `assert_order_cancelled` (Fix B) | Подтвердить |
| `test_func001_*` (expire unpaid) | `status == cancelled` | closed+cancelled | Legacy assert | Fix B | Подтвердить |
| `test_func002_*` (cancel policy) | legacy status | closed+cancelled | Legacy assert | Fix B | Подтвердить |
| `test_block8_refund_settlement` | legacy status | closed+cancelled | Legacy assert | Fix B | Подтвердить |
| `test_int004_*` refund metadata | legacy status | closed+cancelled | Legacy assert | Fix B | Подтвердить |
| `test_sber_*` expire unpaid | legacy status | closed+cancelled | Legacy assert | Fix B | Подтвердить |
| `test_sec006` guest cancel | display/status | display=`cancelled`, status closed | Частично | Fix B + display_status | Подтвердить |
| Guest-cancel / SEC-006 | ownership token | без ослабления | — | Fix A/B | Регресс OK |

**Вывод этапа 1:** исходные **13 FAIL B8-010 уже устранены в FIX-PACK B** (`order_fsm_assertions.assert_order_cancelled`, обновлённые suites). До Fix G полный `tests/` suite: **459 passed, 8 skipped, 0 failed**.

Runtime-дефектов FSM/резервов при повторной диагностике **не обнаружено** — менять сервисы не требовалось.

---

## 2. Что сделано в Fix G (остаточный hardening)

Не «перекраска ради зелёного» — укрепление фикстур и asserts, которые ещё сеяли legacy `status='cancelled'`.

### 2.1. Helper

`tests/order_fsm_assertions.py`:

- `fsm_v2_create_kwargs(**kwargs)` — `status=cancelled` → `closed` + `closure_result=cancelled`
- `assert_order_completed` — `closed` + `completed`, и **не** `is_cancelled()`

### 2.2. Обновлённые фикстуры / asserts

| Файл | Изменение |
|---|---|
| `tests/test_int001_int002_order_fsm.py` | `_order()` через `fsm_v2_create_kwargs`; bulk-skip → `assert_order_cancelled` |
| `tests/test_payment_security.py` | `_catalog_order` + late-pay assert → `assert_order_cancelled` |
| `tests/test_order_repay.py` | `_make_order` через `fsm_v2_create_kwargs` |
| `tests/test_sber_payments.py` | `_order` через `fsm_v2_create_kwargs` |

### 2.3. Fix F leftover: `TestJwtLoginMergesGuestCart`

| Поле | Значение |
|---|---|
| Файл | `apps/users/tests.py` (вне `testpaths=["tests"]`) |
| FAIL | add to cart → 400 `Товара нет в наличии` |
| Причина | Cart API проверяет retail Stock; фикстура без Stock |
| Исправление | Создать `Store` + `Stock(quantity=10)` в `setUp` |
| Production-код | **не** менялся |

---

## 3. Assertions: до / после (контракт)

| Семантика | Правильный assert |
|---|---|
| Отмена | `is_cancelled()` + `status==closed` + `closure_result==cancelled` |
| Завершение | `is_fulfilled()` / `assert_order_completed` — **не** проходит `is_cancelled()` |
| UI | `display_status_code()` / API `display_status` → `"cancelled"` |
| Legacy seed | через `fsm_v2_create_kwargs`, не сырой `status='cancelled'` |

---

## 4. Проверки бизнес-логики (не маскировка)

По точечным suites (все **passed**):

1. Отмена освобождает `reserved_quantity` (`test_sec003`).  
2. Повторный release идемпотентен (Fix B + sec003).  
3. Физический `quantity` не уменьшается при локальной отмене.  
4. `closed+completed` ≠ отмена (`assert_order_completed` / repay completed).  
5. `closed+cancelled` → `is_cancelled()` True.  
6. Expire unpaid → cancel + release (`test_func001`).  
7. Refund settlement не ломает FSM asserts (`test_block8_refund_settlement`).  
8. Guest cancel + SEC-006 (`test_sec006`).  
9. Повторная отмена API — контракт Fix B.

**FSM / transitions / stock_ops / 1С — не изменялись.**

---

## 5. Изменённые файлы

- `backend/tests/order_fsm_assertions.py`
- `backend/tests/test_int001_int002_order_fsm.py`
- `backend/tests/test_payment_security.py`
- `backend/tests/test_order_repay.py`
- `backend/tests/test_sber_payments.py`
- `backend/apps/users/tests.py`
- `docs/audit/FIX_PACK_G_FSM_V2_TESTS_REPORT.md`

---

## 6. Результаты тестов

### Точечные

| Suite | Result |
|---|---|
| sec003, func001, func002, block8 refund, int004, int001, payment_security, order_repay, sber, Fix A/B, SEC-005/006, JwtLoginMergesGuestCart, StaffAccess | **158 passed** |
| `apps/users/tests.py` (весь модуль) | **23 passed** |

### Полный backend suite (`testpaths=tests`)

| Метрика | Result |
|---|---|
| Passed | **459** |
| Failed | **0** |
| Skipped | **8** (`test_concurrency_postgres` и др.) |
| Время | ~32 s |

### Django

| Check | Result |
|---|---|
| `manage.py check` | OK (0 issues) |
| `makemigrations --check --dry-run` | No changes detected |

---

## 7. Совместимость Fix A–F

| Pack | Статус |
|---|---|
| A guest success | OK |
| B cancel/FSM | OK (база B8-010) |
| C auth refresh | не затрагивался |
| D idempotency/pay | SEC-005 OK |
| E UI | не затрагивался |
| F AdminGuard | StaffAccess users tests OK; JwtLoginMergesGuestCart починен |

BLOCK 1–7: код не менялся; onec suites в полном прогоне зелёные.

---

## 8. Оставшееся / непроверенное

1. Postgres concurrent cancel (`test_concurrency_postgres` — 7 skipped без PG).  
2. Реальные PSP/1С.  
3. `apps/*/tests.py` не входят в default `testpaths` — гонялись явно; при желании CI может расширить discovery отдельно.  
4. B8-015–019 — вне scope.

---

## 9. Вердикт B8-010

| Критерий | Статус |
|---|---|
| 13 legacy FAIL устранены | **Да** (Fix B + подтверждение Fix G) |
| Полный pytest зелёный | **Да** (459 passed, 0 failed) |
| FSM не откатывали | **Да** |
| JwtLoginMergesGuestCart | **Исправлен** (фикстура Stock) |

**СТОП:** Fix-pack G завершён. Следующий pack не начинался.
