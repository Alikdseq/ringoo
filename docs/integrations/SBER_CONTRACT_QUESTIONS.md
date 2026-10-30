# Вопросы к Сберу / эквайрингу (контракт callback и статуса)

Собрано по **текущему коду** Ringo (`integrations/sber`, `apps/payments`). Не менять реализацию подписи, пока нет официального ответа.

## Текущая реализация (факт)

- Регистрация: `register.do` (одностадийная).
- Подтверждение оплаты: только `getOrderStatusExtended` → `orderStatus=2` и `actionCode=0`.
- Callback: принимается как сигнал; payload `operation`/`status` **не** считаются доказательством оплаты.
- Дополнительно: optional shared secret `SBER_ECOM_CALLBACK_TOKEN` (`?token=` / `X-Sber-Callback-Token`).
- Перед `paid`: сверка `amount`, `orderNumber`, `currency` с локальным `Payment`.
- Checksum/HMAC callback в коде **не** реализован (в доступной OpenAPI проекта не подтверждён как обязательный).

## Вопросы

1. **Подпись callback.** Поддерживается ли официальная криптографическая подпись / checksum для callback в используемом протоколе (ecom REST)? Если да — алгоритм, канонизация тела, заголовок/поле, окно timestamp.
2. **Подлинность без подписи.** Какие механизмы банк считает достаточными (static callback URL + merchant credentials на status API, IP allowlist, mTLS)?
3. **Обязательные поля status API.** Какие поля `getOrderStatusExtended` всегда присутствуют при успешной оплате (`amount`, `orderNumber`, `currency`, `orderStatus`, `actionCode`, …)?
4. **Финальный успех.** Точная матрица `orderStatus` + `actionCode` для deposited/оплачено в одностадийной схеме; отличия двухстадийной, если появится.
5. **Сопоставление с заказом мерчанта.** Гарантирует ли банк, что `orderNumber` в status = наш `orderNumber` при запросе по `orderId` (`mdOrder`)?
6. **Повторная доставка callback.** Политика retries: интервалы, условие остановки, ожидаемый HTTP-код от мерчанта, идемпотентность на стороне банка.
7. **dynamicCallbackUrl.** Можно ли передавать query-параметр с секретом; сохраняется ли он при доставке; поддерживается ли кастомный заголовок.
8. **IP-адреса** исходящих callback (для firewall allowlist), тест vs бой.
9. **Возвраты / reverse.** Какие статусы приходят и нужно ли повторно звать status API.
10. **Таймауты.** Рекомендуемый timeout мерчанта к status API; поведение при 5xx мерчанта на callback.

Ответы зафиксировать в `docs/integrations/` и только затем менять код проверки подписи.
