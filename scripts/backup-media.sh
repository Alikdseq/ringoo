#!/usr/bin/env bash
# Резервное копирование медиафайлов (изображения, 3D-модели) из Docker volume.
# Использование: ./scripts/backup-media.sh [каталог_бэкапов]
# По умолчанию каталог: ./backups (от корня проекта).
# Имя volume: из docker-compose (по умолчанию ringoo_media_volume).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${1:-$PROJECT_ROOT/backups}"
MEDIA_VOLUME="${MEDIA_VOLUME:-ringoo_media_volume}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/ringoo_media_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup-media] Creating media backup: $FILE"
# Тар из volume в stdout, сжатие на хосте
if docker run --rm -v "$MEDIA_VOLUME":/media:ro alpine tar -c -C /media . 2>/dev/null | gzip -9 > "$FILE"; then
  echo "[backup-media] Done. Size: $(du -h "$FILE" | cut -f1)"
else
  echo "[backup-media] Volume empty or missing, writing empty archive"
  echo -n "" | gzip -9 > "$FILE"
  echo "[backup-media] Done. Size: $(du -h "$FILE" | cut -f1)"
fi
