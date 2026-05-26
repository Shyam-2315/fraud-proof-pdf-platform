# PDFCraft

PDFCraft is a fraud-resistant PDF generation SaaS with a customer-facing app, a FastAPI backend, and an internal admin review surface. The product is designed to keep the customer experience simple while enforcing shared anonymous usage limits, account verification, rate limiting, and investigation tooling behind the scenes.

## Key Features

- Anonymous two-PDF free limit with shared quota enforcement
- Fraud-resistant shared usage tracking across browser resets, Incognito sessions, and Safari/private browsing
- Browser and device continuity signals with dynamic IP tracking
- VPN, proxy, and proxy-chain awareness in backend risk scoring
- Redis-backed rate limiting for customer and admin flows
- OTP email verification for new customer accounts
- Admin monitoring for events, visitors, PDFs, audits, and model state
- Customer-safe responses that avoid leaking internal fraud logic or infrastructure details

## Tech Stack

- Backend: FastAPI, Pydantic, Motor, MongoDB Atlas, Upstash Redis
- Customer frontend: React, Vite, TypeScript
- Admin frontend: React, Vite, TypeScript, TanStack Router
- Deployment: Render for backend, Vercel for frontend apps
- Fraud and analytics services: internal rule engine, identity linking, optional ML model pipeline

## Architecture Overview

- `frontend/` contains the customer-facing product.
- `backend/` contains the FastAPI API, business logic, repositories, and fraud-resistant services.
- `pdfcraft-guardian-main/` contains the internal admin dashboard.
- MongoDB stores users, visitors, generated PDFs, verification records, refresh tokens, and audit data.
- Redis is used for rate limiting and operational safeguards.
- Gmail SMTP is used for OTP delivery in production.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system diagram and request flows.

## Repository Layout

```text
backend/
  app/
  tests/
  scripts/
  data/
  requirements.txt
  start_render.sh
  .env.example
  .env.production.example

frontend/
  src/
  scripts/
  package.json
  vite.config.ts
  .env.example
  .env.production.example
  vercel.json

pdfcraft-guardian-main/
  src/
  package.json
  vite.config.ts
  .env.example
  .env.production.example

docs/
  ARCHITECTURE.md
  DEPLOYMENT.md
  BUG_FIX_REPORT.md
  LEAD_REPORT.md
  DEMO_SCRIPT.md
  INTERVIEW_EXPLANATION.md

README.md
docker-compose.yml
docker-compose.prod.yml
start.sh
stop.sh
reset.sh
```

## Local Setup

Prerequisites:

- Python 3.11+
- Node.js 18+
- Docker with Compose

Create local env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp pdfcraft-guardian-main/.env.example pdfcraft-guardian-main/.env
```

Start the local stack:

```bash
./start.sh
```

Local URLs:

- Customer frontend: `http://localhost:3025`
- Admin frontend: `http://localhost:3035/admin/login`
- Backend API: `http://localhost:8025`
- API docs: `http://localhost:8025/docs`

Stop the stack:

```bash
./stop.sh
```

## Environment Variables

Backend highlights:

- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `ADMIN_API_KEY`
- `EMAIL_PROVIDER`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`
- `EMAIL_VERIFICATION_OTP_TTL_MINUTES`
- `EMAIL_VERIFICATION_MAX_ATTEMPTS`
- `EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS`

Frontend highlights:

- `VITE_API_BASE_URL`
- `VITE_APP_NAME`
- `VITE_APP_ENV`

Only example files should be committed. Local `.env` files must stay untracked.

## Running Backend and Frontend Separately

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8025 --reload
```

Customer frontend:

```bash
cd frontend
npm install
npm run dev
```

Admin frontend:

```bash
cd pdfcraft-guardian-main
npm install
npm run dev
```

## Testing Commands

Backend compile check:

```bash
python3 -m compileall -q backend/app backend/tests
```

Backend tests in the running container:

```bash
docker exec fraud-pdf-backend python -m pytest
```

Customer frontend build:

```bash
cd frontend && npm run build
```

Customer forbidden-word scan:

```bash
cd frontend && node scripts/customer-ui-forbidden-scan.mjs
```

## Deployment

Production topology:

- Backend: Render
- Customer frontend: Vercel
- Admin frontend: Vercel
- Database: MongoDB Atlas
- Redis: Upstash Redis
- Email: Gmail SMTP with an app password

Deployment checklist:

1. Configure MongoDB Atlas and collect the connection string.
2. Configure Upstash Redis and collect the `rediss://` connection URL.
3. Set Render backend environment variables from `backend/.env.production.example`.
4. Set Vercel frontend environment variables from `frontend/.env.production.example`.
5. Set Vercel admin environment variables from `pdfcraft-guardian-main/.env.production.example`.
6. Regenerate the Gmail app password if it was ever exposed, then update Render.
7. Redeploy Render and Vercel after configuration changes.

Detailed instructions are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Demo Flow

1. Open the customer app.
2. Generate two PDFs anonymously.
3. Confirm the third anonymous attempt is blocked behind signup/login.
4. Register a customer account.
5. Receive and submit the OTP verification code.
6. Log in after verification.
7. Generate a logged-in PDF and review history/usage.
8. Open the admin dashboard and review the visitor, PDF, and audit views.

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for the step-by-step walkthrough.

## Honest Limitations

- PDFCraft is fraud-resistant, not impossible to bypass.
- Email verification confirms email ownership, not unique human identity.
- Stronger abuse defenses such as CAPTCHA, payments, reputation systems, or external device intelligence may still be required for high-risk production traffic.
- Render-style ephemeral disk is not a long-term substitute for shared object storage if the product scales horizontally.

## Related Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/BUG_FIX_REPORT.md](docs/BUG_FIX_REPORT.md)
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- [docs/LEAD_REPORT.md](docs/LEAD_REPORT.md)
- [docs/INTERVIEW_EXPLANATION.md](docs/INTERVIEW_EXPLANATION.md)
