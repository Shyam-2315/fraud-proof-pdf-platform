# Fraud Proof PDF Platform

**PDFCraft** is the customer-facing PDF generation SaaS. Customers can generate PDFs, use free monthly allowance, create an account, view their own history, and download PDFs.

**Fraud Proof PDF Platform** is the internal backend and admin monitoring system. Visitor matching, fraud events, risk scoring, blocked attempts, and investigation tools are internal-only and protected.

## Current Completed Status

- Customer app runs at http://localhost:3025
- Backend runs at http://localhost:8025
- MongoDB host port is `27225`
- Redis host port is `6385`
- Anonymous users can generate 2 PDFs
- Logged-in Free users can generate 5 PDFs/month
- Customer UI hides internal fraud/ML/security details
- Admin dashboard, ML pages, visitor investigation, and audit logs are protected
- Synthetic dataset generation, candidate model training, and final demo check are available

## Quick Start

```bash
./start.sh
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
./stop.sh
```

Useful verification commands:

```bash
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
docker exec -it fraud-pdf-backend python -m pytest
docker exec -it fraud-pdf-frontend npm run build
```

Production deployment readiness is documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Production SaaS Foundation

Phase 5 adds:

- User signup, login, refresh tokens, logout, and `/api/auth/me`
- Customer roles and admin roles
- Free, Pro, and Business plan structure
- Monthly authenticated PDF limits: Free `5`, Pro `100`, Business `1000`
- Anonymous two-PDF limit preserved
- PDF download endpoint with ownership checks
- Admin access by either `X-Admin-API-Key` or admin JWT
- Default local admin seeding from environment variables
- Redis-backed rate limiting
- Security headers middleware
- Customer frontend pages for login, signup, account, and pricing

## Architecture

- Frontend: React + Vite + TypeScript + Tailwind
- Backend: FastAPI
- Database: MongoDB
- Cache/rate limit: Redis
- Customer app: PDFCraft
- Internal admin: Fraud Proof PDF Platform

## Ports

| Service | Host Port | Container Port |
| --- | ---: | ---: |
| Frontend | `3025` | `3025` |
| Backend | `8025` | `8025` |
| MongoDB | `27225` | `27017` |
| Redis | `6385` | `6379` |

Do not use host ports `8000`, `8010`, `3000`, `5432`, `6379`, or `27017`.

## Environment

Backend `backend/.env`:

```bash
APP_ENV=development
APP_PORT=8025
FRONTEND_URL=http://localhost:3025
MONGO_URL=mongodb://mongodb:27017
MONGO_DB_NAME=fraud_proof_pdf
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-me-super-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ADMIN_API_KEY=change-me-admin-key
DEFAULT_ADMIN_EMAIL=admin@pdfcraft.local
DEFAULT_ADMIN_PASSWORD=AdminPassword123
DEFAULT_ADMIN_NAME=PDFCraft Admin
PDF_STORAGE_DIR=storage/generated_pdfs
SECURE_COOKIES=false
TRUST_PROXY_HEADERS=false
ENABLE_API_DOCS=true
```

Frontend `frontend/.env`:

```bash
VITE_API_BASE_URL=http://localhost:8025
VITE_APP_NAME=PDFCraft
VITE_APP_ENV=development
```

Production examples are available at:

- `backend/.env.production.example`
- `frontend/.env.production.example`

Vite reads `VITE_*` values at build time, so set `VITE_API_BASE_URL` before building the production frontend image.

## Run

```bash
./start.sh
```

URLs:

- Customer app: http://localhost:3025
- Swagger: http://localhost:8025/docs
- Backend health: http://localhost:8025/health
- Backend live: http://localhost:8025/live
- Backend ready: http://localhost:8025/ready
- Admin login: http://localhost:3025/admin/login

Stop:

```bash
./stop.sh
```

## Customer Demo

1. Open PDFCraft at http://localhost:3025.
2. Generate two anonymous PDFs.
3. Try a third PDF and confirm the login/signup prompt.
4. Sign up or log in.
5. Generate PDFs as a logged-in Free user.
6. Open `/account` to see plan usage.
7. Open `/history` and download a PDF.

Customer APIs never expose fraud detection internals, risk scores, fingerprints, IP monitoring, user agents, session lists, investigation data, or technical block codes.

## Completed Phases

- Phase 1: Fraud engine foundation with identity graph, feature snapshots, rule engine, decision engine, and Mongo indexes
- Phase 2: Synthetic dataset generation, weak labels, scikit-learn training, optional-safe model loading, and model registry
- Phase 3: Safe fraud decision integration with PDF generation, preserving authenticated monthly limits
- Phase 4: Admin-only ML/fraud visibility, model controls, decision history, feature snapshots, identity links, and admin labels
- Phase 5: Final documentation, demo scripts, and verification flow

## Advanced ML Fraud Engine

