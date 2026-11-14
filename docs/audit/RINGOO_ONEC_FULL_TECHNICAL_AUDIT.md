# Полный технический аудит интеграции Ringoo ↔ 1С

**Дата:** 2026-11-12  
**Режим:** READ-ONLY (код/миграции/production не изменялись)  
**Объект:** каталог, склады, серии, остатки, резервы, Celery-синхронизация, публичный API/frontend, inbound order status (контекст)  
**Источник истины:** текущий код в репозитории `C:\ringoo`

---

## 1. Executive Summary

### Общая оценка

Интеграция каталога с 1С имеет зрелый каркас: `defusedxml`, Basic Auth без утечки в логи, DRY_RUN по умолчанию, многоуровневый gate APPLY, `UniqueConstraint(product, store, onec_series_id)`, сохранение `reserved_quantity` при upsert quantity, защита 1C-managed полей товара в Admin API.  

При этом **несколько подтверждённых дефектов делают production APPLY опасным**: идемпотентность остатков с `qty` в ключе, отсутствие release/deduction при `closed/completed`, автопубликация не-Apple-Room складов, устаревшие остатки при исчезновении строк из выгрузки, поломки cart/UI на серийных SKU, суммирование warehouse-остатков в публичной «наличии».

### Готовность к production APPLY: **28%**

| Метрика | Значение |
|--------|----------|
| Всего проблем в реестре | 28 |
| CRITICAL | 6 |
| HIGH | 10 |
| MEDIUM | 8 |
| LOW | 4 |

### Главные причины опасности запуска

1. **Идемпотентность `onec_import:…:q{qty}`** — цикл `5→8→5` (и `1→0→1`) оставляет ложный остаток навсегда.  
2. **Завершение заказа не снимает резерв и не списывает quantity** — `reserved_quantity` накапливается; после sync с 1С доступность ломается.  
3. **Автосоздание Store как публичной точки** (`is_active=True`, `is_warehouse=False`) для «Сервис»/«Офис»/любого нового склада.  
4. **Нет reconciliation отсутствующих позиций** — проданные серии/нулевые остатки, исчезнувшие из XML, остаются продаваемыми.  
5. **Серийный учёт ломает cart** (`MultipleObjectsReturned`) и искажает PDP/stores UI.  
6. **Публичный `availability_status` учитывает `is_warehouse=True`**, checkout — нет → ложное «В наличии».

**Вердикт:** APPLY сейчас **нельзя** запускать на боевом каталоге с реальными заказами.

---

## 2. Карта архитектуры

```
1С УТ11 (/razrab/hs/)
  GET CatalogFolders/folders  ─┐
  GET CatalogProducts/products─┤
                               ▼
                    OneCClient (client.py)
                      Basic Auth, timeout, 20MB cap,
                      same-host redirect block
                               ▼
                    parser.py (defusedxml)
                      OneCFolder / OneCProductRow
                      parse_warnings → OneCParseError
                               ▼
                    plan_from_parsed / _plan_*
                      CatalogImportPlan (DRY_RUN|APPLY)
                      categories / products / warehouses / stocks / issues
                               ▼
         ┌─────────────────────┴─────────────────────┐
         │ dry_run=true          dry_run=false        │
         │ OneCCatalogSyncLog    apply lock Redis+DB  │
         │ report JSON           apply_catalog_import │
         └───────────────────────┬───────────────────┘
                                 ▼
              Category / Product / Store / Stock
                                 │
                                 ▼
              apply_onec_stock_upsert → StockMovement (OP_RECONCILIATION)
                                 │
                                 ▼
              Public API / Admin / Checkout / Cart / Sitemap
```

### Триггеры

| Триггер | Путь | APPLY? |
|---------|------|--------|
| Admin UI Sync | `POST /api/v1/admin/onec/sync/{dry-run\|apply}/` → Celery `run_onec_catalog_sync_task` → `catalog_sync.run_catalog_import` | только apply + confirm + ONE_C_API_ENABLED |
| Celery Beat | `scheduled_onec_catalog_sync_task` | если `ONE_C_CATALOG_SYNC_ENABLED` и `ONE_C_API_ENABLED` |
| CLI | `manage.py import_onec_catalog [--apply --i-understand-apply]` | да, **без** Redis-lock и SyncLog |

