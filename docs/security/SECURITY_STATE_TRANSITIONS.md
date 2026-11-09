# Переходы статусов

Дата: 2026-11-07. Источник — `apps/orders/services/transitions.py` и статусы `Payment`. Это не полная прогонка каждого ребра.

## Заказ

Допустимые переходы функции `transition_order_status`:

| Из | В |
|---|---|
| new | confirmed, cancelled |
| confirmed | in_progress, cancelled |
| in_progress | completed, cancelled |
| completed | нет |
| cancelled | нет |

Полный возврат ЮKassa для `new` и `confirmed` идёт в `cancelled` и снимает резерв. Для `in_progress` и `completed` статус заказа не меняется. Частичный возврат статус заказа не меняет. Отдельного статуса `refunded` у заказа нет.

Отмена идёт через `cancel_order_and_release_stock` и снимает резерв. Отмена уже оплаченного заказа требует `allow_paid`. Политика `LATE_ONLINE_PAYMENT_POLICY=revive` может провести `cancelled → confirmed` только с `allow_system_override`. Значение по умолчанию — `manual`: поздний успех оставляет заказ отменённым и платёж в `needs_review`. Это проверено на SQLite.

Кто инициирует. Покупатель статус заказа патчем не меняет. Группа заказов в админском API ходит через ту же функцию. Webhook сам пишет только переход `new → confirmed` после сверки GET.

## Платёж

`created → registered` после ответа ЮKassa с id и `confirmation_url`. Дальше `pending`, `paid`, `failed`. `paid` не переигрывается повторным webhook. `reversed` и `refunded` тоже не переводятся обратно в `paid` этой функцией сверки. Несовпадение суммы, валюты или metadata при удалённом `succeeded` даёт `needs_review`, не `failed` и не `paid`.

Полный подтверждённый refund: `paid → refunded`. Частичный: `paid → needs_review`. Заказ при этом остаётся как был.

Один `paid` на заказ зафиксирован ограничением базы.

## Резерв

Создание заказа увеличивает `reserved_quantity`, если условный UPDATE прошёл. Отмена уменьшает. Оплата и повтор webhook количество резерва не меняют. Импорт 1С меняет `quantity` и может оставить резерв больше количества. Возврат денег резерв не уменьшает.

## Возврат товара

Флаг `RETURNS_ENABLED` по умолчанию выключен. Денежный возврат в API по умолчанию dry-run. Переходы возврата в этом блоке не вызывались. Права сотрудника на чужой возврат при включённом флаге остаются открытым API-003.

## Журнал

Платёж пишет `payment_creation_started`, `payment_created`, `payment_succeeded`, `payment_canceled`, `payment_refunded` без секрета и без номера карты. Сверка кладёт урезанный JSON: ключи `password`, `secret`, `authorization`, `card`, `payment_method` вырезаются. Склад пишет `StockMovement`. Каталог 1С пишет `OneCCatalogSyncLog`. Отдельного сквозного журнала «платёж + резерв + 1С» одной лентой нет: последовательность собирается по этим таблицам и логам процесса. Куда логи процесса попадают на VPS, блок 6 не подтвердил.
