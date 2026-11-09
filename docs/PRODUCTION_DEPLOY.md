# Ringoo — Production Deployment (источник истины)

**Актуально с:** 2026-11-07 (Block 5)
**Устарело:** `docs/DEPLOYMENT.md` (исторический черновик; используйте этот файл + чеклисты ниже).

Связанные чеклисты:

- `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` — пошаговый VPS checklist
- `docs/FINAL_DEPLOYMENT_CHECKLIST.md` — soft launch без live pay/1С (`ringoo15.store`)
- `docs/ops/ROLLBACK_PROCEDURE.md`
- `docs/ops/BACKUP_AND_RESTORE.md`
- `docs/ops/VPS_FIREWALL_AND_TLS.md`
- `docs/ops/ADMIN_MFA_SETUP.md`

## Требования

| Компонент | Минимум |
|-----------|---------|
| ОС | Ubuntu 20.04+ (или аналог) |
| Docker Engine | актуальный stable |
| Docker Compose | **≥ 2.24** (`!override`, `ports: !reset`) |
| RAM / CPU | ≥ 2 GB / 2 vCPU |
| Диск | ≥ 20 GB + запас под media/backups/logs |

## Файлы конфигурации

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | Базовый стек (dev публикует DB/Redis — **не** для VPS в одиночку) |
| `docker-compose.prod.yml` | Overlay: gunicorn, `node server.js`, закрытые DB/Redis, restart |
| `.env.production` | Секреты и prod flags (из `.env.production.example`, **не в Git**) |
| `.env.backup` | Опционально для host scripts (`scripts/backup-set.sh`) |

Каноническая команда:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production config

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
```

Рекомендуемые теги образов: `RINGOO_IMAGE_TAG=<git-sha>` или semver; `RINGOO_GIT_SHA` / `RINGOO_RELEASE` попадают в `/health/`.

## Обязательные переменные (имена, без значений)

`SECRET_KEY`, `DATABASE_URL`, `DB_NAME`, `DB_PASSWORD`, `POSTGRES_BOOTSTRAP_PASSWORD`, `REDIS_URL`, `REDIS_PASSWORD`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `NEXT_PUBLIC_API_V1_URL`, `NEXT_PUBLIC_SITE_URL`, `DJANGO_SETTINGS_MODULE=config.settings.production`.

## Флаги первого запуска (выключено)

```text
YOOKASSA_ENABLED=0
YOOKASSA_TEST_MODE=1
NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0
SBER_ECOM_ENABLED=false
ONE_C_API_ENABLED=false
ONE_C_ORDER_SYNC_ENABLED=false
ONE_C_SYNC_PARTNER_ON_REGISTER=false
ONE_C_CATALOG_SYNC_ENABLED=0
BACKUP_OFFSITE_ENABLED=0
RETURNS_ENABLED=0
ADMIN_OTP_ENABLED=1
DEBUG=False
```

## Порядок запуска (кратко)

1. DNS A-записи → VPS IP
2. Firewall: 22 (ограниченно), 80, 443; **не** 5432/6379/8000/3000 снаружи
3. `.env.production`
4. `compose config` проверка
5. `up -d --build`
6. Backup пустой/новой БД (если уже есть данные — полный backup)
7. `migrate --noinput`
8. `collectstatic --noinput`
9. `createsuperuser` + TOTP (`docs/ops/ADMIN_MFA_SETUP.md`)
10. Caddy/Nginx TLS (`docs/ops/caddy.ringoo15.store.caddyfile`)
11. `GET /health/` → healthy; главная / каталог smoke
12. Настроить cron `scripts/backup-set.sh` + (позже) offsite

## Обновление релиза

См. `docs/ops/ROLLBACK_PROCEDURE.md` и чеклист PRODUCTION. Перед migrate — backup DB+Media.

## Инциденты

Операторский runbook: `docs/ops/RINGOO_OPERATOR_RUNBOOK.md`.