The internal engine is designed to answer one operational question: is this visitor likely trying to bypass the free PDF limit?

It uses:

- Identity graph links across cookie, localStorage, session, fingerprint, device profile, canvas/WebGL, account, and IP/user-agent signals
- Explainable rule scoring with admin-visible reason codes
- Feature snapshots for visitor identify, PDF attempts, allowed/blocked generations, login, signup, and downloads
- Local IP intelligence with VPN/proxy/datacenter/TOR flags and no external API requirement
- Silent behavior events such as page view, generate click, PDF generated, download, login, and signup
- Synthetic PDFCraft-specific training data for initial bootstrapping
- Optional scikit-learn ML models with safe rule-engine fallback when model files are missing
- Weak labels from the rule engine and admin manual labels for future retraining
- Model versioning, candidate review, activation, rejection, and an active model pointer

### Fraud Engine Architecture

The engine is intentionally layered:

1. Visitor identification stores customer-safe visitor continuity while keeping raw signals internal.
2. Identity graph links visitors and accounts with confidence-scored relationships.
3. Feature builder converts visitor, behavior, risk, and usage history into tabular model features.
4. Rule engine produces explainable scores and reason codes.
5. ML model optionally adds fraud probability and anomaly score.
6. Decision engine combines the available signals and persists admin-visible decisions.
7. PDF generation consumes only the final internal decision and returns clean customer messages.

If no active ML model exists, the platform continues using the rule engine only.

### Why IP-Only Is Weak

IP addresses are weak identity signals. They can change when a user restarts a router, switches WiFi, uses a mobile hotspot, or uses a VPN. They can also be shared by many innocent users. The engine therefore treats same IP alone as weak evidence and does not merge visitors or label fraud from IP alone. Stronger continuity comes from cookie/localStorage/session/fingerprint/device profile/behavior/IP intelligence combinations.

### Identity Graph

The identity graph stores links in `visitor_identity_links`. Strong links include same cookie, localStorage, fingerprint, device profile, canvas, WebGL, and account association. Weak links such as same IP are useful for investigation but are not enough to merge visitors. This preserves usage continuity when cookies are cleared but protects innocent users on shared networks.

### Rule Engine

The rule engine assigns points for explainable behaviors such as cookie clearing after a prior cookie, same fingerprint across multiple cookies, too many sessions in a short window, webdriver automation, rapid generation attempts, repeated blocked attempts, and local risky IP indicators. Scores are capped at 100 and stored with reason codes for admin review.

### Synthetic Dataset

`backend/scripts/generate_synthetic_fraud_dataset.py` creates 12,000 PDFCraft-specific rows:

- 5,000 normal examples
- 5,000 fraud examples
- 2,000 gray-zone examples

The gray-zone group exists so the model learns that ambiguous behavior, especially same IP alone, is not automatically fraud.

### ML Training

`backend/scripts/train_fraud_models.py` trains a `RandomForestClassifier` or `LogisticRegression` classifier plus an `IsolationForest` anomaly model. Training can use the synthetic CSV, real collected training events, or demo data. The model feature columns are stored next to the trained artifacts so inference stays stable across versions.

### Model Versioning And Safe Activation

Training creates entries in `ml_model_versions` with metrics, feature columns, paths, and status. New models can remain `CANDIDATE`, be `ACTIVE`, be `REJECTED`, or later be archived. The active pointer lives in `backend/models/fraud/active_model.json`. If the active pointer or model artifacts are missing, PDF generation still works with the rule engine fallback.

### Admin Labels

Admins can apply manual labels to visitors from the investigation view or `POST /api/admin/fraud/label`. Admin labels override weak labels for future training and create audit/event records. Customer UI never exposes these labels or any fraud terminology.

### Dataset Strategy

Real product data starts small, so the first model can be bootstrapped with PDFCraft-specific synthetic scenarios. The app continuously stores real-time `fraud_training_events`, and admin labels override weak labels during future retraining. External fraud datasets can be useful references, but the most valuable data is the product-specific identity, usage, and behavior data collected by PDFCraft.

### GPU Note

A 6GB VRAM laptop GPU is enough for future small neural network or autoencoder experiments. The production engine currently uses explainable CPU-friendly scikit-learn models because this is tabular fraud data and admin review needs clear reasons. Future experiments live under `backend/experiments/deep_learning/` and are not used by production decisions by default.

## Admin Demo

For local development, the default admin is created only when these are configured:

- `DEFAULT_ADMIN_EMAIL=admin@pdfcraft.local`
- `DEFAULT_ADMIN_PASSWORD=AdminPassword123`

Admin flow:

1. Open http://localhost:3025/admin/login manually.
2. Log in with admin email/password or use the API key fallback.
3. View dashboard, events, visitors, investigation timelines, PDFs, and audit logs.

Admin API key check:

```bash
curl -i http://localhost:8025/api/admin/fraud/summary \
  -H "X-Admin-API-Key: change-me-admin-key"
```

