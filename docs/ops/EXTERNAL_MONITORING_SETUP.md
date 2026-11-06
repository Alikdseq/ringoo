# Внешний мониторинг и уведомления Ringoo

Внутренние источники уже есть:

- `python manage.py report_ops_alerts` / `--json`
- `GET /health/` при `OPS_HEALTH_DETAILS=1`
- `docs/ops/MONITORING_OPS_ALERTS.md`
- `python manage.py monitor_hung_payments`

Этот документ описывает **безопасное подключение внешнего канала** (рекомендуется Telegram) без блокировки основного магазина.

## 1. Какие события считать важными

| Событие | Условие | Важность | Источник | Действие |
|---------|---------|----------|----------|----------|
| Платежи `needs_review` | count > 0 | Critical | `report_ops_alerts` | Сверка с ЮKassa/Сбер, не «гадать» статус |
| Ошибки обмена 1С | `orders_onec_error` > 0 | High | то же | Лог sync, склад клиента |
| Зависшие online NEW | > N минут | High | то же | Celery expire / провайдер |
| Ошибки backup 24h | `backup_failed_24h` > 0 | High | то же + `/health` ops | Повторить из админки, проверить диск/`pg_dump` |
| Нет свежих backup | `backup_stale` | Medium | то же | Создать копию вручную |
| Locks expire/reconcile | long hold | Medium | cache keys | Проверить воркеры |
| Celery / Beat down | process/heartbeat | Critical | внешний process check | Restart worker/beat |
| Расхождение склада | сверка 1С vs Stock | High | импорт/ручная | Не авто-править без решения |

Повторяющиеся алерты: отправлять не чаще 1 раза в N минут на один `alert_key` (дедуп в Redis).

## 2. Почему Telegram

В проекте уже заложены ops-команды и JSON-отчёты; Telegram бот — простой канал для владельца без новой шины событий. Slack допустим тем же адаптером.

**Не создавать** отдельный микросервис только ради алертов.

## 3. Архитектура (безопасная)

```
cron / beat → report_ops_alerts --json
           → thin notifier (optional manage.py notify_ops_alerts)
           → Telegram Bot API (timeout short, fail-open)
```

Правила:

1. Нотификатор **никогда** не кидает исключение в платёжный/заказный код.
2. В сообщении **нет** ФИО, телефонов, email, полных order UUID при желании маскировать до 8 символов, нет сумм карт.
3. Секреты только в env: `OPS_TELEGRAM_BOT_TOKEN`, `OPS_TELEGRAM_CHAT_ID`.
4. Логировать `ops_notify ok|fail` без тела с PII.
5. Retry: 2–3 попытки с backoff; при неуспехе — запись в лог, exit code для cron.
6. Дедуп: `cache.set(f"ops_alert:{key}", 1, timeout=900)`.

## 4. Параметры для подключения (владелец предоставляет)

| Переменная | Назначение |
|------------|------------|
| `OPS_TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `OPS_TELEGRAM_CHAT_ID` | ID чата/группы (отрицательный для групп) |
| `OPS_NOTIFY_ENABLED` | `0`/`1` — выключатель |
| `OPS_NOTIFY_DEDUP_SECONDS` | Например `900` |

Не коммитить реальные значения. Добавить в `.env.example` пустые ключи при подключении кода нотификатора.

## 5. Минимальный cron (без кода нотификатора)

Пока нотификатор не задеплоен:

```cron
*/10 * * * * cd /app && python manage.py report_ops_alerts --json >> /var/log/ringoo-ops.jsonl
```

Внешний uptime-check: `GET https://<host>/health/` каждые 1–5 мин (ожидать 200 + `"status":"healthy"`).

## 6. Проверка после подключения секретов

1. `OPS_NOTIFY_ENABLED=1` на staging.
2. Создать тестовый `Payment` со статусом `needs_review` **только на staging**.
3. Запустить `report_ops_alerts` + notifier.
4. Убедиться, что сообщение пришло без PII.
5. Повторный запуск в окне дедупа — без спама.
6. Выключить тестовый алерт.

## 7. Статус на момент закрытия блока №4

- Внутренний сбор метрик: **реализован** (включая backup stale/failed).
- Внешняя доставка в Telegram/Slack: **документирована, секреты не подключены** (`NOT IMPLEMENTED` до предоставления токена/chat_id).
