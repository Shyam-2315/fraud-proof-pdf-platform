# PDFCraft / Fraud Proof PDF Platform

PDFCraft is a customer-facing SaaS for generating downloadable PDFs with anonymous and authenticated usage limits. Fraud Proof PDF Platform is the internal backend and admin system used to enforce abuse-prevention rules, monitor usage signals, investigate suspicious activity, and manage ML-assisted fraud monitoring.

The platform is designed to be fraud-resistant rather than "fraud proof": the customer experience stays simple, while the backend combines multi-signal identity continuity, rule-based risk scoring, rate limiting, auditability, and optional ML-assisted monitoring.

## What Problem It Solves

- Gives customers a clean PDF generation workflow with account-based usage control.
- Preserves a simple free tier without exposing internal fraud controls in the customer UI.
- Helps internal reviewers detect repeated limit bypass attempts across cookies, storage resets, device fingerprints, behavior, and network signals.
- Supports a reviewable path from explainable rules to candidate ML models.

## Main Features

- Anonymous two-PDF limit
- Customer signup, login, token refresh, logout, and account usage views
- Logged-in monthly usage limits by plan
- Secure PDF download with ownership checks
- Customer/admin separation
- Internal admin dashboard
- Fraud events, decision history, and audit logs
- Identity graph and feature snapshots
- Rule engine and ML fraud engine
- Synthetic fraud dataset generation
- Candidate training, versioning, activation, and rejection
- Health, readiness, backup, and deployment scripts

## Architecture Overview

- `frontend/`: customer-facing PDFCraft app
- `pdfcraft-guardian-main/`: internal admin dashboard
- `backend/`: FastAPI API, persistence, abuse-prevention logic, and ML services
- `deploy/`: reverse proxy configuration
- `scripts/`: operational checks and backup helpers
- `docs/`: deployment notes, architecture notes, demo/report material, and review docs

Local ports are fixed:

| Service | URL / Port |
| --- | --- |
| Customer frontend | `http://localhost:3025` |
| Admin frontend | `http://localhost:3035/admin/login` |
| Backend API | `http://localhost:8025` |
| MongoDB host port | `27225` |
| Redis host port | `6385` |

## Folder Structure

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

## Tech Stack

- Backend: FastAPI, Pydantic, MongoDB, Redis
- Customer frontend: React, Vite, TypeScript
- Admin frontend: React, Vite, TypeScript, TanStack Router
- Deployment: Docker Compose, Nginx
- Free hosting option: Render, Vercel, MongoDB Atlas, Upstash Redis
- ML: scikit-learn-based fraud model training and versioning

## Local Setup

1. Copy or allow the startup script to create local env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp pdfcraft-guardian-main/.env.example pdfcraft-guardian-main/.env
```

2. Start the stack:

```bash
./start.sh
```

3. Stop the stack:

```bash
./stop.sh
```

## URLs

- Customer app: `http://localhost:3025`
- Admin app: `http://localhost:3035/admin/login`
- Backend: `http://localhost:8025`
- Health: `http://localhost:8025/health`
- Ready: `http://localhost:8025/ready`
- Public config: `http://localhost:8025/api/public/config`
- API docs: `http://localhost:8025/docs` when `ENABLE_API_DOCS=true`

## Customer Demo Flow

1. Open the customer app.
2. Generate two PDFs anonymously.
3. Attempt a third generation and confirm the login/signup gate.
4. Register or log in.
5. Generate PDFs as an authenticated customer.
6. Review `/usage`, `/history`, and `/account`.
7. Download a previously generated PDF.

Customer-facing screens and API responses should not expose fraud, ML, identity graph, or internal risk terminology.

## Admin Demo Flow

1. Open `http://localhost:3035/admin/login`.
2. Authenticate with the seeded admin account or admin API key in local development.
3. Review dashboard, events, visitors, PDF activity, audit logs, and investigation details.
4. Use the ML section to inspect the active model and start candidate training.

## ML Fraud Engine Demo

```bash
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
```

Key internal capabilities:

- Multi-signal visitor identity continuity
- Explainable rule scoring and decision reasons
- Synthetic bootstrapping data for cold-start training
- Candidate model registry and safe activation flow
- Rule-engine fallback when no active model is available

## Testing Commands

```bash
python3 -m compileall -q backend/app backend/scripts backend/tests
docker compose config
docker compose -f docker-compose.prod.yml config
docker exec -it fraud-pdf-backend python -m pytest
docker exec -it fraud-pdf-frontend npm run build
docker exec -it fraud-pdf-admin-frontend npm run build
python3 scripts/check_production_env.py --env backend/.env.production.example
```

## Cleanup / Review Notes

- Generated caches, build artifacts, tracked local env files, and Windows metadata files were removed from the repo surface.
- Dead customer-frontend admin/TanStack route leftovers were removed; the separate admin app remains in `pdfcraft-guardian-main/`.
- Local development ports were preserved.
- Demo/report docs and ML/fraud engine code were kept.

See [docs/CODE_REVIEW_READY.md](docs/CODE_REVIEW_READY.md) and [docs/CLEANUP_REPORT.md](docs/CLEANUP_REPORT.md).

## Deployment Guide

Use [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the VPS + Docker Compose deployment path.

For free-tier review/demo hosting, use [docs/FREE_HOSTING.md](docs/FREE_HOSTING.md).

Expected production domains are placeholders:

- Customer: `https://pdfcraft.yourdomain.com`
- Admin: `https://admin.pdfcraft.yourdomain.com`
- API: `https://api.pdfcraft.yourdomain.com`

## Security Notes

- Do not commit local `.env` files.
- Replace all placeholder secrets before production deployment.
- Keep MongoDB and Redis private in production.
- Enable secure cookies and trusted proxy headers only in the intended production topology.
- Keep internal fraud terminology out of the customer frontend.
- The admin dashboard stores admin credentials in `sessionStorage`, not in source code.

## Free Hosting Option

Recommended free-tier split:

- customer frontend on Vercel from `frontend/`
- admin frontend on Vercel from `pdfcraft-guardian-main/`
- backend on Render from `backend/`
- MongoDB Atlas M0
- Upstash Redis free tier

This keeps local Docker development unchanged while allowing online review without a VPS.

## Known Limitations

- Local development uses Docker volumes for PDFs and model artifacts; multi-instance production should move these to shared storage.
- On free hosting, generated PDFs and model artifacts may be temporary because Render filesystem storage is ephemeral. For production, use object storage such as S3 or Cloudflare R2.
- Refresh tokens are still handled client-side for the customer app; a stricter production setup should move refresh handling to secure HttpOnly cookies.
- The ML engine is intended for decision support and monitoring, not as a sole enforcement mechanism.
- Online ML training is disabled by default for free hosted demos; train locally and publish model files separately if needed.

## Next Improvements

- Move generated PDFs and model artifacts to object storage for horizontal scale.
- Add stronger secret management for production deployments.
- Add CI checks for builds, tests, and forbidden customer-facing terminology scans.
- Add observability for fraud decision drift and model performance over time.
