# Контракт HTTP API 1С:УТ 11 для сайта Ringoo

**Статус:** этап B — каталог, регистрация и заказы (SiteOrders) на стороне сайта.  
**Дата:** 28 октября 2026.

Базовый URL публикации: `{SERVER}/razrab/hs/`  
Переменные окружения сервера сайта:

| Переменная | Назначение |
| --- | --- |
| `ONE_C_API_BASE_URL` | Базовый адрес без завершающего слэша, напр. `https://SERVER/razrab/hs` |
| `ONE_C_LOGIN` | Логин пользователя API 1С (предпочтительно) |
| `ONE_C_PASSWORD` | Пароль (только env сервера; сменить, если светился в документах) |
| `ONE_C_API_USER` / `ONE_C_API_PASSWORD` | Синонимы (этап 1) |
| `ONE_C_API_TIMEOUT` | Таймаут секунд (по умолчанию 60) |
| `ONE_C_API_ENABLED` | `true` только для явных запросов из backend |
| `ONE_C_SYNC_PARTNER_ON_REGISTER` | Не включать в production без согласования |
| `ONE_C_ORDER_SYNC_ENABLED` | Асинхронная отправка заказов в 1С |
| `ONE_C_DEFAULT_WAREHOUSE_ID` | Устарело: не используется для sync; `warehouseId` = `Store.onec_warehouse_id` выбранного магазина |
| `ONE_C_ORDER_SYNC_MAX_ATTEMPTS` | Лимит повторов при сети/500 |

Не использовать `/ut11_test/hs/` и не смешивать UUID из разных баз. Хост сервера не выдумывать — подтвердить у Алана/администратора 1С.

Авторизация: **HTTP Basic**. Кодировка UTF-8.

---

## 1. Подтверждённые методы

| Назначение | Метод | Путь | Ответ |
| --- | --- | --- | --- |
| Категории | `GET` | `CatalogFolders/folders` | XML |
| Товары, цены, остатки | `GET` | `CatalogProducts/products` | XML |
| Регистрация покупателя | `POST` | `SiteRegistration/registrate` | JSON |
| Заказ / оплата | `POST` | `SiteOrders/orders` | JSON |
| Отмена заказа | `POST` | `SiteOrders/orders/cancel` | JSON |

### 1.1. Категории / товары

См. прежние правила парсера. Остатки хранятся по складу **и** `seriesId` (`Stock.onec_series_id`).

### 1.2. Регистрация покупателя

Тело JSON: `lastName`, `firstName`, `middleName`, `phone`.

Успех `201`/`200`:

```json
{ "ClientId": "<uuid>", "created": true }
```

Сайт сохраняет `ClientId` в `users_user.onec_partner_id` и/или `orders_order.onec_client_id`.  
`partnerId` принимается только как совместимость со старыми ответами.  
После таймаута — `pending_review`, автоповтор запрещён.

### 1.3. Заказы (`SiteOrders/orders`)

```json
{
  "orderId": "<uuid заказа сайта>",
  "orderNumber": "ORD-…",
  "orderDate": "2026-10-25T14:00:00+03:00",
  "warehouseId": "<uuid склада>",
  "ClientId": "<uuid контрагента>",
  "paid": false,
  "items": [
    {
      "productCode": "00-00034618",
      "quantity": 1,
      "amount": 5500.00,
      "seriesId": "<uuid или null>"
    }
  ]
}
```

- `amount` — сумма **всей строки**, не цена единицы.
- Разные серии одного товара — отдельные строки с `quantity=1`.
- Самовывоз и доставка: `warehouseId` = `Store.onec_warehouse_id` выбранного магазина заказа (магазин с наличием всех позиций; без сетевого резерва и без перемещений).
- Онлайн: сначала `paid=false`, после Сбера — тот же payload с `paid=true`.
- Наличные / при получении / перевод: пока только `paid=false`.
- Снимок payload без `paid` хранится в `Order.onec_payload_snapshot`.
- Повторы с тем же `orderId`; `400`/`409`/`422` без бесконечных ретраев.

Ответ успеха: `documentId`, `documentNumber`, `documentType`, `created`, `posted`.

### 1.4. Отмена

```json
{ "orderId": "<uuid>", "paid": false }
```

`paid` = последнее принятое состояние документа. Возврат денег отдельно.

---

## 2. Поведение сайта

1. После создания заказа — Celery `sync_order_to_onec_task(paid=false)`.
2. После `Payment.status=paid` — `sync_order_to_onec_task(paid=true)`.
3. После отмены заказа — `cancel_order_in_onec_task`.
4. Недоступность 1С не блокирует оформление на сайте.
5. Фискализация и callback от 1С — вне scope фазы B.

---

## 3. Внешние блокеры до реальных POST

- [ ] Подтверждён полный URL тестовой публикации `/razrab/hs/`
- [ ] UUID складов магазинов → `Store.onec_warehouse_id` для каждой точки
- [ ] Секреты только в env; пароль из старой инструкции сменён
- [ ] Явное разрешение на тестовые POST регистрации/заказов

---

## 4. Безопасная проверка

```bash
cd backend
python manage.py import_onec_catalog \
  --folders ../integration1CandKassa/Иерархия\ Папок.xml \
  --products ../integration1CandKassa/Товары.xml

# Тесты без сети:
python manage.py test tests.test_onec_http tests.test_onec_orders tests.test_onec_catalog
```

Не запускать `--apply` и реальные POST заказов на production без dry-run и согласования.