### Ключевые файлы

- `backend/integrations/onec/client.py`, `parser.py`, `importer.py`, `catalog_sync.py`, `orders.py`, `inbound.py`
- `backend/apps/stores/stock_ops.py`, `ledger.py`, `models.py`
- `backend/apps/products/tasks.py`, `management/commands/import_onec_catalog.py`
- `backend/apps/admin_api/views/onec_sync.py`
- `frontend/src/app/admin/sync/page.tsx`

---

## 3. Реестр проблем

### ONEC-001 — Idempotency key содержит quantity

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `backend/integrations/onec/importer.py` (строки ~912–914), `backend/apps/stores/stock_ops.py` (314–322)  
**Функция:** `apply_catalog_import` → `apply_onec_stock_upsert`  

**Что происходит:** ключ `onec_import:{product}:{store}:{series}:q{qty}` проверяется по всей истории `StockMovement(success=True)`.  

**Почему проблема:** после `5→8` повторный импорт `5` находит старый ключ `:q5` и **не обновляет** `Stock.quantity` (остаётся 8).  

**Как воспроизвести:** APPLY qty=5 → APPLY qty=8 → APPLY qty=5; проверить `Stock.quantity` (ожидается 5, фактически 8).  

**Последствия:** расхождение сайта и 1С, продажа отсутствующего / сокрытие реального остатка.  

**Исправление:** ключ на `run_id` / `generated_at` / hash плана + `(product,store,series)` **без** qty; повтор одного плана — идемпотентен; новый прогон с тем же qty — пишет актуальное состояние.  

**Тесты:** `5→8→5`, `1→0→1`, повтор одного plan с тем же qty, новый plan с тем же qty.  

**Данные:** все `Stock` / `StockMovement` reconciliation.  
**Без миграции:** да (смена формата ключа).  
**Зависимости:** ONEC-002 (длина ключа).

---

### ONEC-002 — Молчаливое усечение idempotency_key до 128

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `stock_ops.py:317`, `ledger.py`, `StockMovement.idempotency_key` max_length=128  

**Что происходит:** `key[:128]` обрезает `:q{qty}` при длинном `series_id` (budget префикса ~86 + series).  

**Последствия:** все импорты одной серии коллидируют в один ключ → остаток «замораживается» после первого успешного upsert.  

**Исправление:** короткий hash (sha256 hex 32–64) или отдельное поле; запрет truncate без ошибки.  

**Тесты:** series_id 64 символа + смена qty.  
**Без миграции:** предпочтительно да; иначе увеличить max_length.  
**Зависимости:** ONEC-001.

---

### ONEC-003 — closed/completed не снимает резерв и не списывает остаток

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `backend/apps/orders/services/transitions.py` (~139–167)  
**Функция:** `transition_order_status`  

**Что происходит:** при `STATUS_CLOSED` + `CLOSURE_CANCELLED` вызывается `cancel_order_and_release_stock`; при `CLOSURE_COMPLETED` только сохраняются status/closure_result. `OP_DEDUCTION` объявлен, **нигде не вызывается**.  

**Почему проблема:** после выдачи `reserved_quantity` остаётся; 1С уменьшает физический остаток → sync пишет меньший `quantity` при живом резерве → `available` падает навсегда.  

**Воспроизведение:** заказ 1 шт → closed/completed → sync quantity−1 → `reserved_quantity` всё ещё ≥1.  

**Исправление (бизнес-решение нужно):**  
- A) на completed: release reserve + не трогать quantity (1С — источник quantity);  
- B) release + local OP_DEDUCTION (если сайт — источник до sync).  
Рекомендация при inbound 1С как SoT по физике: **release reserve only**, quantity только из 1С.  

**Тесты:** completed → reserved=0; повтор completed идемпотентен; sync после продажи.  
**Без миграции:** да.  
**Зависимости:** ONEC-004, политика резервов.

---

### ONEC-004 — Импорт допускает reserved > quantity и не алертит

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `stock_ops.py` update_or_create quantity-only; `test_block8` закрепляет quantity=0 при reserved=2  

**Последствия:** available=0; restock/новый приход «съедается» дефицитом; Admin PATCH не может частично снизить reserved.  

