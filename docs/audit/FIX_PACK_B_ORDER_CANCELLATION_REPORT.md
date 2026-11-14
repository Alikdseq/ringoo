# FIX-PACK B — отмена заказов, FSM и резервы (B8-010)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**HEAD (до изменений pack):** `b3a9db4` на `main`  
**Production:** не затрагивался  
**Коммит:** не создавался  

---

## 1. Общая информация

Fix-pack B выполнен после READ-ONLY аудита FSM.  
Выбран **сценарий A**: при отмене правильный статус — `closed` + `closure_result=cancelled`.  
Дополнительно исправлен дефект Admin API: PATCH `status=cancelled` отклонялся ChoiceField до alias-маппинга.

---

## 2. Первопричина B8-010

| | |
|---|---|
| Тест ждал | `order.status == Order.STATUS_CANCELLED` (`"cancelled"`) |
| Фактически | `status == "closed"`, `closure_result == "cancelled"` |
| Где меняется | `cancel_order_and_release_stock()` → `Order.STATUS_CLOSED` + `CLOSURE_CANCELLED` (`apps/orders/services/__init__.py`) |
| Почему 200 | Отмена успешна; assert устарел относительно FSM v2 (migration `0012_order_status_v2_and_inbound`) |

`STATUS_CANCELLED = "cancelled"` в модели — **legacy-алиас** для чтения старых строк/`is_cancelled()`, не целевой write-статус после 0012.

---

## 3. Фактическая бизнес-логика

### 3.1 Статусы fulfillment

| Код | Смысл |
|---|---|
| `new` | Начальный |
| `processing` | В обработке (алиасы legacy: `confirmed`, `in_progress`) |
| `ready` | Готов к выдаче |
| `closed` | Терминальное закрытие; смысл задаёт `closure_result` |

**`closure_result`:**

| Значение | Смысл |
|---|---|
| `completed` | Заказ выполнен / получен |
| `cancelled` | Заказ отменён |

**Отмена ≠ отдельный `status=cancelled`.**  
Отмена = `closed` + `closure_result=cancelled`.  
`Order.is_cancelled()`, `display_status_code()` → `"cancelled"` для UI.

Оплата — отдельно: `payment_status` / `Payment`.

### 3.2 Таблица переходов (ALLOWED_TRANSITIONS)

| Исходный | Действие | Новый | Допустимо | Причина |
|---|---|---|---|---|
| new | взять в работу | processing | да | FSM |
| new | отмена / выдача | closed (+result) | да | FSM |
| processing | готов | ready | да | FSM |
| processing | отмена / выдача | closed (+result) | да | FSM |
| ready | выдача / (системная) отмена | closed (+result) | да | FSM |
| closed | любой | — | нет | терминальный |

Клиентская отмена дополнительно ограничена `customer_may_cancel_order`: только `new`/`processing`, не paid, не уже cancelled.

Запрещены: closed→processing/new; customer cancel из `ready`/paid/completed; чужой заказ; guest без валидного token.

### 3.3 Обоснование сценария A

Подтверждено кодом:

- `cancel_order_and_release_stock` docstring и реализация;
- `transition_order_status` / `_normalize_target("cancelled")`;
- migration 0012: `cancelled` → `closed`+`cancelled`;
- BLOCK 4 tests (`test_onec_block4_orders_locks`);
- FE: `status-labels.ts`, admin `updateOrderStatus` уже шлёт `closed`+`closure_result`.

---

## 4. Гостевая отмена

| | |
|---|---|
| Endpoint | `POST /api/v1/orders/{id}/cancel/` |
| Permission | `AllowAny` + throttle |
| Доступ | `guest_may_access_token` (SEC-006); phone+number **недостаточно** |
| Исход | `closed`/`cancelled`; release reserve; enqueue 1С cancel |
| Повтор | `customer_may_cancel_order` → 400 |
| Ответ | OrderSerializer: `status`, `closure_result`, `display_status=cancelled` |

---

## 5. Авторизованная отмена

| | |
|---|---|
| Endpoint | тот же `…/cancel/` |
| Доступ | `order.user_id == request.user.id` (staff без ownership → 403) |
| Admin | `PATCH /api/v1/admin/orders/{id}/` через `transition_order_status` |
| Admin alias | `status=cancelled` → closed+cancelled (**исправлено** в serializer) |
| Django admin | `OrderAdmin.save_model` → FSM |

