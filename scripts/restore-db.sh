#!/usr/bin/env bash
# Восстановление БД PostgreSQL из сжатого дампа.
# Использование: ./scripts/restore-db.sh <файл.sql.gz> [--drop]
# Пример: ./scripts/restore-db.sh backups/ringoo_db_20260310_030000.sql.gz
# С опцией --drop перед восстановлением удаляются все объекты в БД (полная замена).

set -euo pipefail

if [ $# -lt 1 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage: $0 <backup.sql.gz> [--drop]"
  echo "  backup.sql.gz  Path to gzipped pg_dump file"
  echo "  --drop         Drop all objects in DB before restore (full replace)"
  exit 1
fi

DUMP_FILE="$1"
DROP_BEFORE="${2:-}"

if [ ! -f "$DUMP_FILE" ]; then
  echo "Error: file not found: $DUMP_FILE"
  exit 2
fi

DB_CONTAINER="${DB_CONTAINER:-ringoo_db}"
DB_NAME="${DB_NAME:-ringoo}"
DB_USER="${DB_USER:-postgres}"

echo "[restore-db] Restoring from $DUMP_FILE into container $DB_CONTAINER"

if [ "$DROP_BEFORE" = "--drop" ]; then
  echo "[restore-db] Dropping existing objects..."
  docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    DO \$\$ DECLARE r RECORD;
    BEGIN
      FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
      END LOOP;
      FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequence_name) || ' CASCADE';
      END LOOP;
    END \$\$;
  " 2>/dev/null || true
fi

gunzip -c "$DUMP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1
echo "[restore-db] Done."
echo "[restore-db] Run: make migrate (if schema may have changed)."