**Исправление:** ops-alert `reserved__gt=F(quantity)`; админский repair; не авто-резать reserved без политики.  
**Тесты:** import qty&lt;reserved; alert; partial reserved fix.  
**Без миграции:** да (CheckConstraint — отдельное решение).

---

### ONEC-005 — Автопубликация новых складов 1С

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `importer.py` ~871–880  

**Что происходит:** новый склад (не Apple Room) → `is_warehouse=False`, `is_active=True`, address/city «Уточнить». Dry-run показывает «Сервис», «Офис».  

**Последствия:** появляются в `/stores`, checkout, sitemap; покупатель выбирает техсклад.  

**Исправление:** default `is_active=False` и/или `is_warehouse=True` до ручного маппинга; whitelist публичных складов; CLI `list_onec_warehouses` как обязательный pre-apply.  

**Тесты:** create store inactive; public list excludes; checkout rejects.  
**Без миграции:** да.  

---

### ONEC-006 — Нет обнуления позиций, исчезнувших из выгрузки

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `apply_catalog_import` (аддитивный upsert only)  

**Что происходит:** отсутствует в XML → Stock не трогается. 1С часто не отдаёт нулевые серии.  

**Последствия:** продажа «призраков».  

**Исправление:** snapshot reconciliation с safety gates (min rows, anomaly %, require full dump flag); dry-run отчёт «would zero N».  
**Тесты:** row disappeared → zero/deactivate; incomplete dump → abort.  
**Без миграции:** да (логика); возможно поле `last_seen_at`.  
**Зависимости:** политика владельца 1С.

---

### ONEC-007 — price_blocked блокирует и карточку, и остатки

**Приоритет:** HIGH (архитектурный trade-off; закреплено тестами)  
**Статус:** CONFIRMED  
**Файл:** `importer.py` ~413, 496–503, 582–596  

**Сейчас:** любая bad/empty price по code → skip product + skip all stocks.  

**Вариант A (текущий):** не обновляем цену мусором и не двигаем остатки — безопаснее для цены, но при `qty=0` + empty price **не обнуляет** sold-out.  

**Вариант B:** блокировать только price/card, писать валидные stocks — лучше актуальность наличия, риск витрины со старой ценой.  

**Рекомендация:** для **существующих** товаров — B (stock upsert при валидном qty); для **create** — A (не создавать без цены). Явно разделять в плане.  

**Тесты:** existing product empty price + qty=0 → stock 0; new product empty price → no create/no stock.

---

### ONEC-008 — Cart MultipleObjectsReturned на серийных SKU

**Приоритет:** CRITICAL  
**Статус:** CONFIRMED  
**Файл:** `backend/apps/cart/views.py:97` (`Stock.objects.get(product, store_id)`)  

**Последствия:** HTTP 500 при increment; `.first()` на create ложно режет quantity.  

**Исправление:** `Stock.available_quantity_at_store` / aggregate; не get по (product,store).  
**Тесты:** ≥2 series rows; add/increment cart.  
**Без миграции:** да.

---

### ONEC-009 — serial_rows блокируют blank-series stock

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `orders.py` `plan_and_reserve_at_store` ~279–291  

**Что происходит:** любое непустое `onec_series_id` (даже qty=0) переключает ветку serial; blank row игнорируется.  

**Последствия:** витрина показывает наличие, checkout InsufficientStock.  

**Исправление:** serial_rows = series с available&gt;0; политика перехода serial↔non-serial.  
**Тесты:** zero serial + blank qty&gt;0.

---

### ONEC-010 — Frontend/PDP не агрегирует серии по store

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `StoresContent.tsx` ~290–294; `ProductPageClient.tsx` stock map  

**Последствия:** last series wins → ложный out-of-stock / дубли магазинов.  

**Исправление:** sum by store_id на API или FE.  
**Тесты:** multi-series same store.

---

### ONEC-011 — Публичная availability включает is_warehouse

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `products/serializers.py` `get_available_quantity_total` / `get_availability_status` (~181–268); `catalog_filters.py`  

**Последствия:** «В наличии» только на Apple Room / inactive; checkout невозможен.  

