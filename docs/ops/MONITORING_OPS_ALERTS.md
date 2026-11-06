# Мониторинг критических ситуаций Ringoo

**Дата:** 2026-11-06

## Что контролировать

| Сигнал | Как | Действие |
|---|---|---|
| `Payment.status=needs_review` | `manage.py report_ops_alerts` / `/health/?` при `OPS_HEALTH_DETAILS=1` | Ручная сверка с ЮKassa/Сбер |
| Ошибки Celery / Beat unhealthy | `docker compose ps`, логи worker/beat | Перезапуск worker/beat; проверить Redis |
| `Order.onec_sync_status=error` / `pending_review` | `report_ops_alerts` | Повтор sync / правка склада клиента |
| Зависшие online NEW (>30 мин) | `report_ops_alerts` | Expire task жив? Провайдер API? |
| Expire/reconcile lock «залип» | `expire_lock_held` / `reconcile_lock_held` в отчёте | TTL lock; при зависании — TTL истечёт |
| Webhook ошибки | логи `apps.payments.yookassa_service` | Throttle / API down / binding reject |
| Ошибки создания backup (24h) | `backup_failed_24h` в `report_ops_alerts` / `/health` ops | Диск, `pg_dump`, права `BACKUP_STORAGE_ROOT` |
| Нет свежей ready-копии | `backup_stale` (порог `BACKUP_STALE_ALERT_HOURS`) | Создать архив в админке «Резервное копирование» |

Внешний канал: `docs/ops/EXTERNAL_MONITORING_SETUP.md` (Telegram — после выдачи секретов).

## Команды

```bash
# внутри backend контейнера / venv
python manage.py report_ops_alerts
python manage.py report_ops_alerts --json
python manage.py monitor_hung_payments   # существующая команда
```

Cron (staging/prod, пример раз в 5–15 мин):

```bash
*/10 * * * * cd /app && python manage.py report_ops_alerts --json >> /var/log/ringoo-ops.jsonl
```

## Health endpoint

- `/health/` — DB + cache (публичный LB probe).
- При `OPS_HEALTH_DETAILS=1` добавляется блок `ops` с счётчиками. **Не включать на публичном edge без IP allowlist.**

## Celery

В локальном compose Beat/Worker могут быть `unhealthy` при отсутствии нагрузки/healthcheck — перед staging проверить:

```bash
docker compose ps
docker compose logs celery celery-beat --tail=100
```

## Ограничения

- Реальные алерты в Slack/Telegram/PagerDuty в репозитории **не подключены** — нужен внешний транспорт.
- Команда только читает БД/cache; не меняет платежи и 1С.
