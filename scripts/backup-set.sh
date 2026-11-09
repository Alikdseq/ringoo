#!/usr/bin/env bash
# Единый backup-набор: PostgreSQL + Media (+ опционально age + SHA256).
# Использование: ./scripts/backup-set.sh [каталог]
# Env: см. .env.backup.example; AGE_RECIPIENT включает шифрование DB/Media.
# Не печатает секреты. Offsite S3 — отдельно (apps.backups / docs/ops).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/.env.backup" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env.backup"
  set +a
fi

BACKUP_DIR="${1:-${BACKUP_DIR:-$PROJECT_ROOT/backups}}"
DB_CONTAINER="${DB_CONTAINER:-ringoo_db}"
DB_NAME="${DB_NAME:-ringoo}"
DB_USER="${DB_USER:-ringoo_admin}"
MEDIA_VOLUME="${MEDIA_VOLUME:-ringoo_media_volume}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
AGE_RECIPIENT="${AGE_RECIPIENT:-}"
LOCK_FILE="${BACKUP_LOCK_FILE:-/tmp/ringoo-backup-set.lock}"
STATUS="SUCCESS"
SET_ID="$(date +%Y%m%d_%H%M%S)"
SET_DIR="$BACKUP_DIR/set_${SET_ID}"
MANIFEST="$SET_DIR/MANIFEST.txt"

mkdir -p "$BACKUP_DIR" "$SET_DIR"

cleanup_lock() {
  rm -f "$LOCK_FILE" 2>/dev/null || true
}
trap cleanup_lock EXIT

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "[backup-set] Another backup is running (lock $LOCK_FILE)" >&2
    exit 1
  fi
elif [[ -f "$LOCK_FILE" ]]; then
  echo "[backup-set] Lock file exists: $LOCK_FILE" >&2
  exit 1
else
  echo "$$" >"$LOCK_FILE"
fi

fail() {
  STATUS="FAILED"
  echo "[backup-set] FAILED: $*" >&2
  echo "status=$STATUS" >>"$MANIFEST"
  exit 1
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "unavailable"
  fi
}

echo "=== Ringoo backup-set $SET_ID $(date '+%Y-%m-%d %H:%M:%S') ==="
{
  echo "set_id=$SET_ID"
  echo "started_at=$(date -Iseconds 2>/dev/null || date)"
  echo "db_name=$DB_NAME"
  echo "db_user=$DB_USER"
  echo "media_volume=$MEDIA_VOLUME"
} >"$MANIFEST"

# 1) PostgreSQL available
docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null \
  || fail "PostgreSQL not ready"

# 2–4) Dump + gzip
DB_PLAIN="$SET_DIR/ringoo_db_${SET_ID}.sql.gz"
echo "[backup-set] Dumping database…"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
  | gzip -9 >"$DB_PLAIN" \
  || fail "pg_dump failed"
gzip -t "$DB_PLAIN" || fail "gzip integrity check failed for DB"
DB_SHA="$(sha256_file "$DB_PLAIN")"
echo "db_file=$(basename "$DB_PLAIN")" >>"$MANIFEST"
echo "db_sha256=$DB_SHA" >>"$MANIFEST"
echo "db_bytes=$(wc -c <"$DB_PLAIN" | tr -d ' ')" >>"$MANIFEST"

# 5–6) Media
MEDIA_PLAIN="$SET_DIR/ringoo_media_${SET_ID}.tar.gz"
echo "[backup-set] Archiving media…"
if docker run --rm -v "$MEDIA_VOLUME":/media:ro alpine tar -c -C /media . 2>/dev/null | gzip -9 >"$MEDIA_PLAIN"; then
  :
else
  echo -n "" | gzip -9 >"$MEDIA_PLAIN"
  echo "[backup-set] WARN: media volume empty or missing — empty archive written"
fi
gzip -t "$MEDIA_PLAIN" || fail "gzip integrity check failed for media"
MEDIA_SHA="$(sha256_file "$MEDIA_PLAIN")"
echo "media_file=$(basename "$MEDIA_PLAIN")" >>"$MANIFEST"
echo "media_sha256=$MEDIA_SHA" >>"$MANIFEST"
echo "media_bytes=$(wc -c <"$MEDIA_PLAIN" | tr -d ' ')" >>"$MANIFEST"

# 7) Optional age encryption (no plaintext left if encrypt succeeds)
if [[ -n "$AGE_RECIPIENT" ]]; then
  command -v age >/dev/null 2>&1 || fail "age CLI required when AGE_RECIPIENT is set"
  echo "[backup-set] Encrypting with age…"
  age -r "$AGE_RECIPIENT" -o "${DB_PLAIN}.age" "$DB_PLAIN" || fail "age encrypt DB failed"
  age -r "$AGE_RECIPIENT" -o "${MEDIA_PLAIN}.age" "$MEDIA_PLAIN" || fail "age encrypt media failed"
  rm -f "$DB_PLAIN" "$MEDIA_PLAIN"
  echo "encrypted=1" >>"$MANIFEST"
  echo "db_file=$(basename "${DB_PLAIN}.age")" >>"$MANIFEST"
  echo "media_file=$(basename "${MEDIA_PLAIN}.age")" >>"$MANIFEST"
  echo "db_sha256=$(sha256_file "${DB_PLAIN}.age")" >>"$MANIFEST"
  echo "media_sha256=$(sha256_file "${MEDIA_PLAIN}.age")" >>"$MANIFEST"
else
  echo "encrypted=0" >>"$MANIFEST"
  echo "[backup-set] AGE_RECIPIENT empty — plaintext gzip kept locally (encrypt before offsite)."
fi

# Release metadata (best-effort)
{
  echo "git_sha=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "finished_at=$(date -Iseconds 2>/dev/null || date)"
  echo "status=$STATUS"
} >>"$MANIFEST"

# Retention: keep set_* directories
if command -v find >/dev/null 2>&1; then
  find "$BACKUP_DIR" -maxdepth 1 -type d -name 'set_*' -mtime +"$KEEP_DAYS" -exec rm -rf {} + 2>/dev/null || true
fi

echo "[backup-set] SUCCESS set=$SET_ID dir=$SET_DIR"
echo "[backup-set] Offsite upload NOT performed by this script — use Django offsite or operator S3."
echo "=== done ==="