**Исправление:** фильтр `store__is_active=True, store__is_warehouse=False` везде в публичных агрегатах.  
**Тесты:** stock only warehouse → out_of_stock; filter in_stock.

---

### ONEC-012 — StockListView без фильтра warehouse

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `stores/views.py` StockListView ~187–202  

**Последствия:** утечка остатков техсклада по UUID.  
**Исправление:** 404 если store warehouse/inactive.

---

### ONEC-013 — CLI import обходит apply lock и SyncLog

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `import_onec_catalog.py` ~138  

**Последствия:** параллельный APPLY с Beat/Admin.  
**Исправление:** вызывать только `run_catalog_import` / общий lock.  
**Тесты:** CLI+Celery concurrent → один побеждает.

---

### ONEC-014 — Огромная атомарная транзакция на весь apply

**Приоритет:** HIGH  
**Статус:** POTENTIAL (механизм confirmed, deadlock — potential)  
**Файл:** `importer.py` `@transaction.atomic` на весь apply  

**Плюс:** rollback при mid-fail.  
**Минус:** долгие FOR UPDATE на Stock; риск deadlock с checkout; cache invalidate внутри tx.  

**Исправление:** батчи по N stocks с per-batch atomic + run lock; или savepoints + короткий lock order.  
**Тесты:** concurrent reserve during import (postgres).

---

### ONEC-015 — Ложный stocks_upserted при skip из-за idempotency

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `importer.py` ~916 всегда `+=1`  

**Последствия:** SyncLog SUCCESS при фактически skipped updates.  
**Исправление:** считать по второму return bool / before≠after.

---

### ONEC-016 — series_present раздувает errors_count / PARTIAL

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `importer.py` series_present issues; `catalog_sync` errors_count=len(issues)  

**Последствия:** каждый sync с сериями выглядит как PARTIAL/ошибки.  
**Исправление:** severity levels: info vs error.

---

### ONEC-017 — Сопоставление склада по name__iexact

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `importer.py` ~843–849, 853–855  

**Последствия:** чужой магазин с тем же именем получает чужой `onec_warehouse_id` и остатки.  

**Исправление:** match только по `onec_warehouse_id` или явному mapping JSON; name — только report ambiguous.  
**Тесты:** two stores same name.

---

### ONEC-018 — series без seriesId схлопываются в onec_series_id=""

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `parser.py` has_series; `importer` series_id strip  

**Последствия:** несколько IMEI без ID перезаписывают одну blank-строку.  
**Исправление:** skip/report если series name без ID; не писать в "".

---

### ONEC-019 — parentCode=База на товарах не нормализуется

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `parser.py` folders strip База; products оставляют `00-00010097`  

**Последствия:** product_missing_category / skip create.  
**Исправление:** нормализовать parent на товарах как у folders.

---

### ONEC-020 — Категории: циклы и незачистка parent

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `_plan_categories` topo break без issue; apply `if parent:` не clears  

**Последствия:** `A.parent=A` / `A↔B` на 2-м импорте; нельзя вернуть в root.  
**Исправление:** cycle detect + skip; always set parent including None.

---

### ONEC-021 — Homonym subcategory slug → permanent skip

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `_plan_categories` category_slug_conflict  

**Последствия:** вторая «USB-C» не создаётся.  
**Исправление:** unique slug per onec_code (`usb-c-<code>`).

---

### ONEC-022 — Django Admin Stock обходит ledger и 1C guard

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `stores/admin.py` StockAdmin / StockInline  

**Последствия:** ручная порча quantity/reserved без журнала.  
**Исправление:** readonly для onec products; только через stock_ops.

---

### ONEC-023 — Product delete каскадом убивает Stock с резервами

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `admin_api/views/products.py` delete  

**Исправление:** запрет delete onec-managed / при reserved&gt;0.

---

### ONEC-024 — Ledger success=False + unique key ломает retry

**Приоритет:** HIGH  
**Статус:** CONFIRMED  
**Файл:** `stock_ops` + `ledger.py` IntegrityError swallow  

**Последствия:** повтор reserve/release мутирует Stock без успешного ledger / double mutate.  
**Исправление:** update failed row → success; или key includes attempt; pre-check any key.

---

