# BLOCK 6 — производительность и нагрузка Ringoo ↔ 1С

Дата: 2026-11-14  
Среда: локальные тесты (`config.settings.test`, SQLite). Production не затрагивался.

---

## 1. Исходное состояние (этап A, READ-ONLY)

После BLOCK 1–5 бизнес-логика снимка, серий, резервов и «Склад» корректна, но горячие пути имели измеримые издержки:

| Область | Наблюдение |
|---|---|
| Каталог | `ProductListView` prefetch'ил `stock_items`, но `ProductListSerializer.get_available_quantity_total` вызывал `Stock.available_quantity_retail` → **новый SQL на каждый товар** (+ повтор для `availability_status`) |
| PDP | Prefetch `stock_items` игнорировался: отдельно `aggregated_public_stock_for_product` + `available_quantity_retail` |
| Цвета/фото | `.filter()` / `ordered_product_images` сбрасывали prefetch |
| Корзина | Nested `ProductListSerializer` без prefetch stock → N+1 на наличие |
| `available_quantity_*` | Python-цикл по строкам Stock вместо SQL `Sum(Greatest(...))` |
| Импорт apply | Построчный `apply_onec_stock_upsert`: lookup movement + stock + `update_or_create` + `refresh` + `record_stock_movement` (savepoint) |
| Индексы | Unique `(product,store,series)`, индексы product/store/series, unique `idempotency_key` — достаточны; новых индексов без EXPLAIN на Postgres не добавляли |
| Транзакция снимка | Одна `@atomic` на apply (ONEC-014) — **не дробить** |

«Склад» / 9 складов / серии / idempotency / reconciliation — не менять.

---

## 2. Найденные узкие места (подтверждённые)

1. **N+1 наличия в каталоге/PDP/корзине** — prefetch не использовался.
2. **~14 SQL на одну строку upsert** (замер single-loop ×40) — неприемлемо на десятках тысяч позиций.
3. **Вложенные savepoint** на каждый `record_stock_movement` внутри большого apply.
4. XML parse держит дерево в памяти (`ET.fromstring`) — приемлемо для ~2k–10k тестовых строк; streaming не внедряли без смены контракта парсера.

---

## 3. Показатели до оптимизации

| Сценарий | Показатель | Значение |
|---|---|---|
| Каталог 24 товара ×5 складов ×3 серии | SQL (оценка по коду + паттерн N+1) | **~50+** запросов наличия поверх базовых |
| `apply_onec_stock_upsert` ×40 | SQL / row | **14.1** (замер: 562 queries / 40, ~292 ms) |
| Повторный тот же путь | — | тот же построчный профиль |

Замер «до» для каталога: serializer гарантированно игнорировал prefetch (`available_quantity_retail(obj.pk)`).  
Замер «до» для upsert: тест `test_single_upsert_query_cost` сохранён как baseline построчного API.

---

## 4. Что изменено

1. **Каталог / PDP / images / cart** — использование prefetch; `Prefetch(stock_items, store__is_active=True + select_related('store'))`; цвета без `.filter()`; `ordered_product_images` уважает prefetch; PDP availability из агрегированного stock без второго SQL.
2. **`available_quantity_retail` / `_at_store`** — SQL `Sum(Greatest(qty-reserved, 0))`.
3. **`apply_onec_stock_upserts_batch`** — prefetch movements/stocks, `bulk_create`/`bulk_update` Stock, `bulk_create` StockMovement; reserved не трогается; ключи `onec:{sha256}`; ONEC-024 failed→retry; UUID/str нормализация ключей.
4. **`apply_catalog_import`** — upsert + zero через batch **внутри той же atomic** (ONEC-014 сохранён).
5. Построчный `apply_onec_stock_upsert` оставлен для точечных вызовов/тестов.