Customer JWTs cannot access admin endpoints. Admin JWTs can.

## Advanced Fraud Engine Demo

Run the final product check:

```bash
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
```

Generate synthetic data:

```bash
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
```

Train a candidate model without activating it:

```bash
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py \
  --synthetic-csv data/synthetic_fraud_dataset.csv \
  --auto-activate=false
```

Train and explicitly activate a demo synthetic model:

```bash
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py \
  --synthetic-csv data/synthetic_fraud_dataset.csv \
  --auto-activate=true
```

List model versions:

```bash
curl -i http://localhost:8025/api/admin/ml/models \
  -H "X-Admin-API-Key: change-me-admin-key"
```

View the active model pointer:

```bash
curl -i http://localhost:8025/api/admin/ml/models/active \
  -H "X-Admin-API-Key: change-me-admin-key"
```

Run local scenarios:

```bash
docker exec -it fraud-pdf-backend python scripts/demo_fraud_scenarios.py
```

The demo script covers:

- Normal visitor
- Same fingerprint with new cookie
- Same visitor with changed IP
- Multiple sessions
- Automation signal with `webdriver=true`
- Rapid generation attempts
- Risky IP from `backend/data/ip_risk_list.json`
- Logged-in user after anonymous block

Admin UI:

- `/admin/ml` shows active model details, training counts, and a Train New Model control.
- `/admin/ml/models` shows model version metrics with Activate and Reject actions.
- `/admin/visitor/:visitorId` shows fraud decisions, rule score, ML probability, anomaly score, feature snapshots, identity links, behavior timeline, IP intelligence, and admin label controls.

## Documentation

- [Lead Report](docs/LEAD_REPORT.md)
- [Interview Explanation](docs/INTERVIEW_EXPLANATION.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Production Deployment](docs/DEPLOYMENT.md)

## Deployment Checklist

- Local dev remains on ports `8025`, `3025`, `27225`, and `6385`.
- Production uses `docker-compose.prod.yml` behind Nginx.
- Validate production env with `python3 scripts/check_production_env.py --env backend/.env.production`.
- Validate production Compose with `docker compose -f docker-compose.prod.yml config`.
- Deploy with `./deploy-prod.sh` after replacing placeholders.
- Keep admin URLs, admin accounts, and API keys internal.

Production backup commands:

```bash
scripts/backup_mongo.sh
scripts/backup_storage.sh
scripts/restore_mongo.sh backups/mongo/YYYYMMDD_HHMMSS/mongo.archive
```

Production logs:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f reverse-proxy
```

MongoDB indexes are created idempotently on backend startup. For a large production database, manage new indexes carefully during maintenance windows.

API docs are enabled for local demo with `ENABLE_API_DOCS=true`. Set `ENABLE_API_DOCS=false` or protect docs in production.

## Troubleshooting

- If the frontend cannot reach the backend, confirm `VITE_API_BASE_URL=http://localhost:8025`.
- If admin pages redirect to login, re-enter the admin API key or admin account credentials.
- If anonymous generation unexpectedly asks for login, use a fresh browser session or run the final demo check, which uses unique test IDs.
- If training fails because the CSV is missing, run `python scripts/generate_synthetic_fraud_dataset.py` inside the backend container.
- If Docker ports conflict, stop the conflicting service; do not change this project’s ports.

## API Examples

Register:

```bash
curl -i -X POST http://localhost:8025/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer1@example.com",
    "full_name": "Customer One",
    "password": "StrongPassword123"
  }'
```

Login:

```bash
curl -i -X POST http://localhost:8025/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer1@example.com",
    "password": "StrongPassword123"
  }'
```

Me:

```bash
curl -i http://localhost:8025/api/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Authenticated PDF generation:

```bash
curl -i -X POST http://localhost:8025/api/pdf/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"title":"Logged In PDF","content":"PDF generated by logged in user"}'
```

PDF download:

```bash
curl -i http://localhost:8025/api/pdf/download/<PDF_ID> \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Anonymous identify:

```bash
curl -i -c cookies.txt -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -d '{
    "local_storage_id": "demo-local-001",
    "session_id": "demo-session-001",
    "fingerprint_hash": "demo-fingerprint-001",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-IN",
      "platform": "Windows",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }'
```

## Verification

```bash
docker compose config
./start.sh
curl http://localhost:8025/health
curl http://localhost:8025/live
curl http://localhost:8025/ready
curl http://localhost:8025/api/public/config
curl -I http://localhost:3025
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
docker exec -it fraud-pdf-backend python scripts/demo_fraud_scenarios.py
docker exec -it fraud-pdf-backend python -m pytest
docker exec -it fraud-pdf-frontend npm run build
./stop.sh
```

Production config checks:

```bash
docker compose -f docker-compose.prod.yml config
python3 scripts/check_production_env.py --env backend/.env.production.example
```
