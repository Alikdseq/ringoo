# Инструкция для 1С: входящие статусы и оплаты на сайт Ringoo

**Дата:** 9 ноября 2026  
**Сайт:** `https://ringoo15.store`  
**Endpoint:** `POST /api/v1/integrations/1c/orders/status/`

Полный URL:

```text
https://ringoo15.store/api/v1/integrations/1c/orders/status/
```

## 1. Когда отправлять запрос

| Событие в 1С | Что слать на сайт |
|---|---|
| Заказ принят в работу | `status: processing` |
| Заказ собран / готов | `status: ready` |
| Товар выдан / доставлен | `status: closed`, `result: completed` |
| Заказ отменён | `status: closed`, `result: cancelled` |
| Клиент оплатил наличными в магазине | блок `payment` со `status: paid`, `method: cash` |
| Клиент оплатил картой в магазине | блок `payment` со `status: paid`, `method: card_on_pickup` |

**Не нужно** слать оплату для заказов с онлайн-оплатой (ЮKassa) — сайт уже ставит `paid` сам.  
Если 1С всё же пришлёт `paid` для уже оплаченного online-заказа, сайт ответит успехом без второго платежа.

Статус выполнения и статус оплаты — **разные поля**. Можно слать отдельно или вместе в одном JSON.

## 2. Авторизация

Заголовок (обязательно):

```http
X-OneC-Token: <секретный_токен>
```

Токен выдаёт администратор сайта (переменная `ONE_C_INCOMING_TOKEN` / `ONEC_INCOMING_TOKEN`).  
Не передавать токен в URL и не писать его в переписку/тикеты.

Без токена или с неверным — `401`.  
Если токен на сервере не настроен — `503`.

## 3. Общие правила JSON

- Метод: `POST`
- `Content-Type: application/json; charset=utf-8`
- Обязательно: `event_id`, `order_number`
- Нужен хотя бы один из: `status` или `payment`
- `order_number` — номер **сайта**, как в заказе (формат `ORD-YYYYMMDD-xxxxxx`), тот же, что уходит в 1С в поле `orderNumber`
- `event_id` — уникальный ID события в 1С; повтор с тем же ID безопасен (`duplicate: true`)

### Допустимые `status`

| Код | Смысл на сайте |
|---|---|
| `processing` | В обработке |
| `ready` | Готов к выдаче (самовывоз) / готов к отправке (доставка) |
| `closed` | Завершён (нужен `result`) |

### Допустимые `result` (только с `closed`)

| Код | Текст покупателю |
|---|---|
| `completed` | Получен |
| `cancelled` | Отменён |

### Допустимые `payment.status`

`paid`, `refunded` (переход `paid` → `unpaid` запрещён)

### Допустимые `payment.method`

| Код от 1С | Способ на сайте |
|---|---|
| `cash` | Наличными |
| `card_on_pickup` | Картой при получении |
| `card_on_delivery` | то же (синоним) |

Сумма `payment.amount` должна совпадать с суммой заказа сайта (Decimal, например `"25990.00"`). Валюта: `RUB`.

### Разрешённые переходы статуса

```text
new → processing → ready → closed
         ↘           ↘
          closed(cancelled) из processing/ready/new
```

Повтор того же статуса — OK. Менять уже `closed` обычным запросом нельзя (`409`).

## 4. Примеры запросов

### 4.1. Заказ принят

```bash
curl -X POST "https://ringoo15.store/api/v1/integrations/1c/orders/status/" \
  -H "Content-Type: application/json" \
  -H "X-OneC-Token: YOUR_TOKEN_HERE" \
  -d '{
    "order_number": "ORD-20261109-aaaa01",
    "status": "processing",
    "event_id": "1c-evt-ORD-20261109-aaaa01-01",
    "source": "1c",
    "occurred_at": "2026-11-09T18:00:00+03:00"
  }'
```

### 4.2. Готов к выдаче

```json
{
  "order_number": "ORD-20261109-aaaa01",
  "status": "ready",
  "event_id": "1c-evt-ORD-20261109-aaaa01-02",
  "source": "1c",
  "occurred_at": "2026-11-09T18:30:00+03:00"
}
```

### 4.3. Оплата наличными

```json
{
  "order_number": "ORD-20261109-aaaa01",
  "payment": {
    "status": "paid",
    "method": "cash",
    "amount": "25990.00",
    "currency": "RUB",
    "payment_reference": "PAY-100025-01"
  },
  "event_id": "1c-pay-ORD-20261109-aaaa01-01",
  "source": "1c",
  "occurred_at": "2026-11-09T18:45:00+03:00"
}
```

### 4.4. Выдача + уже оплачен (комбо)

```json
{
  "order_number": "ORD-20261109-aaaa01",
  "status": "closed",
  "result": "completed",
  "payment": {
    "status": "paid",
    "method": "cash",
    "amount": "25990.00",
    "currency": "RUB",
    "payment_reference": "PAY-100025-01"
  },
  "event_id": "1c-evt-ORD-20261109-aaaa01-04",
  "source": "1c",
  "occurred_at": "2026-11-09T19:00:00+03:00"
}
```

### 4.5. Отмена

```json
{
  "order_number": "ORD-20261109-aaaa01",
  "status": "closed",
  "result": "cancelled",
  "event_id": "1c-evt-ORD-20261109-aaaa01-05",
  "source": "1c",
  "occurred_at": "2026-11-09T19:10:00+03:00"
}
```

## 5. Ответы сайта

### Успех — `200`

```json
{
  "success": true,
  "order_number": "ORD-20261109-aaaa01",
  "order_status": "ready",
  "closure_result": null,
  "payment_status": "paid",
  "duplicate": false,
  "message": "Order updated successfully"
}
```

### Повтор `event_id` — `200`

```json
{
  "success": true,
  "order_number": "ORD-20261109-aaaa01",
  "duplicate": true,
  "message": "Event already processed"
}
```

### Ошибки

| HTTP | `error` | Когда |
|---|---|---|
| 401 | `unauthorized` | Нет / неверный токен |
| 400 | `invalid_json` / `event_id_required` / … | Плохие данные |
| 404 | `order_not_found` | Нет заказа с таким `order_number` |
| 409 | `invalid_transition` / `amount_mismatch` / `order_closed` | Конфликт бизнес-правил |
| 503 | `inbound_disabled` | Токен на сервере не задан |

При временной сетевой ошибке **повторяйте тот же `event_id`** — сайт не применит событие дважды.

## 6. Связь с исходящим обменом

Сайт → 1С (как раньше): создание заказа, `paid=true` после ЮKassa, отмена с сайта.  
1С → сайт (этот документ): `processing` / `ready` / выдача / отмена / оплата в магазине.

Номер заказа для поиска на сайте: поле `orderNumber` из исходящего `SiteOrders/orders`.
