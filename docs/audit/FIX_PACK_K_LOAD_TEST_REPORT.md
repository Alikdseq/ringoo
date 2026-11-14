# FIX-PACK K — B8-018: Нагрузочное тестирование Ringoo ↔ 1С

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Production / реальная 1С / APPLY на VPS / платежи / `.env` / migrate / commit:** не выполнялись  
**Код runtime (parser/importer/stock_ops):** не переписывался  
**Артефакты прогона:** `backend/scripts/b8_018_load_benchmark.py`, `backend/var/b8_018_results.json`, fixtures в `backend/var/b8_018_fixtures/`

---

## 1. Среда тестирования и конфигурация БД

| Параметр | Значение |
|---|---|
| Django settings | `config.settings.test` |
| БД | **SQLite `:memory:`** |
| Cache (Django test) | `DummyCache` (lock.add не персистит) |
| Redis localhost:6379 | **доступен** (PING), использован только как факт наличия; lock API проверен через LocMemCache |
| RAM available (старт) | ~754 MiB |
| Python | 3.11.9 |

**Важно:** все APPLY/DRY-RUN timings ниже — **SQLite**, не PostgreSQL. Результаты нельзя выдавать за prod Postgres benchmark. Конкурентные writers / WAL / row-level locks на Postgres **не подтверждены** этим pack.

### Инвентаризация (этап A)

| Зона | Поведение |
|---|---|
| `parser.py` | `defusedxml` `ET.fromstring` / `ET.parse` — **полный DOM** в памяти |
| `importer.py` | План целиком в RAM (`products`, `stocks`, `stocks_to_zero`, `issues`); `plan.to_dict()` сериализует всё |
| `apply_catalog_import` | **Одна** `transaction.atomic` (ONEC-014) на upsert+zero |
| `apply_onec_stock_upserts_batch` | Prefetch prior keys + existing Stock; `bulk_create` / `bulk_update` / `bulk_create` movements |
| Redis lock | `cache.add("onec:catalog:apply_lock")` + fallback `OneCCatalogSyncLog STATUS_RUNNING` |
| N+1 риск | Per-product create/update в `apply_catalog_import`; legacy single upsert (не на hot path batch) |
| Без Postgres недостоверно | True concurrency, длительные TX под нагрузкой, realistic IO |

---

## 2. Fixtures

Синтетика по структуре sample (`<Товары><Товар … />`), UUID складов из `warehouse_map` (без PII/секретов).

| Имя | Карточки | XML-строки | Склады | Серии* | Размер, байт | gen_ms |
|---|---:|---:|---:|---:|---:|---:|
| `2k_x3wh` | 2 000 | 7 800 | 3 | 2 (30% карточек) | 2 208 740 | 25 |
| `10k_x3wh` | 10 000 | 39 000 | 3 | 2 (30%) | 11 060 740 | 121 |
| `25k_x1wh` | 25 000 | 25 000 | 1 | 1 (30%) | 6 953 959 | 83 |
| `50k_x1wh` | 50 000 | 50 000 | 1 | 1 (30%) | 13 918 959 | 124 |
| `folders.xml` | 1 категория `SYN-CAT-001` | — | — | — | малый | — |

\*Серии добавляются только для ~30% карточек (`i % 10 < 3`), иначе blank series — ближе к смеси телефонов/аксессуаров в sample.

Также: штатные `integrations/onec/fixtures/sample_*.xml` (структурный эталон).

---

## 3. Таблица объёмов (сводка)

| Объём | Parser | DRY-RUN plan | Batch APPLY (строки Stock) |
|---|---|---|---|
| 2k cards / ~7.8k rows | OK | OK (~16 s plan SQLite) | 1k/5k — OK |
| 10k / ~39k rows | OK | Тяжело (~61 s + 22 MB report) | 10k — OK |
| 25k / 25k rows | OK | Тяжело (~85 s) | 25k — OK (~28 s) |
| 50k / 50k rows | OK (~3.2 s) | **не гоняли full plan** (gate по времени/RAM/report) | не гоняли |

---

## 4. Parser benchmark

| Fixture | read_ms | parse_ms | rows | unique cards | peak tracemalloc MiB | RSS after MiB |
|---|---:|---:|---:|---:|---:|---:|
| 2k_x3wh | 30 | 457 | 7 800 | 2 000 | 14.0 | 85 |
| 10k_x3wh | 114 | 2 619 | 39 000 | 10 000 | 66.5 | 134 |
| 25k_x1wh | 76 | 1 448 | 25 000 | 25 000 | 42.0 | 114 |
| 50k_x1wh | 135 | 3 070 | 50 000 | 50 000 | 83.9 | 153 |

Рост времени/памяти **примерно линейный** по числу XML-строк (не по «карточкам»). DOM выдерживает 50k строк на этой машине; streaming **не обязателен** до ~50–100k строк при текущей форме XML.

