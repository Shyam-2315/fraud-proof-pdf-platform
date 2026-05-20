#!/usr/bin/env bash
set -euo pipefail

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
fi

echo "Starting PDFCraft full stack..."
echo "Frontend:       http://localhost:3025"
echo "Backend health: http://localhost:8025/health"
echo "Swagger docs:   http://localhost:8025/docs"

docker compose up --build