Файлы: `stock_ops.py`, `stores/models.py`, `products/serializers.py`, `products/views.py`, `product_images.py`, `cart/views.py`, `importer.py`, `tests/test_onec_block6_performance.py`, `tests/test_onec_stock_reconciliation.py` (patch batch).

---

## 5. Показатели после оптимизации

| Сценарий | До | После |
|---|---|---|
| Каталог 24 / page_size=24 | ~50+ SQL | **5 SQL**, ~559 ms cold |
| PDP 9 складов ×3 серии | 2+ stock SQL сверх prefetch | **5 SQL** всего, ~29 ms |
| Upsert ×40 | **14.1 SQL/row** | batch **0.20 SQL/row** (8 queries / 40), ~24 ms |
| Idempotent re-batch ×40 | — | ≤10 SQL, applied=0 |

---

## 6. Результаты нагрузочных тестов

Фактически запущено (`tests/test_onec_block6_performance.py`):

| Объём | Результат | Время | Peak tracemalloc |
|---|---|---|---|
| Batch 1 000 stock rows | applied=1000 | ~1018 ms | ~2.1 MiB |
| Batch 5 000 stock rows | applied=5000 | ~5355 ms | ~9.3 MiB |
| XML plan dry-run 2 000 товаров | stocks≥2000 | ~8058 ms | ~3.6 MiB |

**10 000 / 50 000 / 100 000** полных apply на этой машине в CI-цикле **не гонялись** (время/объём SQLite). Экстраполяция с 5k (~1.07 ms/row batch): 10k ≈ 11 s, 50k ≈ 55 s, 100k ≈ 110 s CPU-bound на SQLite; на PostgreSQL ожидается лучше за счёт bulk, но **это оценка, не факт прогона**.

Конкурентный заказ↔импорт: отдельный stress не запускался; сохранены Redis-lock apply (BLOCK 4) и atomic снимка.

Регрессии: `test_onec_block6` + reconciliation/idempotency — **39 passed**; BLOCK3–5 + stores/cart/products/admin/guards — **112 passed**.

---

## 7. Использование памяти

- Batch 5k: peak ~9.3 MiB (tracemalloc, только Python-аллокации теста).
- XML plan 2k: peak ~3.6 MiB на этапе plan.
- Полный DOM XML на 50k–100k строк по-прежнему риск OOM парсера — **не решено** (нужен `iterparse` отдельным блоком).

---

## 8. SQL-запросы

| Операция | SQL |
|---|---|
| Catalog list 24 | 5 |
| Product detail | 5 |
| Single upsert ×40 | 562 (~14.1/row) — legacy path |
| Batch upsert ×40 | 8 (~0.20/row) |
| Batch idempotent replay ×40 | ≤10 |

Новые миграции индексов **не** добавлялись.

---

## 9. Риски для BLOCK 1–5

| Риск | Оценка |
|---|---|
| Idempotency / reserved / reconciliation | Низкий — покрыто тестами BLOCK1–2 + batch reserved test |
| Серии / «Склад» / 9 складов | Не менялись; BLOCK3/stores зелёные |
| Atomic полного снимка | Сохранена; batch внутри той же транзакции |
| Rollback mid-apply | Тест обновлён на patch batch |

---

## 10. Миграции

**Не нужны.**

---

## 11. Что осталось нерешённым

- Streaming/`iterparse` для XML 50k–100k.
- Реальный Postgres EXPLAIN + прогон 50k/100k apply.
- Конкурентный load-тест заказ+import (Locust/и т.п.).
- ONEC-014: по-прежнему одна длинная транзакция (осознанно).
- Построчный create/update Product в apply (не batch) — вторичный bottleneck при большом create.
- `unique_product_slug` / category slug — потенциальные exists-циклы при массовом create.

---

## 12. Вердикт: переход к BLOCK 7

**Да**, можно переходить к BLOCK 7 после прочтения отчёта.  
Production APPLY/migrate/restart — только по отдельному разрешению.  
К BLOCK 7 в этой сессии **не переходим**.
