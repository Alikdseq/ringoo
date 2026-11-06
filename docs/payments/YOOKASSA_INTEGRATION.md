# Интеграция ЮKassa (тестовый магазин)

Актуально для Ringoo / ringoo15.store. Сбер ecom сохранён в коде, но **основной** онлайн-сценарий — ЮKassa.

## Архитектура

```
Checkout (Next.js)
  → POST /api/v1/orders/{id}/pay/
  → Django apps.payments (initiate_online_payment)
  → YooKassa API POST /v3/payments (Basic Auth, Idempotence-Key)
  → сохранение Payment (provider=yookassa)
  → form_url / confirmation_url → редирект покупателя

ЮKassa webhook
  → POST /api/v1/payments/yookassa/webhook/
  → GET /v3/payments/{id} (повторная сверка)
  → Payment.status=paid, Order.status=confirmed

Return page /orders/{id}/payment/return
  → polling GET /api/v1/orders/{id}/payment/
  → backend снова сверяет статус со шлюзом
```

Источник истины по оплате — **ответ API ЮKassa**, не return URL и не «сырой» webhook.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `YOOKASSA_ENABLED` | `1` включает провайдер |
| `YOOKASSA_TEST_MODE` | `1` (по умолчанию) — только ключи `test_…` |
| `YOOKASSA_SHOP_ID` | shopId из личного кабинета |
| `YOOKASSA_SECRET_KEY` | секретный ключ (**только backend**, никогда `NEXT_PUBLIC_*`) |
| `YOOKASSA_API_URL` | `https://api.yookassa.ru/v3` |
| `YOOKASSA_RETURN_URL` | опционально; иначе `{FRONTEND_URL}/orders/{order_id}/payment/return` |
| `YOOKASSA_WEBHOOK_URL` | справочно для ops (URL, который указывают в кабинете ЮKassa) |
| `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` | UI-флаг витрины (`1` показать «Онлайн-оплата») |
| `SBER_ECOM_ENABLED` | держать `false`, пока работает ЮKassa |

При одновременно включённых ЮKassa и Сбер runtime выбирает **только ЮKassa**.

## Получение ключей (тест)

1. Кабинет ЮKassa → тестовый магазин.
2. Скопировать **shopId** и **секретный ключ** (`test_…`).
3. Положить в `backend/.env.development` и/или корневой `.env` (для Docker Compose).
4. Не коммитить секреты.

## Локальный запуск

```bash
# корневой .env уже содержит YOOKASSA_* (gitignored)
# включить кнопку на витрине:
# NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=1

docker compose up -d --build
docker compose exec web python manage.py migrate
```

Frontend в Docker собирает `NEXT_PUBLIC_*` при `npm run build`. После смены флага удалите `.next` и пересоберите frontend-контейнер.

## Webhook

В кабинете ЮKassa укажите HTTPS URL:

```text
https://<ваш-публичный-хост>/api/v1/payments/yookassa/webhook/
```

Для локальной отладки — ngrok/cloudflare tunnel на backend `:8000`.

События: `payment.succeeded`, `payment.canceled`, `payment.waiting_for_capture` (и др. — обрабатываются через GET payment).

Обработчик:

1. Читает `object.id`
2. Запрашивает платёж у API ЮKassa
3. Сверяет сумму, валюту `RUB`, metadata (`order_id`, `payment_id`)
4. Идемпотентно ставит `paid` (unique constraint «один paid на заказ»)

## Проверка статусов

- Админка Django → Платежи: provider, yookassa_payment_id, amount, is_test, paid_at
- Celery task `reconcile_open_payments` сверяет зависшие платежи ЮKassa и Сбера
- Return-страница не считает оплату успешной только по URL

## Тестовые карты (официально ЮKassa)

В **тестовом** магазине **настоящие** банковские карты не работают — на странице ЮKassa часто показывают общее «технический сбой», при этом в API платёж остаётся `pending` без `payment_method`.

Используйте только [тестовые карты ЮKassa](https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing?lang=ru#test-bank-card):

| Номер | Система | 3‑D Secure |
|---|---|---|
| `5555 5555 5555 4444` | Mastercard | нет |
| `5555 5555 5555 4477` | Mastercard | да |
| `4111 1111 1111 1111` | Visa | нет |
| `4793 1281 6164 4804` | Visa | да |
| `2202 4743 0132 2987` | Мир | нет |
| `2200 0000 0000 0004` | Мир | да |

Срок — любая будущая дата; CVC и код 3‑D Secure — любые цифры.

Кошелёк ЮMoney в тестовом магазине проходит без реального кошелька (кнопка «Заплатить») — поэтому wallet может «работать», а карта с реальными реквизитами — нет.

## Типичные ошибки

| Симптом | Причина |
|---|---|
| 503 `yookassa_misconfigured` | Нет shopId/secret |
| 400 `yookassa_test_key_required` | `TEST_MODE=1`, но ключ не `test_…` |
| 502 `yookassa_create_failed` | Ошибка API / сеть |
| UI без «Онлайн-оплата» | `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` не `1` |
| Оплата есть, заказ new | Webhook не дошёл — откройте return page или дождитесь reconcile |
| «Технический сбой» на карте, API `pending` без `payment_method` | Часто введена **не тестовая** карта / неверные данные; Ringo-платёж уже создан корректно |
| `127.0.0.1:*` / `ERR_CONNECTION_REFUSED` в консоли | Обычно расширения браузера / локальные утилиты (напр. AnyDesk `:7070`), не ЮKassa |

## Переход на боевые ключи клиента

1. Получить **live** shopId и secret (без префикса `test_`).
2. `YOOKASSA_TEST_MODE=0`
3. Обновить `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY`
4. Проверить webhook на production HTTPS
5. `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=1` в prod build args
6. `SBER_ECOM_ENABLED=false`
7. Смоук: тестовый мини-платёж → succeeded → заказ confirmed
8. Не логировать и не коммитить секреты

## Безопасность

- Секрет только на backend
- Сумма только из `Order.total_amount`
- Доступ к `/pay/` и `/payment/`: владелец / staff / гость (`order_number` + phone)
- Webhook без доверия к payload без GET API
- Админка: статус `paid` не редактируется вручную (readonly)
- Тестовый режим блокирует live-ключ и наоборот
