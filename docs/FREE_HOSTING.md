# Free Hosting Guide

This project can be deployed for review/demo on free-tier services with this split:

- customer frontend: Vercel from `frontend/`
- admin frontend: Vercel from `pdfcraft-guardian-main/`
- backend: Render web service from `backend/`
- database: MongoDB Atlas M0
- Redis: Upstash Redis

Local Docker Compose development remains unchanged.

## 1. Deploy Backend To Render

Create a new Render Web Service connected to this repository.

Use:

- Root directory: `backend`
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `./start_render.sh`

Relevant files:

- [backend/start_render.sh](/home/snp2315/Projects/SaaS/fraud-proof-pdf-platform/backend/start_render.sh)
- [render.yaml](/home/snp2315/Projects/SaaS/fraud-proof-pdf-platform/render.yaml)

Render will provide `PORT` automatically. The backend now accepts `PORT` as a fallback for `APP_PORT`.

## 2. Create MongoDB Atlas Free Cluster

1. Create a MongoDB Atlas M0 cluster.
2. Create a database user.
3. Whitelist `0.0.0.0/0` for demo use, or restrict further if you have a better outbound-IP strategy.
4. Copy the connection string.
5. Set Render env:

```text
MONGODB_URL=mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=fraud_pdf
```

## 3. Create Upstash Redis Free Database

1. Create an Upstash Redis database.
2. Copy the `rediss://` connection URL.
3. Set Render env:

```text
REDIS_URL=rediss://default:PASSWORD@HOST:PORT
```

The backend now degrades gracefully if Redis is unavailable: startup continues, a warning is logged, and rate limiting is skipped instead of crashing the whole app.

## 4. Deploy Customer Frontend To Vercel

Create a Vercel project for `frontend/`.

Use:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`

Relevant file:

- [frontend/vercel.json](/home/snp2315/Projects/SaaS/fraud-proof-pdf-platform/frontend/vercel.json)

Required env:

```text
VITE_API_BASE_URL=https://YOUR_RENDER_BACKEND_URL
VITE_APP_NAME=PDFCraft
VITE_APP_ENV=production
```

## 5. Deploy Admin Frontend To Vercel

Create a second Vercel project for `pdfcraft-guardian-main/`.

Use:

- Root directory: `pdfcraft-guardian-main`
- Build command: `npm run build`
- Output directory: `dist`

Relevant file:

- [pdfcraft-guardian-main/vercel.json](/home/snp2315/Projects/SaaS/fraud-proof-pdf-platform/pdfcraft-guardian-main/vercel.json)

Required env:

```text
VITE_API_BASE_URL=https://YOUR_RENDER_BACKEND_URL
VITE_APP_NAME=PDFCraft Internal Admin
VITE_APP_ENV=production
```

## 6. Backend Environment Variables

Set these on Render:

```text
APP_ENV=production
APP_NAME=PDFCraft
FRONTEND_URL=https://YOUR_CUSTOMER_FRONTEND_URL
ADMIN_FRONTEND_URL=https://YOUR_ADMIN_FRONTEND_URL
BACKEND_PUBLIC_URL=https://YOUR_RENDER_BACKEND_URL
CORS_ORIGINS=https://YOUR_CUSTOMER_FRONTEND_URL,https://YOUR_ADMIN_FRONTEND_URL,http://localhost:3025,http://localhost:3035
MONGODB_URL=mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=fraud_pdf
REDIS_URL=rediss://default:PASSWORD@HOST:PORT
JWT_SECRET_KEY=strong-secret
ADMIN_API_KEY=strong-admin-key
ENABLE_DEFAULT_ADMIN_SEED=false
SECURE_COOKIES=true
COOKIE_SAMESITE=none
TRUST_PROXY_HEADERS=true
ENABLE_API_DOCS=true
PDF_STORAGE_DIR=/tmp/generated_pdfs
ML_MODELS_DIR=/tmp/models/fraud
ENABLE_ONLINE_ML_TRAINING=false
```

Notes:

- `ENABLE_API_DOCS=true` is acceptable for demo hosting; disable later if needed.
- `PDF_STORAGE_DIR=/tmp/generated_pdfs` and `ML_MODELS_DIR=/tmp/models/fraud` are demo-friendly for free hosting.

## 7. Update CORS

The backend reads `CORS_ORIGINS` as a comma-separated list or JSON array.

Recommended value for free hosting plus local dev:

```text
CORS_ORIGINS=https://pdfcraft.vercel.app,https://pdfcraft-admin.vercel.app,http://localhost:3025,http://localhost:3035
```

Do not use `*` because credentials are enabled.

## 8. Test Deployed URLs

After deployment:

```bash
curl https://YOUR_RENDER_BACKEND_URL/health
curl https://YOUR_RENDER_BACKEND_URL/api/public/config
```

Then manually verify:

1. Open the customer Vercel URL.
2. Open the admin Vercel URL.
3. Log in to admin with the configured admin API key or admin account.
4. Generate two PDFs anonymously from the customer UI.
5. Confirm the third attempt asks for login/signup.

## 9. Known Limitations Of Free Hosting

- Render free instances can sleep and cold-start.
- Render free filesystem is ephemeral; `/tmp` PDF/model storage is temporary.
- Generated PDFs may not persist reliably across restarts.
- Online ML training is disabled by default for hosted demos via `ENABLE_ONLINE_ML_TRAINING=false`.
- For real production durability, move generated PDFs and model artifacts to S3, Cloudflare R2, or similar object storage.
