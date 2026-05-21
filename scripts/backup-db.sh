#!/usr/bin/env bash
# Резервное копирование БД PostgreSQL (Docker).
# Использование: ./scripts/backup-db.sh [каталог_бэкапов]
# По умолчанию каталог: ./backups (от корня проекта).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${1:-$PROJECT_ROOT/backups}"
DB_CONTAINER="${DB_CONTAINER:-ringoo_db}"
DB_NAME="${DB_NAME:-ringoo}"
DB_USER="${DB_USER:-postgres}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/ringoo_db_${TIMESTAMP}.sql.gz"

echo "[backup-db] Creating database backup: $FILE"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl | gzip -9 > "$FILE"
echo "[backup-db] Done. Size: $(du -h "$FILE" | cut -f1)"
