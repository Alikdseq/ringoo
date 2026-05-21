#!/usr/bin/env bash
# Восстановление медиафайлов из архива в Docker volume.
# Использование: ./scripts/restore-media.sh <файл.tar.gz>
# Пример: ./scripts/restore-media.sh backups/ringoo_media_20260310_030000.tar.gz
# Внимание: текущее содержимое volume дополняется/перезаписывается файлами из архива.

set -euo pipefail

if [ $# -lt 1 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage: $0 <backup.tar.gz>"
  echo "  backup.tar.gz  Path to gzipped tar of media files"
  exit 1
fi

ARCHIVE="$1"
if [ ! -f "$ARCHIVE" ]; then
  echo "Error: file not found: $ARCHIVE"
  exit 2
fi

MEDIA_VOLUME="${MEDIA_VOLUME:-ringoo_media_volume}"

echo "[restore-media] Restoring from $ARCHIVE into volume $MEDIA_VOLUME"
gunzip -c "$ARCHIVE" | docker run --rm -i -v "$MEDIA_VOLUME":/media:rw alpine tar -x -C /media
echo "[restore-media] Done."