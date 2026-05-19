#!/usr/bin/env bash
set -euo pipefail

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi

docker compose down -v --remove-orphans
docker container rm -f fraud-pdf-backend fraud-pdf-mongodb fraud-pdf-redis 2>/dev/null || true
docker volume rm fraud_pdf_mongo_data fraud_pdf_redis_data 2>/dev/null || true
docker network rm fraud_pdf_network 2>/dev/null || true
docker compose up --build