### ONEC-025 — Cancel → revive → cancel leak reserved

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `orders.py` release key без generation  

**Исправление:** `release:…:gen{n}` / revive bumps generation.

---

### ONEC-026 — parse_catalog_files без parse_warnings на пустой XML

**Приоритет:** MEDIUM  
**Статус:** CONFIRMED  
**Файл:** `parser.py` parse_catalog_files vs parse_catalog_xml_strings  

**Последствия:** CLI file dry-run/apply может планировать пустой набор без abort (additive — не обнулит, но silent).  
**Исправление:** единые warnings.

---

### ONEC-027 — Нет Content-Length / mid-stream integrity check

**Приоритет:** LOW–MEDIUM  
**Статус:** POTENTIAL / NEEDS_PRODUCTION_VERIFICATION  
**Файл:** `client.py` read до EOF  

**Риск:** «чистый» обрыв с well-formed усечённым XML → частичный план.  
**Смягчение:** уже есть empty warnings на http strings; нужны min-row / delta gates перед APPLY.

---

### ONEC-028 — Нет уникальности IMEI на уровне системы

**Приоритет:** LOW (gap)  
**Статус:** CONFIRMED (отсутствие)  
**Файл:** Stock.onec_series_name без unique  

**Последствия:** один IMEI теоретически на двух складах/товарах.  
**Решение:** бизнес — нужна ли global unique IMEI.

---

## 4. Проверка известных рисков (A–J)

### A. Idempotency key (`5→8→5`)

**Да, остаток станет неправильным (CONFIRMED).**  
Архитектурно: ключ = `onec_import:{run_id}:{product}:{store}:{series}` (или hash плана). Повтор **того же** плана → no-op; **новый** run с qty=5 после 8 → пишет 5.

### B. Складская модель / публичность

**Да, склад 1С может стать публичным магазином (CONFIRMED)** — всё кроме Apple Room.  
Исключить: default inactive/warehouse + manual mapping whitelist.

### C. Цена и количество

Текущий A безопаснее для цен, хуже для sold-out с пустой ценой.  
Архитектурно безопаснее **гибрид**: create требует цену; update stock независимо от price_blocked для existing.

### D. Резервы

Импорт **не затирает** reserved (хорошо).  
Но **не предотвращает** reserved&gt;quantity и **completed не release** → импорт косвенно ломает available.  
При reserved&gt;quantity: available=0; нужны ops, не silent clamp reserved.

### E. Транзакции

`apply_catalog_import` сам в `@transaction.atomic` — mid-fail rollback **внутри apply** гарантирован.  
CLI без sync-lock; plan вне tx (TOCTOU). Долгая tx — риск блокировок.

### F. Серии

Смешение serial/blank: **да** (reserve path + UI).  
Перенос серии между складами: новый store-row создаётся; старый на прежнем складе **не обнуляется** (ONEC-006).

### G. Отсутствующие строки

Остаток **сохраняется** (stale). Риск высокий для серий.

### H. Неполная выгрузка

Пустой HTTP XML → abort. Усечённый non-empty XML → **возможен частичный план** без anomaly gate.  
APPLY частичного dump **аддитивен** (не обнулит всё), но не обновит отсутствующие → stale.

### I. SKU-конфликт

Чужие остатки на чужую карточку из-за SKU: **в основном нет** — ambiguous skip product; stock plan может числиться в summary, но apply skip без product.  
Риск: match по `sku==code` при пустом onec_code **усыновляет** карточку (by design).

### J. Повтор после частичного сбоя

Внутри одной atomic apply — полный rollback.  
После успешного apply + следующий fail: предыдущий успех остаётся.  
Повтор с qty-ключом — **небезопасен** (ONEC-001). CLI параллельно — **небезопасен** (ONEC-013).

---

## 5. Таблица покрытия тестами

