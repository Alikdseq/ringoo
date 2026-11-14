# BLOCK 3 — серии, корзина, агрегация, reserved>qty

Дата: 2026-11-14  
Среда: локальные тесты (`config.settings.test`). Production не затрагивался.

---

## 1. Сверка аудита ↔ актуальные решения ↔ код

| Задача | Исходный аудит | Актуальное решение | Состояние до BLOCK 3 | Что сделано |
|---|---|---|---|---|
| BLOCK 1 idempotency | qty в ключе | ключ без qty + ONEC-024 | Уже реализовано | Не трогали |
| BLOCK 2 map 9 складов | whitelist + tech | 9 mapping, «Склад» полноценная точка | Уже реализовано | Не трогали |
| BLOCK 2 reconciliation | full snapshot zero | seen_keys + zero-phase | Уже реализовано | Не трогали |
| price_blocked | split stock/card | existing stock upsert | Уже реализовано | Не трогали |
| ONEC-011 warehouse exclude | exclude `is_warehouse` | **устарело**: «Склад» участвует | Уже исправлено | Подтверждено тестами |
| ONEC-008 cart MultiGet | `.get(product,store)` 500 | aggregate available | Cart уже на `available_quantity_retail` | Тесты multi-series |
| ONEC-009 serial vs blank | zero serial блокирует blank | serial только с available>0 + blank remainder | **Баг** | Исправлен `plan_and_reserve_at_store` |
| ONEC-010 UI/API series | last-wins / дубли | одна точка, sum available | **Баг** API+FE | Aggregate API + FE |
| ONEC-018 series without id | collapse / silent | blocker if series name w/o id; blank OK | Уже blocker | Тесты |
| ONEC-004 reserved>qty | alert, no auto-cut | diagnose report_only | Не хватало diagnose | `diagnose_reserved_over_quantity` |

### Не применять из старого аудита
- Исключение `is_warehouse=True` из наличия/самовывоза.
- Автосоздание неизвестных Store.
- Обнуление резерва при импорте.

### BLOCK 1/2 — завершено (подтверждено)
Idempotency без qty, reconciliation, карта 9 складов, запрет unknown warehouse, «Склад» как полноценная точка, price≠stock для existing.

---

## 2. Исправлено в BLOCK 3

1. **ONEC-009** — `plan_and_reserve_at_store`: серийная ветка только при `available>0`; остаток из blank-series; смесь serial+blank.
2. **ONEC-010** — `Stock.aggregated_public_stock_for_product`; ProductStockView; ProductDetailSerializer.stock; FE PDP + StoresContent.
3. **ONEC-008** — подтверждён cart на агрегатах + тесты ≥2 серии.
4. **ONEC-011** — подтверждение «Склад» + `is_warehouse` в StorePageSerializer.
5. **ONEC-018** — тесты: series без seriesId → blocker; обычный товар без серии → OK.
6. **ONEC-004** — `diagnose_reserved_over_quantity`; счётчик в результате apply; CLI diagnose расширен; тесты import qty&lt;reserved и restock.

---

## 3. Изменённые файлы

- `backend/apps/stores/models.py` — `aggregated_public_stock_for_product`
- `backend/apps/stores/views.py` — ProductStockView.list агрегация
- `backend/apps/stores/serializers.py` — `is_warehouse` в StorePageSerializer
- `backend/apps/products/serializers.py` — stock агрегат
- `backend/integrations/onec/orders.py` — reserve serial/blank
- `backend/integrations/onec/importer.py` — diagnose reserved + apply stats
- `backend/apps/products/management/commands/diagnose_onec_stock_series.py`
- `frontend/.../ProductPageClient.tsx` — sum by store
- `frontend/.../StoresContent.tsx` — sum by store
- `backend/tests/test_onec_block3_series_cart.py` — новый
- `docs/audit/BLOCK2_...` — устаревшая строка про inactive склад
- `docs/audit/BLOCK3_SERIES_CART_REPORT.md` — этот отчёт

---

## 4. Тесты

Новый: `tests/test_onec_block3_series_cart.py` (cart multi-series, reserve blank/serial, API aggregate, warehouse, seriesId, reserved>qty).

Прогон: `114 passed, 1 skipped`  
(`test_onec_block3_series_cart`, `test_onec_orders`, stores/cart/orders, reconciliation).

Frontend lint/typecheck/build в этой сессии **не запускались** (фокус backend + точечный FE).

---

## 5. Миграции

**Не требуются.**

---

## 6. Риски для BLOCK 1/2

Низкие: reconciliation/idempotency/warehouse map не менялись. Reserve path расширен совместимо (serial-only сценарии сохранены).

---

## 7. Точка «Склад»

Сохранена: active, в наличии, корзина, заказ/самовывоз, метка UI, sync в confirmed map.

---

## 8. Нерешённое (не BLOCK 3)

- ONEC-002/003 и др. (закрытие заказа / release policy) → BLOCK 4+
- CLI apply lock (ONEC-013), батчинг транзакции (ONEC-014)
- Полный frontend CI suite

---

## 9. Вердикт: переход к BLOCK 4

**Да**, после staging DRY-RUN каталога (не production). BLOCK 3 по коду и релевантным тестам закрыт.
