# Спецификация процесса возвратов Ringoo

**Статус:** техническая спецификация + DRAFT legal alignment. Реальные money API по умолчанию `dry_run=true`.

## Модели

- `ReturnRequest` — заявка, FSM статусов, основание, требование покупателя, способ возврата товара.
- `ReturnItem` — позиция/qty/сумма/снимки цвета + `condition` + `restocked_quantity`.
- `ReturnEvent` — журнал переходов.
- `MoneyRefund` — денежный контур с `idempotency_key`, отдельно от склада.

## API

- Покупатель: `POST /api/v1/returns/create/`, `GET /api/v1/returns/`, `GET /api/v1/returns/{id}/`
- Админ: `/api/v1/admin/returns/` + `transition` / `refund` / `inspect`

## Деньги

- Нельзя превысить сумму Payment.
- Идемпотентность по ключу.
- YooKassa: `create_refund` + сверка GET (существующий webhook INT-004).
- Sber: до решения владельца — `needs_review` (не авто).
- Webhook не делает restock.

## Склад

- Restock **только** после inspection и `condition=sellable` через `stock_ops.restock_at_store` → `StockMovement.OP_RESTOCK`.
- Defective/damaged/quarantine — без увеличения available.

## Частичные возвраты

Сумма линии = `price(заказа) * qty`. Общие скидки доставки — **NEEDS BUSINESS DECISION** (пока доставка не возвращается автоматически).
