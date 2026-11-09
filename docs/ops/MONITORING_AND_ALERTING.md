# Monitoring and alerting — Ringoo

Объединяет и дополняет: `MONITORING_OPS_ALERTS.md`, `EXTERNAL_MONITORING_SETUP.md`.

## Health

| Endpoint | Содержание | Публичность |
|----------|------------|-------------|
| `GET /health/` | Django + PostgreSQL + Redis; `git_sha` / `release` | Да (LB) |
| `OPS_HEALTH_DETAILS=1` | + counters needs_review / backup / stale online | **Только** внутренний probe / IP allowlist |

Не включайте ops-details на публичном edge без ограничения доступа.

## Что мониторить снаружи

- HTTPS главной (`https://ringoo15.store/`) — 2xx
- `https://…/health/` — 200 + `"status":"healthy"`
- TLS expiry (внешний checker)
- HTTP 5xx rate у reverse proxy

Интервалы (рекомендация, не утверждённый SLA): health каждые 1–5 мин; alert после 2–3 подряд неудач.

## Celery

```bash
docker compose … ps celery celery-beat
docker compose … logs celery celery-beat --tail=200
python manage.py report_ops_alerts --json
```

Контроль: worker/beat up; expire unpaid; reconcile; отсутствие вечного `already_running` на catalog sync; рост failed tasks в логах.

Beat критичен для истечения онлайн-резервов — при остановке Beat растёт `orders_stale_new_online_30m`.

## Backup alerts

- Нет `BackupArchive` READY дольше `BACKUP_STALE_ALERT_HOURS`
- `backup_failed_24h` > 0
- Host cron: успешный `scripts/backup-set.sh` (exit 0) + свежий `set_*/MANIFEST.txt`

## Диск и логи

- Docker json-file: в daemon.json ограничить `max-size`/`max-file` (рекомендация 50m × 5)
- Application: RotatingFileHandler `/app/logs/django.log` (10 MB × 5)
- Следить: media volume, `backups/`, docker volumes

## Канал уведомлений

Telegram/Slack — только после выдачи секретов владельцем (`EXTERNAL_MONITORING_SETUP.md`).
Не коммитить bot tokens. До настройки — cron + mail/log file на VPS.
