# Deployment Guide

## 1. Prerequisites

- Ubuntu or comparable Linux VPS
- Docker Engine with Compose plugin
- DNS control for customer, admin, and API hostnames
- TLS certificate strategy for Nginx or an external load balancer
- Enough disk for MongoDB data, Redis persistence, generated PDFs, and model artifacts

## 2. Server Requirements

Minimum practical baseline for a demo/staging VPS:

- 2 vCPU
- 4 GB RAM
- 40+ GB SSD

Recommended for broader internal review:

- 4 vCPU
- 8 GB RAM
- 80+ GB SSD

## 3. Environment Setup

Create production env files from examples:

```bash
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
cp pdfcraft-guardian-main/.env.production.example pdfcraft-guardian-main/.env.production
```

Update placeholders before deployment:

- `JWT_SECRET_KEY`
- `ADMIN_API_KEY`
- `FRONTEND_URL`
- `ADMIN_FRONTEND_URL`
- `BACKEND_PUBLIC_URL`
- `CORS_ORIGINS`
- `DEFAULT_ADMIN_PASSWORD` if seeding stays enabled
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`

Run the safety check:

```bash
python3 scripts/check_production_env.py --env backend/.env.production
```

## 4. Domain Setup

Recommended hostnames:

- Customer: `pdfcraft.yourdomain.com`
- Admin: `admin.pdfcraft.yourdomain.com`
- API: `api.pdfcraft.yourdomain.com`

Point those DNS records to the VPS public IP before enabling TLS.

## 5. Docker Production Deployment

Validate the stack first:

```bash
docker compose -f docker-compose.prod.yml config
```

Start the production stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Equivalent helper script:

```bash
./deploy-prod.sh
```

Follow logs:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

## 6. Reverse Proxy

Relevant files:

- `deploy/nginx/nginx.conf`
- `deploy/nginx/conf.d/pdfcraft.conf`

Routing contract:

- customer domain -> `frontend`
- admin domain -> `admin-frontend`
- API domain -> `backend`

Forwarded headers configured:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

`TRUST_PROXY_HEADERS=true` should only be enabled when the backend is actually running behind this trusted reverse proxy path.

## 7. HTTPS / TLS

The production compose file exposes ports `80` and `443` on the reverse proxy only.

Recommended options:

- Terminate TLS directly in Nginx and mount certificates into the proxy container.
- Or terminate TLS at a cloud load balancer and keep Nginx private behind it.

If terminating in Nginx, add `listen 443 ssl` server blocks and configure cert/key paths under `/etc/nginx/certs`.

## 8. Database and Redis

- MongoDB and Redis are internal-only in `docker-compose.prod.yml`.
- They are not intended to be exposed on public host ports in production.
- MongoDB indexes are created on backend startup.
- Redis is used for rate limiting and should stay reachable by all backend instances.

## 8a. Email Verification Setup

Required backend environment variables for OTP email verification:

- `EMAIL_PROVIDER=SMTP`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME=PDFCraft`
- `SMTP_USE_TLS=true`
- `EMAIL_VERIFICATION_OTP_TTL_MINUTES=10`
- `EMAIL_VERIFICATION_MAX_ATTEMPTS=5`
- `EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60`
- `ENABLE_DISPOSABLE_EMAIL_BLOCK=true`
- `ENABLE_EMAIL_MX_CHECK=false`

Behavior notes:

- In development, if SMTP is not configured, verification codes are logged to the backend console for local testing.
- In production, registration/resend requests that need email delivery will fail safely if SMTP is not configured.
- `ENABLE_EMAIL_MX_CHECK` is optional and should stay `false` unless outbound DNS is reliable in your runtime.

## 9. Storage

Current production volumes:

- `fraud_pdf_mongo_data`
- `fraud_pdf_redis_data`
- `fraud_pdf_pdf_storage`
- `fraud_pdf_model_storage`
- `fraud_pdf_proxy_certs`

For horizontal scaling, move PDF output and model artifacts to shared/object storage.

## 10. Backups

MongoDB backup:

```bash
scripts/backup_mongo.sh
```

MongoDB restore:

```bash
scripts/restore_mongo.sh backups/mongo/YYYYMMDD_HHMMSS/mongo.archive
```

PDF/model storage backup:

```bash
scripts/backup_storage.sh
```

## 11. Logs

Local stack logs:

```bash
./logs.sh
```

Production-focused logs:

```bash
scripts/logs.sh
docker compose -f docker-compose.prod.yml logs -f reverse-proxy backend frontend admin-frontend
```

## 12. Health Checks

Run after deployment:

```bash
curl https://api.pdfcraft.your-domain.com/health
curl https://api.pdfcraft.your-domain.com/ready
```

Useful local checks:

```bash
curl http://localhost:8025/health
curl http://localhost:8025/ready
curl http://localhost:8025/api/public/config
```

## 13. Scaling Notes

- Backend application containers are stateless apart from MongoDB, Redis, PDF storage, and model storage.
- Redis and MongoDB should move to managed or replicated deployments before serious scale-out.
- Shared storage is required before running multiple backend replicas that must serve the same PDFs and active model artifacts.
- Reverse-proxy and backend logging should move to centralized aggregation for long-running production use.

## 14. Rollback

1. Keep previous image tags or a previous repo revision available.
2. Stop the current production stack:

```bash
docker compose -f docker-compose.prod.yml down
```

3. Restore previous images, env files, or reverse-proxy config.
4. Start again:

```bash
docker compose -f docker-compose.prod.yml up -d
```

5. Re-run health checks.

## 15. Troubleshooting

- `docker compose -f docker-compose.prod.yml config` fails:
  Check missing env files, invalid YAML, or unresolved build args.

- `scripts/check_production_env.py` fails:
  Replace placeholder secrets, remove localhost origins, and confirm HTTPS URLs.

- `/ready` fails:
  Check MongoDB, Redis, storage volume permissions, and model directory mounts.

- Customer or admin frontend cannot reach API:
  Confirm `VITE_API_BASE_URL` in the respective production env file and verify Nginx API routing.

- Client IPs look wrong in backend logs:
  Confirm proxy forwarding headers and only then enable `TRUST_PROXY_HEADERS=true`.
