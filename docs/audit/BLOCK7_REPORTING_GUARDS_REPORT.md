# BLOCK 7 — отчётность, контроль и защита APPLY 1С

Дата: 2026-11-14  
Среда: локальные тесты (`config.settings.test`). Production не затрагивался.

---

## 1. Сверка аудита ↔ BLOCK 1–6 ↔ остаток

| Задача | Что было в аудите | Что реализовано в BLOCK 1–6 | Что осталось / сделано в BLOCK 7 |
|---|---|---|---|
| ONEC-015 | `stocks_upserted` = planned, в т.ч. idempotent skip | Batch apply возвращал факт (`applied` / `skipped_idempotent`), но SyncLog брал `summary.stocks_upsert` из **плана** | **Исправлено:** после APPLY пишется факт batch; planned отдельно в summary |
| ONEC-016 | `series_present` → `errors_count` / PARTIAL | Issues копились в `errors_count=len(issues)` | **Исправлено:** info/warning/blocker; series_present → info, не PARTIAL |
| ONEC-026 | Пустой file XML без `parse_warnings` | HTTP-строки предупреждали; файлы — нет → риск mass-zero | **Исправлено:** `parse_catalog_files` + `OneCParseError` в plan |
| Blockers APPLY | severity/blocker, unknown warehouse, series без id | Уже fail-closed в BLOCK 2 | Подтверждено; stop_reason в SyncLog |
| Dry-run / Apply / lock | SyncLog + Redis lock (BLOCK 4) | Работало | Счётчики и статус уточнены; plan.run_id = SyncLog.run_id |
| Reconciliation / 9 складов / «Склад» / серии / reserved | BLOCK 2–5 | Готово | Не меняли |
| Batch upsert | BLOCK 6 | Готово | Счётчики завязаны на batch result |
| Отдельный пустой склад в XML | Допустимо | Zero только по seen_keys confirmed | Не меняли |

Не дублировали: карту складов, atomic снимка, reserve/release, admin Stock readonly.

---

## 2. Что было реализовано ранее

- Idempotency без qty, failed retry (BLOCK 1)
- Full-snapshot zero, 9 складов, «Склад» как точка (BLOCK 2)
- Серии / cart / aggregate / reserved>qty diagnose (BLOCK 3)
- completed/cancel release, Redis-lock CLI (BLOCK 4)
- Admin/API Stock + Product archive (BLOCK 5)
- Batch upsert, N+1 каталога (BLOCK 6)
- SyncLog модель, dry-run/apply API, blockers на plan

---

## 3. Что исправлено сейчас

1. **`integrations/onec/reporting.py`** — классификация issues: blocker / error / warning / info.
2. **`catalog_sync.run_catalog_import`** — SyncLog:
   - dry-run: counters_source=`planned`;
   - apply: products/stocks из `apply_catalog_import`; `stocks_zeroed`, `stocks_skipped_idempotent`, `anomalies_count`;
   - `errors_count` без series_present;
   - `stop_reason` при FAILED;
   - `plan.run_id` = SyncLog `run_id`.
3. **`parser.parse_catalog_files`** — пустые folders/products → `parse_warnings` (ONEC-026).
4. **Plan summary** — xml rows, unique products, stock_series_rows, issue counts.
5. **`serialize_sync_log`** — отдаёт zeroed / idempotent / warnings / info / anomalies / stop_reason.

---

## 4. Какие счётчики проверены

| Счётчик | Где | Dry-run | Apply |
|---|---|---|---|
| XML rows / folders | `records_received`, summary | planned | planned (вход) |
| Unique products | summary | да | да |
| Stock positions / series rows | summary | planned | planned + applied |
| Products create/update/skip | SyncLog fields | planned | **applied** |
| Stocks upserted | SyncLog | planned | **applied** (не skip) |
| Stocks zeroed | summary / serialize | 0 | **applied** |
| Skips / idempotent | stocks_skipped + summary | plan skip | plan skip + idempotent |
| Warnings / info / errors | summary + errors_count | раздельно | раздельно |
| Anomalies (reserved>qty) | summary after apply | 0 | diagnose count |
| run_id / duration / initiator / mode / status | SyncLog | да | да |

---

## 5. Аномалии, блокирующие APPLY

- `severity` / `blocker` issues (unknown warehouse, warehouse missing id, series without seriesId, invalid/rejected qty с severity, stock without product, …)
- Unmapped confirmed warehouse
- Unknown warehouseId в выгрузке
- Пустой/битый обязательный XML (`parse_warnings` → `OneCParseError`)
- Parallel apply (Redis lock / running SyncLog)
- `ONE_C_API_ENABLED=false` для API apply

Пустой **отдельный** склад в XML по-прежнему допустим (zero по отсутствию в seen_keys).

---

## 6. Предупреждения / info, не блокирующие APPLY

- **info:** `series_present` (не PARTIAL, не errors_count)
- **warning:** rejected_price (без severity), missing price на карточке, name/price variants, missing category, folder issues, sku conflict (как warning)

---

## 7. Результаты тестов

```text
tests/test_onec_block7_reporting_guards.py
tests/test_onec_sync_log.py
tests/test_onec_stock_idempotency.py
tests/test_onec_stock_reconciliation.py
tests/test_onec_block3_series_cart.py
tests/test_onec_block4_orders_locks.py
tests/test_onec_block5_security_integrity.py
tests/test_block8_catalog_guards.py
```

**93 passed.**

Покрыто: ONEC-015/016, empty file/HTTP snapshot, unknown warehouse → failed, dry-run без мутаций, regress BLOCK 1–5.

---

## 8. Риски и нерешённое

- Поля `stocks_zeroed` / `warnings_count` живут в JSON summary (без миграции колонок) — Admin list показывает основные int-поля.
- Повторный SyncLog apply того же XML с **новым** run_id снова делает upsert (ключи привязаны к run_id) — ожидаемо; идемпотентность внутри одного run подтверждена.
- Streaming XML / 50k–100k — вне BLOCK 7 (BLOCK 6 backlog).
- Произвольные «% пороги аномалий» не вводились.

---

## 9. Миграции

**Не нужны.**

---

## 10. Вердикт: переход к BLOCK 8

**Да**, можно переходить к BLOCK 8 после прочтения отчёта.  
Production APPLY / migrate / restart — только по отдельному разрешению.  
К BLOCK 8 в этой сессии **не переходим**.
