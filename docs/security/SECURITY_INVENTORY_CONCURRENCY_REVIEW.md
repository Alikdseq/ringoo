# Склад, резерв и гонки

Дата: 2026-11-07. Рабочие остатки не менялись. Прогон — SQLite in-memory.

## Где лежит остаток

`Stock.quantity` — учтённое количество, `reserved_quantity` — резерв. Доступно `max(0, quantity - reserved_quantity)`. Уникальность: товар + магазин + `onec_series_id`.

Резерв при оформлении берёт `plan_and_reserve_at_store` только в выбранном магазине. Несерийный путь — `Stock.reserve_atomic`: `select_for_update` и условный `UPDATE`, пока `quantity >= reserved + take`. Серия — отдельный условный `UPDATE` по `onec_series_id`. Журнал `StockMovement` с ключом идемпотентности. Повтор того же ключа успех не повторяет.

Отмена заказа и полный возврат ещё не выданного заказа (`new`/`confirmed`) снимают резерв через `release_order_item_reservations`. Успешная оплата `quantity` не уменьшает. Повтор того же `refund_id` резерв второй раз не снимает. Полный возврат заказа `in_progress` или `completed` резерв и `quantity` не меняет.

Импорт 1С больше не записывает отрицательное количество как ноль. Явный ноль по-прежнему записывает `quantity` и поле резерва не затирает.

## Гонки

Последовательно на SQLite: остаток 1, первый `reserve_atomic` успешен, второй вернул false, `reserved_quantity` остался 1.

Одновременно два покупателя, два `pay`, webhook против отмены, импорт 1С во время оформления — NOT TESTED. В репозитории это описано в `backend/tests/test_concurrency_postgres.py` и пропускается без `RINGOO_TEST_POSTGRES` и `config.settings.test_postgres`. Запускать его можно только на пустой базе, не на рабочей.

`reserve_for_delivery` при неудаче второго `UPDATE` возвращает false и не бросает исключение. Внешний `@transaction.atomic` тогда фиксирует уже сделанные строки. На PostgreSQL строки держатся `select_for_update`, поэтому ветка редкая. Она не воспроизводилась.

SQLite не доказывает, что блокировка на PostgreSQL удержит последнюю единицу.
