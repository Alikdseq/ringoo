# BLOCK 4 — заказы, резервы, блокировки и транзакции

Дата: 2026-11-14  
Среда: локальные тесты (`config.settings.test`). Production не затрагивался.

---

## 1. Сверка задач

| Задача | Исходная проблема | Текущее состояние до BLOCK 4 | Что требуется / сделано |
|---|---|---|---|
| ONEC-002 | Truncate idempotency key → коллизии | Уже закрыто в BLOCK 1: `onec:{sha256}` длина 69, ValueError при >128 | Подтверждено тестом; код не меняли |
| ONEC-003 | `closed/completed` не снимает резерв | Cancel снимал резерв; **completed только менял статус** | Release при completed без локального OP_DEDUCTION (1С SoT quantity) |
| ONEC-013 | CLI `apply_catalog_import` в обход lock | Admin/Celery/Beat → `run_catalog_import` + Redis lock; CLI обходил | CLI переведён на `run_catalog_import` |
| ONEC-014 | Длинная atomic на весь apply | Одна `@transaction.atomic` на upsert+zero | **Оставлено**: иначе partial snapshot; риск задокументирован |

### Правило списания (зафиксировано по коду + аудиту)

| Событие | reserved | quantity |
|---|---|---|
| Создание заказа | +reserve | без изменений |
| `closed` + `cancelled` | release (идемпотентно) | без изменений |
| `closed` + `completed` | release (идемпотентно) | без изменений локально |
| Sync 1С после выдачи | не трогает reserved | пишет актуальный физический qty |

Локальный `OP_DEDUCTION` **не** вызывается: физика остатка — из полного снимка 1С.

---

## 2. Уже было до BLOCK 4

- BLOCK 1: idempotency без qty, ONEC-024 retry  
- BLOCK 2: 9 складов, reconciliation, «Склад» полноценная точка  
- BLOCK 3: серии/cart/aggregate/reserved>qty diagnose  
- Cancel → `release_order_item_reservations`  
- `run_catalog_import` lock для Admin/Celery  

---

## 3. Изменения BLOCK 4

1. **ONEC-003:** `transition_order_status` при `completed` вызывает release; повтор completed/cancelled — идемпотентный release по ключу `release:order:{id}:item:{id}`.
2. **ONEC-013:** `import_onec_catalog` только через `run_catalog_import` (lock + SyncLog).
3. **ONEC-014:** без дробления транзакции; комментарий в `apply_catalog_import`.
4. **ONEC-002:** verification only.

---

## 4. Файлы

- `backend/apps/orders/services/transitions.py`
- `backend/apps/orders/services/__init__.py`
- `backend/integrations/onec/orders.py` (`release_order_item_reservations`)
- `backend/apps/products/management/commands/import_onec_catalog.py`
- `backend/integrations/onec/importer.py` (комментарий ONEC-014)
- `backend/tests/test_onec_block4_orders_locks.py` (новый)
- `docs/audit/BLOCK4_ORDERS_LOCKS_TRANSACTIONS_REPORT.md`

---

## 5. Тесты

Запуск:

```text
tests/test_onec_block4_orders_locks.py
tests/test_int001_int002_order_fsm.py
tests/test_onec_inbound_order_status.py
tests/test_onec_sync_log.py
tests/test_onec_stock_idempotency.py
tests/test_onec_stock_reconciliation.py
tests/test_onec_block3_series_cart.py
```

**Результат: 82 passed.**

Покрыто: completed→reserved=0/qty неизменен; повтор completed; cancel; CLI lock; длина ключа 69.

---

## 6. Нерешённое

- Батчинг/короткие транзакции импорта (ONEC-014) — отложено до роста объёма + протокола safe partial apply.
- ONEC-015+ и прочие пункты аудита вне BLOCK 4.
- Полный suite frontend / полный pytest всего репо в этой сессии не гонялись.

---

## 7. Миграции

**Не нужны.**

---

## 8. Риски для BLOCK 1–3

Низкие. Reconciliation/idempotency/серии/«Склад» не менялись.  
Completed теперь снимает резерв — после выдачи sync 1С не должен оставлять «залипший» reserved (главный риск ONEC-003 закрыт).

---

## 9. Вердикт: переход к BLOCK 5

**Да**, можно переходить к BLOCK 5 после прочтения этого отчёта.  
Production APPLY / migrate / импорт — по-прежнему только по отдельному разрешению.
