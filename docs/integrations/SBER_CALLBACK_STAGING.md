# Staging: Sber callback token (без кабинета Сбера в этом документе)

Инструкция для владельца staging. **Не коммитьте реальный токен.**

## Зачем

Callback `POST /api/v1/payments/sber/callback/` публичный. Оплата всё равно подтверждается только через `getOrderStatusExtended`, но без секрета возможен flood запросов к банку. В production при `SBER_ECOM_ENABLED=true` пустой `SBER_ECOM_CALLBACK_TOKEN` запрещён (`ImproperlyConfigured`). При `DEBUG=False` пустой токен отклоняет callback (403).

## Шаги на staging

1. Сгенерировать секрет локально (значение никуда не вставлять в Git/чат):

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. В секрет-хранилище / env staging задать:

   - `SBER_ECOM_CALLBACK_TOKEN=<секрет>`
   - `SBER_ECOM_CALLBACK_URL=https://<api-host>/api/v1/payments/sber/callback/?token=<тот_же_секрет>`
   - `SBER_ECOM_ENABLED=true` (только после готовности к тестовому шлюзу)
   - `SBER_ECOM_ALLOW_PRODUCTION=false` на staging (боевой epay не включать)

3. В личном кабинете Сбера указать тот же callback URL с `?token=...` (или убедиться, что шлюз может слать заголовок `X-Sber-Callback-Token` — поддержка зависит от кабинета).

4. Проверки (мок/ручные на staging API, **без** реальной карты если не требуется):

   ```bash
   # без токена → 403
   curl -s -o /dev/null -w "%{http_code}" -X POST \
     https://<api-host>/api/v1/payments/sber/callback/ \
     -H "Content-Type: application/json" -d '{"mdOrder":"00000000-0000-0000-0000-000000000000"}'

   # с неверным токеном → 403
   curl -s -o /dev/null -w "%{http_code}" -X POST \
     "https://<api-host>/api/v1/payments/sber/callback/?token=wrong" \
     -H "Content-Type: application/json" -d '{"mdOrder":"00000000-0000-0000-0000-000000000000"}'

   # с верным токеном → 200 {"ok":true} (оплата всё равно только после сверки с банком)
   curl -s -X POST \
     "https://<api-host>/api/v1/payments/sber/callback/?token=<секрет>" \
     -H "Content-Type: application/json" -d '{"mdOrder":"<реальный mdOrder тестового платежа>"}'
   ```

5. Убедиться, что в логах приложения **нет** значения токена (логируется operation/status/mdOrder, не query string целиком).

## Dev

При `DEBUG=True` и пустом токене callback принимается (удобство локальной разработки). Для локальной имитации prod: `SBER_ECOM_CALLBACK_TOKEN_REQUIRED=true`.
