#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_DIR="backups/mongo/${TIMESTAMP}"
ARCHIVE_PATH="${BACKUP_DIR}/mongo.archive"

mkdir -p "$BACKUP_DIR"

docker exec fraud-pdf-mongodb mongodump --archive > "$ARCHIVE_PATH"

echo "MongoDB backup written to ${ARCHIVE_PATH}"