---

## 6. Резервы

| Операция | Поведение |
|---|---|
| Создание заказа | reserve на Stock магазина (серия учитывается) |
| Отмена | `release_order_item_reservations` — только `reserved_quantity` |
| Завершение (`closed`/`completed`) | тот же release; **quantity не списывается** |
| Идемпотентность | ключ `release:order:{order}:item:{item}` |
| Повторная отмена | сервис no-op; user API 400; reserved не уходит в минус |
| Физический `quantity` | не меняется локально (источник — 1С) |

---

## 7. Изменённые файлы

| Файл | Что | Зачем |
|---|---|---|
| `backend/apps/admin_api/views/orders.py` | `status`/`closure_result` как CharField + alias validate | ChoiceField блокировал `cancelled`/`completed` до normalize |
| `backend/tests/order_fsm_assertions.py` | **новый** helper | Единый assert cancelled/not |
| `backend/tests/test_fix_pack_b_order_cancellation.py` | **новый** suite | Контракт FSM/guest/auth/reserves/series/admin |
| `backend/tests/test_sec006_*.py` и др. | Обновлены asserts | Соответствие FSM v2 (не «покраска») |
| `docs/audit/FIX_PACK_B_ORDER_CANCELLATION_REPORT.md` | отчёт | |

Тесты с правками asserts (Scenario A):  
`test_sec006`, `test_sec003`, `test_func002`, `test_func001`, `test_block8_refund_settlement`, `test_int004`, `test_sber_payments` (expire).

**Не менялись:** FSM transitions core, stock_ops reserve/release, guest_access, FE (уже корректен).

---

## 8. Тесты

| Набор | Результат |
|---|---|
| `tests/test_fix_pack_b_order_cancellation.py` | **9 passed** |
| `tests/test_sec006_guest_access_token.py` | **16 passed** (вкл. `test_valid_token_can_cancel`) |
| `tests/test_sec003_cancel_releases_stock.py` | **6 passed** |
| `tests/test_func002_func009_cancel_policy.py` | **7 passed** |
| `tests/test_func001_expire_yookassa_sync.py` | **7 passed** |
| `tests/test_block8_refund_settlement.py` | **7 passed** |
| `tests/test_int004_int005_yookassa_refund_metadata.py` | **16 passed** |
| `test_sber…expire_unpaid_releases_stock` | **1 passed** |
| `tests/test_fix_pack_a_guest_success.py` | **3 passed** |
| BLOCK 3 / 4 / 5 + `apps/orders/tests.py` | в общем прогоне |
| **Сводный прогон** | **145 passed**, 0 failed |

`django check`: OK. `makemigrations --check`: No changes.  
Frontend не менялся → tsc/eslint/build для FE в этом pack не требовались.

---

## 9. Регрессии

| Контур | Статус |
|---|---|
| BLOCK 3 series/cart | OK |
| BLOCK 4 orders/locks | OK |
| BLOCK 5 security | OK |
| Fix-pack A guest success | OK |
| SEC-006 | не ослаблен; cancel с token зелёный |

---

## 10. Оставшиеся проблемы / ограничения

- Реальная конкурентная отмена (два потока Postgres) — не гонялась в этом pack (`test_concurrency_postgres` при наличии Postgres отдельно).
- Django admin UI choices больше не содержат `cancelled` как отдельный status — отмена через FSM/alias API; legacy inline set в тестах всё ещё нормализуется.
- Прочие дефекты BLOCK 8 (B8-002, B8-004, …) — вне scope.
- Production deploy / migrate — не выполнялись.

---

## 11. Вердикт

**FIX-PACK B принят.**

- Семантика `closed` / `cancelled` установлена и задокументирована.  
- Guest + auth cancel проверены; SEC-006 сохранён.  
- Резервы: release идемпотентен, `quantity` не трогается.  
- `test_valid_token_can_cancel` проходит по контракту FSM v2.  
- Admin alias `status=cancelled` снова работает.  
- Production не затрагивался.

---

## 12. Рекомендации (дальше BLOCK 8)

1. **Fix-pack C** — Bearer refresh / session hint (B8-002, B8-006, B8-020).  
2. При наличии — Postgres concurrency suite для cancel.  
3. Controlled commit/release BLOCK 1–7 + Fix-packs A/B по отдельному разрешению.

---

**Fix-pack C самостоятельно не начат.**