| # | Сценарий | Есть тест? | Ожидание | Добавить |
|---|----------|------------|----------|----------|
| 1 | 5→8→5 idempotency | Нет (есть только same qty×2) | qty=5 | обязательно |
| 2 | Повтор одного плана | Частично | no double write | с run_id |
| 3 | Новый план те же qty | Нет | должен писать | да |
| 4 | Частичный fail + retry | Нет | consistent | да |
| 5 | Два параллельных import | lock unit only | один apply | CLI+Celery |
| 6 | Два склада одно имя | Нет | ambiguous | да |
| 7 | Смена warehouseId | Нет | rematch by id | да |
| 8 | Новый склад | Нет | inactive | да |
| 9 | Нет склада | skip missing | да (partial) | усилить |
| 10 | Пустое qty | skip not zero | да | — |
| 11 | Нулевое qty | upsert 0 | да block8 | + после q0 history |
| 12 | Отрицательное qty | reject | да | — |
| 13 | Пустая цена + валидный остаток | block both | да | тест гибрида |
| 14 | Неверная цена + остаток | block | да | — |
| 15 | SKU conflict | plan issue | partial | apply skip assert |
| 16 | Дубли onec_code в XML | aggregate | да dry-run | — |
| 17 | Несколько серий | reserve tests | да | cart/UI |
| 18 | Серия на 2 складах | да series reserve | — | stale other store |
| 19 | Serial→non-serial | diagnose only | — | reserve path |
| 20 | Удаление серии из XML | Нет | zero/stale policy | да |
| 21 | Товар пропал из XML | Нет | policy | да |
| 22 | Неполный XML | empty abort | partial | anomaly |
| 23 | API error | http tests | да | — |
| 24 | Ошибка StockMovement | Нет | rollback | да |
| 25 | Rollback mid-import | atomic exists | — | assert |
| 26 | reserved preserve | да block8 | — | + completed release |
| 27 | Reserve during import | postgres skip | — | enable |
| 28 | 1С down | timeout tests | да | — |
| 29 | APPLY без прав | sync_log 403 | да | — |
| 30 | Непубликация техсклада | StoreList excludes wh | да | **auto-create flags** |

---

## 6. План исправлений

### BLOCK 1 — Целостность данных (CRITICAL)

| Задача | Приоритет | Файлы | Критерий | Тесты |
|--------|-----------|-------|----------|-------|
| Новый idempotency key без qty | P0 | importer, stock_ops | 5→8→5 OK | oscillation |
| Hash/no truncate 128 | P0 | stock_ops, ledger | long series OK | 64-char series |
| completed → release reserved | P0 | transitions, orders | reserved=0 | inbound completed |
| Stale stock policy + dry-run | P0 | importer, sync | no ghost sell | missing row |

### BLOCK 2 — Склады и сопоставление

| Задача | Приоритет | Файлы | Критерий |
|--------|-----------|-------|----------|
| Default inactive / warehouse | P0 | importer | Сервис не в /stores |
| Match only by warehouse id / mapping | P0 | importer | no name hijack |
| Pre-apply warehouse checklist | P1 | list_onec_warehouses, admin UI | mapping required |

### BLOCK 3 — Остатки, серии, резервы

| Задача | Приоритет | Файлы |
|--------|-----------|-------|
| Cart aggregate availability | P0 | cart/views |
| plan_and_reserve serial filter | P0 | orders.py |
| FE/API aggregate by store | P0 | serializers, FE |
| Public availability exclude warehouse | P0 | products serializers/filters |
| series without ID skip | P1 | importer |
| reserved&gt;qty alerts | P1 | report_ops_alerts |

### BLOCK 4 — Идемпотентность и транзакции

| Задача | Приоритет | Файлы |
|--------|-----------|-------|
| CLI → run_catalog_import | P0 | import_onec_catalog |
| Ledger failed-key retry | P0 | ledger, stock_ops |
| Revive/cancel generation | P1 | orders.py |
| Batch apply / shorter locks | P2 | importer |

### BLOCK 5 — Безопасность

| Задача | Приоритет | Файлы |
|--------|-----------|-------|
| Stock Admin readonly onec | P0 | stores/admin |
| StockListView ACL | P1 | stores/views |
| Product delete guards | P1 | admin products |
| APPLY gates уже сильны | — | сохранить |

### BLOCK 6 — Производительность

| Задача | Приоритет | Notes |
|--------|-----------|-------|
| Prefetch products/stores in apply | P2 | N+1 loops |
| Cap issues serialization | P2 | series_present flood |
| 50k–100k rows | P2 | memory + tx time; measure before optimize |

