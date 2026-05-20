#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_DIR="backups/storage"
ARCHIVE_PATH="${BACKUP_DIR}/${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

docker run --rm \
  -v fraud_pdf_pdf_storage:/data/pdfs:ro \
  -v fraud_pdf_model_storage:/data/models:ro \
  -v "$(pwd)/${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  tar -czf "/backup/${TIMESTAMP}.tar.gz" -C /data .

echo "Storage backup written to ${ARCHIVE_PATH}"
