#!/bin/sh
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
RETENTION_DAYS=${RETENTION_DAYS:-7}
TS=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/vibeanalytix_${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting pg_dump to $FILE"
pg_dump -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "$FILE"

echo "[backup] Removing backups older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -type f -name '*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete

echo "[backup] Backup completed"
