# PostgreSQL least privilege — Ringoo

## Цель

Runtime (web/celery) подключается как `ringoo_app` **без** SUPERUSER / CREATEDB / CREATEROLE.  
Миграции — опционально от `ringoo_migrate`.

## Файлы

- `docs/ops/postgres_app_role.sql`
- `docs/ops/postgres_migration_role.sql`
- `scripts/check_postgres_privileges.py` (read-only диагностика)

## Порядок на VPS (вручную)

1. Бэкап.
2. Подключиться как bootstrap (`ringoo_admin` / владелец тома).
3. Раскомментировать и выполнить SQL из `postgres_app_role.sql` с сильным паролем.
4. (Опционально) создать `ringoo_migrate`.
5. В `.env.production`: `DATABASE_URL=postgresql://ringoo_app:…@db:5432/ringoo`.
6. `python scripts/check_postgres_privileges.py` — убедиться, что нет Superuser / Create role / Create DB.

## Проверки в psql

```text
\du ringoo_app
\l ringoo
\dp
```

Ожидание: `Superuser` / `Create role` / `Create DB` — пусто для `ringoo_app`.

## Статус

| Проверка | Статус |
|----------|--------|
| SQL подготовлен | локально |
| Django reject имени postgres | VERIFIED (settings + tests) |
| GRANT на живой VPS БД | **NOT VERIFIED** (требует владельца) |