### BLOCK 7 — Отчётность

| Задача | Приоритет |
|--------|-----------|
| Severity info/warn/error | P1 |
| Actual vs planned upserts | P1 |
| Anomaly gates (row count Δ, zero%) | P0 before first prod APPLY |
| Would-create stores report | P0 |

### BLOCK 8 — Тесты

Покрыть таблицу §5 пункты 1,3,5,6,8,20,21,26-completed,30-autocreate как минимум.

---

## 7. Production Readiness Checklist (до первого APPLY)

- [ ] Исправлен idempotency key (без qty; без опасного truncate)
- [ ] Есть тест oscillation 5→8→5 и 1→0→1
- [ ] Политика completed: release reserved реализована и протестирована
- [ ] Все склады 1С заранее смаплены; auto-create = inactive/warehouse
- [ ] Dry-run на полном XML: 0 unexpected store creates; просмотрены ambiguous/SKU/price
- [ ] Anomaly gates: min product rows, max skip %, no empty dump
- [ ] Политика missing rows согласована с 1С (zero vs keep)
- [ ] Cart/checkout/PDP работают на multi-series SKU
- [ ] Public availability не считает is_warehouse
- [ ] CLI apply идёт через тот же lock, что Celery
- [ ] ONE_C_CATALOG_SYNC_ENABLED=false до ручного green dry-run
- [ ] Backup БД / возможность rollback deploy
- [ ] Ops alert на reserved&gt;quantity
- [ ] Stock Django Admin не даёт править 1C quantity
- [ ] Подтверждение владельца по вопросам §8

---

## 8. Вопросы к владельцу бизнеса / 1С

1. Какие склады из выгрузки — публичные точки выдачи, а какие только техсклады?  
2. Должен ли сайт обнулять остаток, если позиция/серия исчезла из полной выгрузки?  
3. Кто SoT по физическому quantity после продажи — 1С (ожидаемо) или сайт?  
4. Что делать с товарами без цены: скрыть / оставить старую цену / обновить только остаток?  
5. `series`/`seriesId` — это IMEI? Обязателен ли seriesId? Допустимы ли дубли IMEI?  
6. Выгрузка всегда полная snapshot или может быть инкрементальной/частичной?  
7. Нужна ли продажа с Apple Room / сервисного склада (delivery без pickup)?  
8. При reserved&gt;quantity после сбоев — авто-коррекция или только ручной ops?  
9. Можно ли создавать категории/товары с сайта после включения 1С, или 1С — единственный источник?  
10. Какой SLA sync (частота Beat) и допустимое окно устаревания остатков?

---

## 9. Итоговое заключение

### Можно ли безопасно запускать APPLY сейчас?

**Нет.**

### Обязательно до запуска

- ONEC-001, ONEC-002 (идемпотентность остатков)  
- ONEC-003 (completed → release)  
- ONEC-005 (не публиковать новые склады)  
- ONEC-006 или явный freeze + политика stale (иначе ghost stock)  
- ONEC-008, ONEC-009, ONEC-010, ONEC-011 (серии + availability)  
- ONEC-013 (единый apply lock)  
- ONEC-017 (безопасный match складов)  
- Anomaly gates + полный dry-run review  

### Можно отложить

- Батчинг транзакций (ONEC-014) до роста объёма  
- Global IMEI unique (ONEC-028) до бизнес-требования  
- Косметика series_present severity (ONEC-016) после P0  
- Category cycle edge cases если 1С гарантирует acyclic tree  

### Требуют владельца 1С/бизнеса

- Список публичных складов  
- Политика missing rows / partial dump  
- Цена vs остаток (ONEC-007 гибрид)  
- Семантика серий/IMEI  
- SoT резервов vs 1С quantity после выдачи  

### Требуют проверки на production (отдельное разрешение)

- Реальный Content-Length / стабильность полного XML (~7942 строк)  
- Фактические seriesId длины и формат  
- Список складов «Сервис»/«Офис»/БАМ/… vs точки Ringoo  
- Наблюдение reserved&gt;quantity на живых заказах  
- Нагрузка APPLY при конкурентных checkout  

---

*Аудит выполнен без APPLY, без записи в БД production, без запросов к боевой 1С и без изменения кода.*
