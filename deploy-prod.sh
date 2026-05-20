#!/usr/bin/env bash
set -euo pipefail

BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-./backend/.env.production}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-./frontend/.env.production}"

if [ ! -f "$BACKEND_ENV_FILE" ]; then
  echo "Missing $BACKEND_ENV_FILE. Copy backend/.env.production.example and replace placeholders."
  exit 1
fi

if [ ! -f "$FRONTEND_ENV_FILE" ]; then
  echo "Missing $FRONTEND_ENV_FILE. Copy frontend/.env.production.example and set VITE_API_BASE_URL."
  exit 1
fi

python3 scripts/check_production_env.py --env "$BACKEND_ENV_FILE"

set -a
source "$FRONTEND_ENV_FILE"
set +a

export BACKEND_ENV_FILE

docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "Production stack started."
echo "Frontend URL: ${FRONTEND_URL:-https://your-domain.com}"
echo "Backend URL:  ${BACKEND_PUBLIC_URL:-https://api.your-domain.com}"