### Edge cases

| Кейс | Результат |
|---|---|
| Пустой XML | `OneCParseError` «Пустой XML» |
| Битый XML | `OneCParseError` mismatched tag |
| `<Товары></Товары>` | parse_warnings; **plan raises** — неуспешный пустой snapshot |
| quantity=`abc` | Строка парсится; `quantity_problem=not_a_number` (не «успешный ноль») |

---

## 5. Import plan / DRY-RUN

Тестовая БД: предсозданы Product `SYN-000000…` под объём; склады confirmed. DRY-RUN **не менял** `Stock.count`.

| Label | parse_ms | plan_ms | stocks | stocks_to_zero | blockers | apply_allowed | report_bytes | peak MiB |
|---|---:|---:|---:|---:|---|---|---:|---:|
| 2k_x3wh | 545 | **16 227** | 7 800 | 0 | 0 | true | 4.5 MB | 74.9 |
| 10k_x3wh | 2 712 | **60 942** | 39 000 | 0 | 0 | true | **22.5 MB** | 121.5 |
| 25k_x1wh | 1 710 | **85 363** | 25 000 | 0 | 0 | true | 19.4 MB | 109.9 |

`stocks_to_zero=0` в объёмных прогонах — потому что заранее не было «лишних» Stock вне снимка. Отдельный smoke:

- missing series в snapshot → `stocks_to_zero=1`, APPLY обнулил `OLD` (`qty=0`), **reserved=1 сохранён**, продукт не удалён; `reserved_over_quantity_count=1` (аномалия диагностируется).

### Сценарии fail-closed (BLOCK 7)

| Сценарий | Итог |
|---|---|
| all_matched | `apply_allowed=true` |
| unknown_warehouse | blockers `unknown_warehouse` → **blocked** |
| series_without_id | blocker `series_missing_id` |
| bad_quantity | blocker `rejected_quantity` |
| empty_products | `OneCParseError` |
| new_product | `apply_allowed=true` |

---

## 6. Batch APPLY (только локальная test DB)

`apply_onec_stock_upserts_batch` на SQLite:

| rows | applied | time_ms | SQL queries | SQL/row | repeat skip | new run_id applied | reserved preserved |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 000 | 1 000 | 966 | 36 | 0.036 | 1 000 / 32 ms | 1 000 | yes |
| 5 000 | 5 000 | 5 078 | 144 | 0.029 | 5 000 | 5 000 | yes |
| 10 000 | 10 000 | 10 954 | 281 | 0.028 | 10 000 | 10 000 | yes |
| 25 000 | 25 000 | 27 757 | 691 | 0.028 | 25 000 | 25 000 | yes |

Время **почти линейно** (~1.1 ms/row на SQLite). SQL/row стабильно низкий (batch, не N+1).

### Семантика

| Проверка | Результат |
|---|---|
| qty=0 не удаляет Product | OK |
| повторное появление после zero | OK |
| исчезновение серии → zero | OK |
| смена qty сохраняет reserved | OK (9 qty / 2 reserved / avail 7) |
| idempotent same run_id | applied=0, skip=N |
| новый run_id | повторный apply |

---

## 7. SQL query counts

- Batch 25k: **691** queries ≈ **0.028 / row** (bulk chunks).  
- Idempotent repeat 25k: **32** queries.  
- Для сравнения BLOCK 6: single upsert ~5–8 SQL/row; batch ≤25 queries на 40 rows.

---

## 8. Память и время — выводы

| Фаза | Характер роста | Практический вывод |
|---|---|---|
| Parser DOM | ~линейный по XML-строкам | 50k строк локально ок (~84 MiB peak) |
| DRY-RUN plan + report | время и JSON **дорого** | 10k×3 склада (~39k actions) → ~61 s + 22 MB report на SQLite |
| Batch APPLY | линейный | 25k строк ~28 s SQLite |
| RSS процесса к концу полного suite | ~283 MiB | на машине с ~0.7 GiB free — запас тонкий |

Влияние складов/серий: умножает **строки**, не карточки — именно строки двигают parser/plan/apply.

---

## 9. Транзакции и rollback

| Тест | Результат |
|---|---|
| Ошибка mid-batch во внешней `atomic` | `stocks_after == stocks_before` — **частичного snapshot нет** |
| Повтор после неудачи | семантика failed prior → retry (ONEC-024), покрыта batch-кодом / BLOCK тестами |
| Полный snapshot APPLY | одна atomic (ONEC-014) — долгая блокировка на больших объёмах = **эксплуатационный риск**, не баг семантики |

---

## 10. Redis lock / concurrency

