# Восстановление Ringoo из этого архива

Полная инструкция: `docs/ops/BACKUP_RESTORE_GUIDE.md` в репозитории.

## Состав

- `database/` — дамп PostgreSQL (`.sql` / `.dump`) или SQLite / dumpdata
- `media/` — загруженные файлы (`MEDIA_ROOT`)
- `manifest.json`, `checksums.txt`
- `.env.example` — шаблон настроек **без секретов**

## Кратко

1. Расшифруйте архив (если `.enc`) паролем, заданным при создании.
2. Проверьте `checksums.txt`.
3. Восстановите БД (`psql` / `pg_restore`).
4. Скопируйте `media/` в `MEDIA_ROOT`.
5. Заполните `.env` из шаблона (секреты заново).
6. Примените миграции при необходимости и проверьте `/health/`.
