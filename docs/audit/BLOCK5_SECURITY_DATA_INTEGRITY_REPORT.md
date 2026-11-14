# BLOCK 5 — безопасность и целостность складских данных

Дата: 2026-11-14  
Среда: локальные тесты (`config.settings.test`). Production не затрагивался.

---

## 1. Что обнаружено (сверка аудита ↔ код)

| Задача | Исходная проблема | Что сейчас в коде (до BLOCK 5) | Реальный риск | Требуемое исправление |
|---|---|---|---|---|
| ONEC-022 | Admin меняет Stock в обход ledger | Django `StockAdmin`/`StockInline` редактировали `quantity`/`reserved` без `StockMovement`. Admin API уже шёл через `apply_quantity_correction`, но разрешал ручной `reserved_quantity` | Высокий: рассинхрон с 1С, «тихое» изменение резерва | Readonly Django Admin; запрет ручного reserved; qty только через stock_ops |
| ONEC-012 | Публичный `StockListView` | `AllowAny`, без проверки `store.is_active`, без throttle, сырые строки (в т.ч. неактивные товары, серии). `reserved` в сериализаторе уже не отдавался. «Склад» должен оставаться публичным | Средний: утечка внутренних рядов/неактивных точек; не путать с устаревшим «скрыть warehouse» | 404 для неактивного store; только active products; агрегация серий; throttle; «Склад» оставить |
| ONEC-023 | `Product.delete` → CASCADE Stock | `Stock.product` = `CASCADE`; Admin API `delete()` вызывал hard-delete → потеря остатков/резервов. `StockMovement.product` = `SET_NULL` (история частично переживала) | Высокий при случайном удалении | `PROTECT` + архивация (`is_active=False`); hard-delete только без Stock/onec |

### Не применять из старого аудита
- Исключение `is_warehouse=True` из публичных остатков / списка магазинов.
- Параллельная «вторая» система остатков вне `stock_ops`.

---

## 2. Уже было исправлено ранее (BLOCK 1–4)

- Idempotency `onec:{sha256}` без qty; ONEC-024 retry.
- Reconciliation полного снимка + 9 складов; запрет автосоздания Store.
- price_blocked: остатки existing обновляются.
- Агрегация серий (ONEC-010), serial+blank reserve (ONEC-009).
- reserved>qty diagnose; release при completed/cancelled; CLI Redis-lock.
- «Склад» — полноценная точка (`is_warehouse` только UI).

---

## 3. Что изменено сейчас

1. **ONEC-022** — Django Admin: `StockAdmin`/`StockInline` только просмотр; add/delete запрещены. Admin API: `reserved_quantity` readonly (403); `quantity` для non-onec через `apply_quantity_correction` + `StockMovement`; onec qty по-прежнему 403.
2. **ONEC-012** — `StockListView`: активный store (404 иначе), только active products, агрегация по товару, throttle; «Склад» включён. Публичные поля без `reserved` / seriesId.
3. **ONEC-023** — `Stock.product` → `PROTECT`; `safe_delete_or_archive_product`: DELETE → deactivate; hard-delete только локальный товар без Stock/onec; Django `ProductAdmin` блокирует delete при риске.

Устаревший тест `test_store_warehouse_fields_and_public_exclusion` заменён на inclusion (соответствует BLOCK 2+).

---

## 4. Файлы

- `backend/apps/stores/admin.py`
- `backend/apps/stores/models.py` (`PROTECT`, `aggregated_public_stock_for_store`)
- `backend/apps/stores/views.py` (`StockListView`)
- `backend/apps/stores/migrations/0009_stock_product_protect.py`
- `backend/apps/admin_api/views/stock.py`
- `backend/apps/admin_api/views/products.py`
- `backend/apps/products/admin.py`
- `backend/apps/products/services/lifecycle.py` (новый)
- `backend/tests/test_onec_block5_security_integrity.py` (новый)
- `backend/tests/test_admin_integrity.py` (warehouse inclusion)
- `docs/audit/BLOCK5_SECURITY_DATA_INTEGRITY_REPORT.md`

---

## 5. Тесты и результаты

```text
tests/test_onec_block5_security_integrity.py
tests/test_admin_integrity.py
tests/test_onec_block4_orders_locks.py
tests/test_onec_block3_series_cart.py
tests/test_onec_stock_idempotency.py
tests/test_onec_stock_reconciliation.py
apps/stores/tests.py
tests/test_int001_int002_order_fsm.py
tests/test_onec_inbound_order_status.py
tests/test_block8_catalog_guards.py
tests/test_int009_stock_ledger_complete.py
```

**Результат основной связки BLOCK1–5 + stores: 95 passed.**  
**Дополнительно FSM/inbound/guards/ledger: 30 passed.**

Покрыто: Admin readonly; reserved 403; correction→movement; anon/auth/staff store stock; warehouse public; inactive store 404; Product deactivate; PROTECT; empty local hard-delete.

---

## 6. Оставшиеся риски

- Admin API по-прежнему может править `quantity` у **локальных** (без `onec_code`) товаров — осознанно, через ledger.
- Hard-delete локального товара без Stock всё ещё возможен; wishlist/reviews с CASCADE на Product не менялись.
- Миграция `0009` на production **не применялась** в этой сессии.
- ONEC-014 (длинная atomic импорта) — по-прежнему отложено (BLOCK 4).

---

## 7. Миграции

**Да, локально подготовлена:** `stores/0009_stock_product_protect.py`  
Назначение: `Stock.product` `CASCADE` → `PROTECT`, чтобы БД не давала стереть остатки/резервы при удалении Product.

На production не запускать без отдельного разрешения.

---

## 8. Регрессия BLOCK 1–4

Не нарушена: idempotency, reconciliation, 9 складов, серии/cart, completed/cancel release, Redis-lock, «Склад» в наличии — подтверждены прогоном тестов BLOCK 3–4 + stores + block guards.

---

## 9. Вердикт: переход к BLOCK 6

**Да**, можно переходить к BLOCK 6 после прочтения этого отчёта.  
Production APPLY / migrate / импорт — только по отдельному разрешению.  
К следующему блоку в этой сессии **не переходим**.
