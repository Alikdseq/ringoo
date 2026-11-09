# ЮKassa — готовность к live (не включать без согласования)

**Статус на 2026-11-07:** production online payment **выключен** (`YOOKASSA_ENABLED=0`, `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0`).

## Уже реализовано (код)

- Создание платежа с суммой из `Order.total_amount`
- `Idempotence-Key` = id локального Payment
- Webhook → **не** trust payload: re-fetch GET API + сумма/метаданные
- Один PAID на заказ (constraint)
- Expire unpaid + release reserve (FUNC-001)
- Repay после failed/expired; `form_url` очищается у закрытых платежей
- Опциональный `YOOKASSA_WEBHOOK_IP_ALLOWLIST` (пусто = только trust-by-GET)
- Тесты: `test_yookassa_*`, `test_sec007_*`, `test_payment_security`, `test_order_repay`

## Протестировано

- Unit/mock HTTP
- Не live webhook delivery
- Не боевые ключи

## Нужно перед live

1. Sandbox shop + `test_` secret, webhook URL на HTTPS staging
2. Реальный webhook от ЮKassa (succeeded / canceled)
3. Сценарии: закрытие вкладки, повторная оплата, expire резерва, late pay policy
4. Мониторинг `needs_review`
5. Согласование `LATE_ONLINE_PAYMENT_POLICY`
6. Только после soft launch: `YOOKASSA_TEST_MODE=0` + live keys **вне Git**

## Оператор: зависший платёж

1. Не ставить paid вручную.
2. `report_ops_alerts` / админка платежей.
3. Сверка GET в кабинете ЮKassa.
4. Разработчик: sync / needs_review.

## Двойное списание

Защита: unique paid, sync checks, eligibility. Residual: два confirmation URL до expiry старого на стороне ЮKassa — второй PAID отклоняется; деньги при сбое — ручная сверка.
