# Сбербанк ecom — интернет-эквайринг Ringoo (MVP)

**Статус:** фаза A (безопасность/ops) закрыта в коде; проверка на реальном шлюзе — после тестовых доступов.
**Боевой контур не включать без отдельного подтверждения.**
**Аудит готовности:** `docs/AUDIT_READINESS_SBER_1C_KASSA.md`.
**Staging runbook:** `docs/integrations/sber-staging-runbook.md`.

## Среды

| | URL |
| --- | --- |
| Тест | `https://ecomtest.sberbank.ru` |
| Бой | `https://epay.sberbank.ru` |

Env (см. `backend/.env.example`):
`SBER_ECOM_BASE_URL`, `SBER_ECOM_USERNAME`, `SBER_ECOM_PASSWORD`, `SBER_ECOM_ENABLED`,
`SBER_ECOM_RETURN_URL` / `SBER_ECOM_FAIL_URL` / `SBER_ECOM_CALLBACK_URL`,
`ONLINE_PAYMENT_TIMEOUT_MINUTES` (по умолчанию 20),
`LATE_ONLINE_PAYMENT_POLICY` = `manual` | `revive` | `reverse`.

## Сценарий MVP

1. Создать заказ Ringoo (`payment_type=online`).
2. `POST /api/v1/orders/{id}/pay/` → `register.do` (сумма из БД) → `form_url`.
   HTTP register **вне** долгой DB-транзакции.
3. Redirect на платёжную страницу Сбера.
4. Return / callback → всегда `getOrderStatusExtended` → `Payment.status=paid`, заказ `confirmed`.
5. Неоплаченные → сверка с банком → иначе cancel + снятие резерва.
6. Оплата после cancel → `needs_review` + политика late payment (в т.ч. `reverse.do`).

Касса, 1С-заказы, SberPay, СБП — не в MVP.

## Операции

```bash
python manage.py expire_unpaid_online_orders
python manage.py reconcile_open_payments
python manage.py monitor_hung_payments --fail-on-findings
# Celery beat: expire 5 мин, reconcile 3 мин
```

Клиент: `register.do`, `getOrderStatusExtended.do`, `reverse.do`, `refund.do`.

## API

- `POST /api/v1/orders/{id}/pay/` (throttle)
- `GET /api/v1/orders/{id}/payment/`
- `POST /api/v1/payments/sber/callback/` (throttle; подлинность через re-query API)
