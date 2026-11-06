#!/usr/bin/env bash
# Encrypted PostgreSQL backup (age). Does not print secrets.
# Requires: age, docker, gzip.
# Usage: ./scripts/backup-db-encrypted.sh
# Env: see .env.backup.example (AGE_RECIPIENT, DB_*).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/.env.backup" ]]; then
  # shellcheck disable=SC1091
  set -a
  # Do not echo values
  source "$PROJECT_ROOT/.env.backup"
  set +a
fi

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
DB_CONTAINER="${DB_CONTAINER:-ringoo_db}"
DB_NAME="${DB_NAME:-ringoo}"
DB_USER="${DB_USER:-ringoo_admin}"
AGE_RECIPIENT="${AGE_RECIPIENT:-}"

if [[ -z "$AGE_RECIPIENT" ]]; then
  echo "[backup-db-encrypted] Set AGE_RECIPIENT (see .env.backup.example)" >&2
  exit 1
fi

if ! command -v age >/dev/null 2>&1; then
  echo "[backup-db-encrypted] age CLI not found" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PLAIN="$BACKUP_DIR/ringoo_db_${TIMESTAMP}.sql.gz"
ENC="${PLAIN}.age"

echo "[backup-db-encrypted] Dumping to encrypted archive…"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
  | gzip -9 \
  | age -r "$AGE_RECIPIENT" -o "$ENC"

# Never leave plaintext dump
rm -f "$PLAIN" 2>/dev/null || true
echo "[backup-db-encrypted] Done: $ENC"
echo "[backup-db-encrypted] Offsite copy is operator responsibility (NOT VERIFIED by default)."
