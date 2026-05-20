#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/restore_mongo.sh backups/mongo/YYYYMMDD_HHMMSS/mongo.archive"
  exit 1
fi

BACKUP_ARCHIVE="$1"

if [ ! -f "$BACKUP_ARCHIVE" ]; then
  echo "Backup archive not found: $BACKUP_ARCHIVE"
  exit 1
fi

echo "This will restore MongoDB from: $BACKUP_ARCHIVE"
echo "Existing documents in restored collections may be overwritten."
read -r -p "Continue? Type RESTORE to proceed: " CONFIRMATION

if [ "$CONFIRMATION" != "RESTORE" ]; then
  echo "Restore cancelled."
  exit 1
fi

docker exec -i fraud-pdf-mongodb mongorestore --archive --drop < "$BACKUP_ARCHIVE"

echo "MongoDB restore completed."
