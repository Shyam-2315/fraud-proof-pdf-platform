#!/usr/bin/env bash
set -euo pipefail

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
fi

if [ ! -f pdfcraft-guardian-main/.env ]; then
  cp pdfcraft-guardian-main/.env.example pdfcraft-guardian-main/.env
fi

echo "Starting PDFCraft full stack..."
echo "Customer App: http://localhost:3025"
echo "Admin App: http://localhost:3035/admin/login"
echo "Backend API: http://localhost:8025"
echo "Swagger: http://localhost:8025/docs"

docker compose up --build
