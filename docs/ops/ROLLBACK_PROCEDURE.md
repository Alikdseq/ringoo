# Rollback procedure — Ringoo

**Не выполнять destructive rollback на production без согласования.**

## Идентификация версии

- Env: `RINGOO_GIT_SHA`, `RINGOO_RELEASE`, `RINGOO_IMAGE_TAG`
- HTTP: `GET /health/` → поля `git_sha`, `release` (без секретов)
- Образы: `ringoo-web:<tag>`, `ringoo-frontend:<tag>`, celery с тем же tag

## A. Ошибка приложения без изменения схемы БД

Подходит, если **не** применяли новые миграции (или миграции обратно-совместимы).

1. Зафиксировать текущий tag/SHA и симптомы.
2. Убедиться, что предыдущие образы доступны локально или в registry.
3. В `.env.production` выставить предыдущий `RINGOO_IMAGE_TAG` / SHA.
4. Перезапустить без `--build` (или pull старого tag):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d
```

5. Проверить: `/health/`, главная, каталог, корзина, API login.
6. Celery worker + beat должны быть на том же tag, что web.

**Не** откатывать volumes PostgreSQL в этом сценарии.

## B. Ошибка после миграции БД

Автоматический `migrate` reverse **не** рекомендуется.

1. Остановить приём трафика (maintenance / firewall).
2. **Не** делать restore поверх prod без отдельного решения владельца.
3. На **изолированной** staging БД восстановить **pre-migration** backup (`scripts/restore-db.sh` / encrypted).
4. Оценить: может ли старый код работать с **новой** схемой (часто forward-only).
5. Если нет совместимости — план: restore drill → согласованный cutover или hotfix forward.

Документируйте RPO/RTO владельцу (`docs/ops/BACKUP_AND_RESTORE.md`).

## Запрещено

- `docker compose down -v`
- Restore поверх production без письменного разрешения
- Удаление миграций из репозитория «чтобы откатиться»
