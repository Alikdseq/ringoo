# 1С — операционный runbook (без live apply)

**Флаги по умолчанию выключены.** Не включать `ONE_C_API_ENABLED` / catalog Beat без владельца 1С.

Ожидаемые пути (контракт; live **не** подтверждён этим документом):

- `…/CatalogFolders/folders`
- `…/CatalogProducts/products`
- `…/SiteRegistration/registrate`

## Проверка соединения

Админка → «Синхронизация 1С» → «Проверить подключение» (probe).
Или API: `POST /api/v1/admin/onec/sync/probe/` (staff + catalog group).
При `ONE_C_API_ENABLED=false` probe не ходит в сеть.

## Последний успешный sync

`GET /api/v1/admin/onec/sync/status/` → `last_success`, `data_age_hours`, `data_stale`.
Журнал: `GET /api/v1/admin/onec/sync/logs/`.

## Dry-run

Кнопка Dry Run / `POST …/dry-run/`. Не пишет каталог (только SyncLog). При API off — fixtures.

## Apply

Только при API on + `confirm=true` + очередь Celery. Параллельный apply блокируется Redis lock.
**Не** запускать против рабочей 1С без разрешения.

## Stuck `running`

Записи старше ~120 мин помечаются `failed` (`reap_stale_running_applies`). После этого возможен новый запуск. Сверьте каталог вручную при сомнении в незавершённом apply.

## Частичный успех

Статус `partial_success` + `error_messages` в SyncLog. Не очищает каталог. Повторный dry-run → разбор issues с владельцем 1С.

## Расхождение остатков

Ringoo: `quantity` из импорта, `reserved_quantity` локально. Не пишите остатки обратно в 1С с сайта. См. `RINGOO_STOCK_RESERVE_OPTIONS.md`.

## Запрещено без согласования

- Beat catalog sync
- Partner sync on register в prod без ответа по registrate
- Ручной PATCH цены/quantity у товаров с `onec_code`
- Угадывание GUID цветов
