# Backup & restore — Ringoo

## Что есть в репозитории

- `scripts/backup-db.sh` — `pg_dump` + gzip (локальный файл).
- `scripts/backup-media.sh`, `scripts/backup-all.sh`.
- `scripts/restore-db.sh` — восстановление в контейнер.
- `scripts/backup-db-encrypted.sh` — dump → age encrypt (см. ниже).
- `.env.backup.example` — переменные без секретов в Git.

## Шифрование

Рекомендуется [age](https://github.com/FiloSottile/age):

1. Сгенерировать ключ **вне** VPS: `age-keygen -o ringoo-backup.key`.
2. Публичный ключ — в `.env.backup` как `AGE_RECIPIENT=age1...`.
3. Приватный ключ хранить offline / в secret manager (не в Git, не только на том же VPS).

## Offsite

Скрипты **не** настраивают S3 автоматически. После локального `.age` файла:

```bash
# пример — настройте сами
# aws s3 cp backups/ringoo_db_....sql.gz.age s3://YOUR_BUCKET/ringoo/
```

Пока offsite (S3/другой хост) не настроен владельцем → статус **NOT VERIFIED (offsite)**.

## Restore drill (безопасный)

1. Поднять **отдельную** тестовую БД/контейнер (не production volume).
2. `age -d -i ringoo-backup.key file.sql.gz.age > file.sql.gz`.
3. `gunzip -c file.sql.gz | docker exec -i TEST_DB psql -U … -d …`
4. Проверить `\dt` и smoke SELECT.

**Запрещено:** `docker compose down -v` на рабочих томах; destructive restore на prod без явного разрешения.

## Локальный drill 2026-11-06 (изолированные БД Docker `ringoo_db`)

Выполнено **без** затрагивания рабочей БД `ringoo`:

1. Созданы БД `ringoo_mig_check`, `ringoo_mig_seed`, `ringoo_concurrency_test`.
2. На `ringoo_mig_check` применены все миграции (`orders`→0010, `payments`→0003, `stores`→0007), conflicts `{}`.
3. `pg_dump ringoo_mig_check | psql ringoo_mig_seed` — dump/restore цикл успешен.
4. На seed созданы Order/Payment/Stock; nullable поля refund/guest/color совместимы со старыми строками.

**Статус dump→restore на изолированных БД:** VERIFIED (local docker).  
**Статус encrypted offsite + age drill на VPS:** по-прежнему NOT VERIFIED.

## App role

`backup-db.sh` по умолчанию использует `DB_USER` из env; для prod задайте роль с правом `pg_dump` (часто bootstrap или отдельная backup-role), не обязательно SUPERUSER.

## RPO / RTO (рекомендация)

- RPO ≤ 24h (ежедневный encrypted dump + offsite).
- RTO ≤ 4h (документированный restore drill).