| Проверка | Результат |
|---|---|
| Django test cache | DummyCache → `_cache_persists_locks()=false` |
| LocMemCache.add (контракт Redis) | 2-й acquire блокируется; TTL expiry → reacquire OK |
| Redis ping | true (localhost) |
| SyncLog `STATUS_RUNNING` | `_running_apply_in_db()=true` |
| Postgres concurrent import | **не проверялось** |

---

## 11. Узкие места

1. **`plan_from_parsed` + `plan.to_dict()`** — CPU и размер отчёта растут с числом stock actions; API/admin могут упереться в память/таймаут раньше, чем parser.  
2. **Одна atomic на полный APPLY** — корректно для snapshot, но длинное окно блокировок при десятках тысяч строк.  
3. **Per-product loop в `apply_catalog_import`** — не измерен на 25k *созданий* карточек; при большом числе `create` будет медленнее batch stock path.  
4. **Full DOM parser** — приемлем до ~50k строк; при 100k+ и плотных сериях×складах — кандидат на streaming (только после согласования).  
5. **`reserved > quantity` после mass-zero** — диагностируется (`reserved_over_quantity_count`), физический qty обнуляется, заказной reserve не сбрасывается (ожидаемо, но ops-риск).  
6. Без **Redis cache** в runtime lock ослабевает до SyncLog fallback.

---

## 12. Рекомендуемый безопасный предел нагрузки

| Контур | Безопасный ориентир (до Postgres staging) |
|---|---|
| Parser | до **50k XML-строк** локально ок |
| DRY-RUN с полным JSON-отчётом | до **~8–10k stock actions** комфортно; 39k — только offline/ops |
| Batch stock APPLY (уже существующий каталог) | до **25k строк** на SQLite прошло; на prod закладывать запас и maintenance window |
| Полный catalog APPLY (create products + stock + zero) | **не считать подтверждённым** выше нескольких тысяч новых карточек без отдельного прогона |
| 50k full DRY-RUN/APPLY | **не рекомендовать** на текущей реализации отчёта/одной TX без staging Postgres + урезанного reporting |

---

## 13. Что не удалось проверить и почему

| Пункт | Причина |
|---|---|
| PostgreSQL concurrency / realistic TX | test DB = SQLite; внешняя/prod БД запрещены ТЗ |
| Реальный XML/объём 1С | обращение к 1С запрещено |
| Production APPLY / DRY-RUN | запрещено |
| Django Redis cache lock end-to-end в test settings | DummyCache; Redis ping есть, но settings не переключались на чтение `.env` |
| Full APPLY 50k cards с create+zero | safety gate по времени/RAM/report; не гоняли |
| Нагрузочный Celery Beat overlap | вне scope локального script (частично покрыто lock unit) |

---

## 14. Предложенные исправления (не внедрены)

| # | Предложение | Риск/нужно согласование |
|---|---|---|
| 1 | Урезать/стримить SyncLog summary (не полный `plan.to_dict()` на больших объёмах) | Низкий/средний |
| 2 | Профилировать `plan_from_parsed` (prefetch Product/Stock) | Низкий |
| 3 | Batch create/update Product в APPLY | Средний — согласовать |
| 4 | Streaming XML parser | Только если >50–100k строк на реальной 1С — **согласование** |
| 5 | Протокол chunked APPLY без нарушения snapshot | **Архитектурное** — не делать без отдельного разрешения |
| 6 | Обязательный Redis cache в staging/prod для apply lock | Ops |
| 7 | Отдельный Postgres load job (1k/5k/25k + concurrent) | Ops staging |

---

## 15. Вердикт B8-018

| Вопрос | Ответ |
|---|---|
| Выдержит ли **2k**? | **Да** (parser + dry-run + batch apply) |
| Выдержит ли **10k**? | **Да**, с оговорками: при 3 складах ≈39k строк dry-run/report тяжёлые на SQLite; stock batch OK |
| Выдержит ли **25k**? | **Parser и batch stock APPLY — да** на test SQLite; full dry-run plan медленный (~85 s); полный catalog APPLY с массовым create не доказан |
| Можно ли безопасно тестировать **50k**? | **Parser — да** локально. Full dry-run/APPLY 50k — **не как безопасный штатный тест** без Postgres staging и контроля отчёта/TX |
| Что остаётся до реальной 1С? | Staging Postgres + Redis lock; DRY-RUN на копии реального XML; замер series×warehouse плотности; узкий APPLY; мониторинг длительности одной atomic и `reserved_over_quantity` |

**Итог:** текущая архитектура (DOM + batch upsert + одна atomic + Redis/SyncLog lock) **пригодна для реального каталога порядка тысяч–десятков тысяч строк остатков**, но узкие места — **построение/сериализация плана** и **длительность единой APPLY-транзакции**, а не разбор XML до 50k строк. Переписывать parser/importer без отдельного согласования не требуется по результатам этого pack.

---

## Остановка

Fix-pack K завершён отчётом. B8-019 и изменения production-кода **не начинались**.
