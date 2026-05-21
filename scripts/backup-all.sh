#!/usr/bin/env bash
# Ежедневное полное резервное копирование: БД + медиа.
# Использование: ./scripts/backup-all.sh [каталог_бэкапов]
# Рекомендуется вызывать по cron раз в сутки (например в 03:00).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${1:-$PROJECT_ROOT/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

echo "=== Ringoo backup $(date '+%Y-%m-%d %H:%M:%S') ==="
"$SCRIPT_DIR/backup-db.sh" "$BACKUP_DIR"
"$SCRIPT_DIR/backup-media.sh" "$BACKUP_DIR"

# Удаление бэкапов старше KEEP_DAYS дней
if command -v find &>/dev/null; then
  find "$BACKUP_DIR" -maxdepth 1 -name 'ringoo_db_*.sql.gz' -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
  find "$BACKUP_DIR" -maxdepth 1 -name 'ringoo_media_*.tar.gz' -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
  echo "[backup-all] Pruned backups older than $KEEP_DAYS days"
fi
echo "=== Backup finished ==="
