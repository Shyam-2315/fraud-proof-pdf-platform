#!/usr/bin/env bash
set -euo pipefail

BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-./backend/.env.production}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-./frontend/.env.production}"
ADMIN_FRONTEND_ENV_FILE="${ADMIN_FRONTEND_ENV_FILE:-./pdfcraft-guardian-main/.env.production}"

if [ ! -f "$BACKEND_ENV_FILE" ]; then
  echo "Missing $BACKEND_ENV_FILE. Copy backend/.env.production.example and replace placeholders."
  exit 1
fi

if [ ! -f "$FRONTEND_ENV_FILE" ]; then
  echo "Missing $FRONTEND_ENV_FILE. Copy frontend/.env.production.example and set VITE_API_BASE_URL."
  exit 1
fi

if [ ! -f "$ADMIN_FRONTEND_ENV_FILE" ]; then
  echo "Missing $ADMIN_FRONTEND_ENV_FILE. Copy pdfcraft-guardian-main/.env.production.example and set VITE_API_BASE_URL."
  exit 1
fi

python3 scripts/check_production_env.py --env "$BACKEND_ENV_FILE"

read_env_value() {
  local env_file="$1"
  local key="$2"
  local value
  value="$(grep -E "^${key}=" "$env_file" | head -n 1 | cut -d '=' -f 2-)"
  printf '%s' "$value"
}

export VITE_API_BASE_URL
export VITE_APP_NAME
export VITE_APP_ENV
export ADMIN_VITE_API_BASE_URL
export ADMIN_VITE_APP_NAME
export ADMIN_VITE_APP_ENV

VITE_API_BASE_URL="$(read_env_value "$FRONTEND_ENV_FILE" "VITE_API_BASE_URL")"
VITE_APP_NAME="$(read_env_value "$FRONTEND_ENV_FILE" "VITE_APP_NAME")"
VITE_APP_ENV="$(read_env_value "$FRONTEND_ENV_FILE" "VITE_APP_ENV")"

ADMIN_VITE_API_BASE_URL="$(read_env_value "$ADMIN_FRONTEND_ENV_FILE" "VITE_API_BASE_URL")"
ADMIN_VITE_APP_NAME="$(read_env_value "$ADMIN_FRONTEND_ENV_FILE" "VITE_APP_NAME")"
ADMIN_VITE_APP_ENV="$(read_env_value "$ADMIN_FRONTEND_ENV_FILE" "VITE_APP_ENV")"

export BACKEND_ENV_FILE

docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "Production stack started."
echo "Frontend URL: ${FRONTEND_URL:-https://pdfcraft.your-domain.com}"
echo "Admin URL:    ${ADMIN_FRONTEND_URL:-https://admin.pdfcraft.your-domain.com}"
echo "Backend URL:  ${BACKEND_PUBLIC_URL:-https://api.pdfcraft.your-domain.com}"
