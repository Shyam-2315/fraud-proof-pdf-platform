# Code Review Ready

## 1. Repository Overview

This repository contains the full PDFCraft product surface:

- customer-facing PDF generation SaaS
- internal admin dashboard
- FastAPI backend
- abuse-prevention and fraud monitoring stack
- ML training and model management scripts
- deployment and operational helpers

## 2. Folder Structure

```text
project-root/
  backend/
  frontend/
  pdfcraft-guardian-main/
  deploy/
  docs/
  scripts/
  docker-compose.yml
  docker-compose.prod.yml
  start.sh
  stop.sh
  README.md
```

## 3. What Each Major Folder Does

- `backend/`: API, business logic, persistence, rate limiting, identity graph, rule engine, ML services, and tests.
- `frontend/`: customer-facing PDFCraft UI only.
- `pdfcraft-guardian-main/`: internal admin dashboard only.
- `deploy/`: Nginx reverse-proxy configuration for production hosting.
- `docs/`: deployment guide, architecture notes, demo/report documents, and cleanup/review notes.
- `scripts/`: production env checks, backup helpers, restore helpers, and log shortcuts.

## 4. What Was Cleaned

- Removed tracked local `.env` files from the repo surface.
- Removed tracked Python cache artifacts and build/cache directories.
- Removed Windows `Zone.Identifier` metadata files.
- Removed dead customer-frontend admin code and unused TanStack route scaffolding from `frontend/`.
- Added a root `.gitignore` to keep generated data, caches, and local env files out of review diffs.
- Added missing admin production env example and tightened deploy/env documentation.

## 5. What Files Are Intentionally Ignored

- local `.env` files
- Python caches
- node modules and build output
- generated PDFs and trained model artifacts
- generated synthetic datasets
- backup archives
- temporary cookie/test files

See the root `.gitignore` for the complete list.

## 6. How To Run Locally

```bash
./start.sh
```

Local URLs:

- customer app: `http://localhost:3025`
- admin app: `http://localhost:3035/admin/login`
- backend: `http://localhost:8025`

Stop:

```bash
./stop.sh
```

## 7. How To Run Tests

```bash
python3 -m compileall -q backend/app backend/scripts backend/tests
docker exec -it fraud-pdf-backend python -m pytest
docker exec -it fraud-pdf-frontend npm run build
docker exec -it fraud-pdf-admin-frontend npm run build
```

## 8. How To Run Demo

```bash
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
```

## 9. How To Deploy

Primary reference:

- [docs/DEPLOYMENT.md](/home/snp2315/Projects/SaaS/fraud-proof-pdf-platform/docs/DEPLOYMENT.md)

Baseline commands:

```bash
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
cp pdfcraft-guardian-main/.env.production.example pdfcraft-guardian-main/.env.production
python3 scripts/check_production_env.py --env backend/.env.production
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

## 10. Known Limitations

- Generated PDFs and model artifacts still use local Docker volumes.
- Customer refresh handling is still client-managed and should move to stricter cookie-based handling for hardened production.
- The ML engine is assistive and layered behind rule-engine fallback; it is not intended as a sole control.

## 11. Security Notes

- Placeholder secrets remain only in example files.
- Customer UI should not surface fraud or ML terminology.
- MongoDB and Redis remain internal-only in production compose.
- `TRUST_PROXY_HEADERS` is intended only for the configured reverse-proxy deployment path.

## 12. What Lead Should Review First

1. `README.md`
2. `docker-compose.yml` and `docker-compose.prod.yml`
3. `backend/app/`
4. `frontend/`
5. `pdfcraft-guardian-main/`
6. `scripts/check_production_env.py`
7. `docs/DEPLOYMENT.md`
8. `docs/CLEANUP_REPORT.md`
