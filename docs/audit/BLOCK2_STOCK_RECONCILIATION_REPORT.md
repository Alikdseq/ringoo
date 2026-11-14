# BLOCK 2 + сверка остатков — технический отчёт

Дата: 2026-11-13  
Среда: локальная / тестовая (production APPLY не выполнялся)

---

## 1. Что реализовано

### Сопоставление складов (BLOCK 2)
- Подтверждённая карта 9 `warehouseId` → существующие Store (ключ — только `onec_warehouse_id`).
- Автосоздание Store при импорте **запрещено**; неизвестный склад → apply blocker.
- Точка «Склад» (`63f7e17d-…`): `is_warehouse=True` (метка UI), `is_active=True`, участвует в наличии/корзине/самовывозе.
- Data-migration `0008_map_confirmed_onec_warehouses`: проставляет ID на 8 seed-магазинах по slug и создаёт `tech-sklad` при отсутствии.
- Ops-файл: `docs/integrations/onec_warehouse_mapping.json` + `warehouse_map.py`.

### Обнуление отсутствующих остатков (reconciliation)
- Полный снимок → `seen_keys = (product_id, store_id, onec_series_id)`.
- После upsert: `stocks_to_zero` для позиций с `quantity>0` на подтверждённых складах, которых нет в снимке.
- Склад, отсутствующий в XML целиком, **не** ошибка: его старые позиции обнуляются.
- Upsert + zero в одной `@transaction.atomic` (`apply_catalog_import`).
- Fail-closed: issues с `severity=True` / `blocker=True`, unknown warehouse, unmapped confirmed warehouse → `apply_allowed=False`, zero-phase не планируется.

### Серии
- Гранулярность обнуления включает `onec_series_id`.
- Серия без `seriesId` → skip + blocker (небезопасная неоднозначность).

### Разделение карточки и остатков
- `price_blocked` переводит create/update карточки в `skip`.
- Для **существующего** Product остатки всё равно планируются как `upsert`.
- Новый товар без цены / без Product → Stock не создаётся; строка не попадает в `seen_keys`.

### Публичное наличие
- `Stock.available_quantity_retail()` — все активные точки, **включая** `is_warehouse` (Apple Room / «Склад»).
- `is_warehouse` — только клиентская метка «склад», не исключение из наличия.
- List/Detail serializers, `in_stock` filter, PDP stock list — учитывают склад.

### Корзина и checkout
- `POST/PATCH /cart/items/` проверяет available по активным точкам (с store или суммарно).
- Точка «Склад»/Apple Room доступна в корзине, самовывозе и заказе.
- API отдаёт `is_warehouse` для подписи «склад» в UI.
- ProductCard и PDP блокируют кнопку при `out_of_stock` / нуле в выбранном магазине.

### Идемпотентность / ONEC-024
- Ключ: `onec:{sha256(run_id:product:store:series)}` — без quantity.
- Повтор того же `run_id` не дублирует движения.
- Failed prior movement (`success=False`) с тем же ключом удаляется и apply повторяется.

---

## 2. Изменённые файлы

| Файл | Что / зачем |
|---|---|
| `integrations/onec/warehouse_map.py` | Карта 9 складов, helpers |
| `integrations/onec/importer.py` | Нет auto-create Store; seen_keys; stocks_to_zero; severity→blockers; price≠stock; apply zero-phase |
| `integrations/onec/catalog_sync.py` | Совместимость с run_id / blockers |
| `apps/stores/stock_ops.py` | BLOCK1 ключ без qty; ONEC-024 retry |
| `apps/stores/models.py` | `available_quantity_retail` |
| `apps/stores/migrations/0008_…` | Маппинг warehouseId + tech-sklad |
| `apps/products/serializers.py` | Розничное наличие / статус |
| `apps/products/catalog_filters.py` | `in_stock` / store без техсклада |
| `apps/cart/views.py`, `serializers.py` | Проверка остатков, отказ техсклада |
| `apps/orders/views.py` | Retail available при reorder |
| `apps/cart/tests.py` | Stock в setup для POST cart |
| `frontend/.../ProductCard.tsx` | Disable add при out_of_stock |
| `frontend/.../ProductPageClient.tsx` | Учёт выбранного магазина |
| `docs/integrations/onec_warehouse_mapping.json` | Ops mapping |
| `tests/onec_test_utils.py` | ensure_confirmed_stores |
| `tests/test_onec_stock_reconciliation.py` | BLOCK2 / zero / public / cart |
| `tests/test_onec_stock_idempotency.py` | BLOCK1 + ONEC-024 |
| Прочие правки тестов block8 / int009 / onec_http | Совместимость |

---

## 3. Миграции

- **`stores.0008_map_confirmed_onec_warehouses`**
  - Обновляет `onec_warehouse_id`, `onec_warehouse_name`, `is_warehouse` у существующих slug.
  - Создаёт `tech-sklad` только если отсутствует.
  - **Риск потери данных:** низкий (не удаляет розничные Store, не меняет адреса/PK).
  - Reverse: снимает mapping; удаляет только tech-sklad с этим warehouseId.

Production migrate **не запускался** (запрет задачи).

---

## 4. Тестирование

Прогон (локально, `config.settings.test`):

- `tests/test_onec_stock_reconciliation.py` — **passed**
- `tests/test_onec_stock_idempotency.py` — **passed**
- `tests/test_block8_catalog_guards.py`, `test_int009_stock_ledger_complete.py`, `test_onec_http.py` — **passed**
- `apps/stores/tests.py`, `apps/cart/tests.py` — **passed**
- `apps/orders/tests.py` — **passed**

Сводно по затронутым наборам: **~93+ / 63** в отдельных прогонах, **0 failed** в финальных связанных suites.

Не прогонялся полный suite всего репозитория (долго); рекомендуется перед тестовым APPLY.

---

## 5. Бизнес-сценарии

| Сценарий | Поведение |
|---|---|
| Товар закончился (нет в XML) | Все его позиции на 9 складах → `quantity=0`, карточка `is_active`, «Нет в наличии» |
| Товар снова в XML | Upsert восстанавливает qty; reserved сохраняется |
| Закончился в одном магазине | Обнуляется только `(product, store, series)` этой точки |
| Исчезла одна серия | Только эта серия → 0; другие серии/магазины без изменений |
| Склад пуст / отсутствует в XML | Все старые позиции этого store обнуляются |
| Только техсклад | Остаток пишется, публично `out_of_stock`, нельзя в корзину/самовывоз |
| Битый quantity / unknown warehouse | APPLY blocked, zero-phase не выполняется |

---

## 6. Что осталось сделать

1. **На staging/dev БД:** `migrate` → проверить 9 mapping (или `list_onec_warehouses --apply` с JSON, если миграция ещё не накатана).
2. **Тестовый DRY-RUN**, затем контролируемый APPLY на не-production (по согласованию).
3. Убедиться, что slug розничных точек на стенде совпадают с seed (`ardon-sovetov-1` …); иначе миграция пропустит строку — нужна ручная привязка.
4. Полный pytest suite перед релизом.
5. Мониторинг первого live-снимка: `stocks_to_zero`, `apply_blockers`, SyncLog.

---

## 7. Готовность к следующему этапу

**Да** — можно переходить к **тестовому импорту на dev/staging** (не production):

1. Migrate `0008`.
2. DRY-RUN каталога, проверить `apply_allowed` и отчёт warehouses.
3. APPLY на тестовой БД, сверить остатки по магазинам/сериям.
4. Проверить витрину: out_of_stock, корзина, checkout, техсклад скрыт.

Production sync / APPLY / migrate — **не выполнять** до явного разрешения.
