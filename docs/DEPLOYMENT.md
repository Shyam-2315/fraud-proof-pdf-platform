# Deployment Guide

## Production Topology

- Backend: Render
- Customer frontend: Vercel
- Admin frontend: Vercel
- Database: MongoDB Atlas
- Rate limiting: Upstash Redis
- OTP email delivery: Brevo transactional email API over HTTPS, with SMTP fallback support

## Backend Environment Variables for Render

Start from `backend/.env.production.example`.

Core backend:

- `APP_ENV=production`
- `APP_NAME=PDFCraft`
- `APP_PORT=8025`
- `FRONTEND_URL`
- `ADMIN_FRONTEND_URL`
- `BACKEND_PUBLIC_URL`
- `CORS_ORIGINS`
- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `ADMIN_API_KEY`
- `SECURE_COOKIES=true`
- `COOKIE_SAMESITE=none`
- `TRUST_PROXY_HEADERS=true`

Email verification and Brevo API:

- `EMAIL_PROVIDER=BREVO_API`
- `BREVO_API_KEY=<brevo api key>`
- `BREVO_FROM_EMAIL=<verified sender email>`
- `BREVO_FROM_NAME=PDFCraft`
- `EMAIL_VERIFICATION_OTP_TTL_MINUTES=10`
- `EMAIL_VERIFICATION_MAX_ATTEMPTS=5`
- `EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60`
- `AUTH_VERIFY_EMAIL_RATE_LIMIT=5/minute`
- `AUTH_RESEND_VERIFICATION_RATE_LIMIT=3/hour`

SMTP fallback:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`
- `SMTP_USE_SSL`

Fraud and usage controls:

- `FREE_USAGE_LIMIT=2`
- `ENABLE_SHARED_IP_ANON_QUOTA=true`
- `ANON_SHARED_IP_FREE_LIMIT=2`
- `ANON_IP_USAGE_WINDOW_HOURS=24`
- `ENABLE_DISPOSABLE_EMAIL_BLOCK=true`
- `ENABLE_EMAIL_MX_CHECK=false`

## Frontend Environment Variables for Vercel

Customer frontend:

- `VITE_API_BASE_URL`
- `VITE_APP_NAME=PDFCraft`
- `VITE_APP_ENV=production`

Admin frontend:

- use the admin app example file in `pdfcraft-guardian-main/.env.production.example`
- point it at the same backend origin as the customer frontend

## MongoDB Atlas Setup

1. Create a MongoDB Atlas project and cluster.
2. Create an application user with a strong password.
3. Restrict network access to the Render backend as tightly as possible.
4. Copy the connection string into `MONGODB_URL`.
5. Set `MONGODB_DB_NAME` to the application database name.

Operational note:

- Backend startup ensures the required indexes for users, visitors, OTP verification, PDFs, and fraud data.

## Upstash Redis Setup

1. Create a Redis database in Upstash.
2. Copy the TLS connection string, typically `rediss://...`.
3. Set that value as `REDIS_URL` in Render.

Operational note:

- Redis is used for rate limiting and should be considered part of the production control plane.

## Production SMTP Recommendation

Use Brevo API over HTTPS for production OTP emails. Keep SMTP configured only as fallback if you need an emergency provider switch.

Production note:

- Gmail SMTP is not recommended for production Render deployment because connection attempts can fail from hosted environments.
- Brevo SMTP on port `587` can also time out from hosted environments; the Brevo HTTPS API avoids that transport problem.

## Brevo API Setup

1. Create a Brevo account.
2. Verify the sender email or domain you want PDFCraft to send from.
3. Generate a Brevo API key.
4. Add these Render environment variables:

```env
EMAIL_PROVIDER=BREVO_API
BREVO_API_KEY=<brevo api key>
BREVO_FROM_EMAIL=<verified sender email>
BREVO_FROM_NAME=PDFCraft
```

Delivery behavior implemented in the backend:

- `BREVO_API` uses Brevo transactional email over HTTPS with a `10s` timeout
- Port `587` uses `SMTP + EHLO + STARTTLS + EHLO + LOGIN`
- Port `465` uses `SMTP_SSL`
- Brevo API key logging is blocked
- SMTP password whitespace is stripped before login
- SMTP password logging is blocked
- OTP logging is blocked in production
- customers only see safe delivery failures

Admin diagnostics:

- `GET /api/admin/email/status`
- `POST /api/admin/email/test`

These endpoints never return the SMTP password or the Brevo API key.

## Render Redeploy Steps

1. Update backend environment variables in Render.
2. Save the service configuration.
3. Trigger a redeploy of the latest backend commit.
4. Confirm:
   - `/health`
   - `/api/admin/email/status`
   - `/api/admin/email/test`
5. Test signup and OTP delivery.

## Vercel Redeploy Steps

1. Update the customer frontend environment variables.
2. Update the admin frontend environment variables if the admin app is deployed.
3. Redeploy both projects.
4. Prefer redeploying without build cache after significant environment or routing changes.

## Recommended Verification Flow After Deployment

1. Sign up from the customer frontend.
2. Confirm OTP email delivery.
3. Verify the email code.
4. Log in.
5. Generate a logged-in PDF.
6. Try login with an unverified account and confirm the verification prompt.
7. Test resend verification.
8. Check admin email status and a safe test email.

## Rollback Strategy

1. Keep the previous Render deploy available.
2. Keep previous Vercel deployments available.
3. If a release fails:
   - roll back the backend
   - roll back the customer frontend
   - roll back the admin frontend if affected
4. Re-run health, login, and OTP verification checks.

## Troubleshooting

- OTP emails not arriving:
  - verify `EMAIL_PROVIDER`
  - verify `BREVO_API_KEY` and `BREVO_FROM_EMAIL`
  - verify the provider sender identity is approved
  - if using SMTP fallback, verify `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`
  - check `GET /api/admin/email/status`
  - test `POST /api/admin/email/test`

- Frontend cannot reach backend:
  - verify `VITE_API_BASE_URL`
  - verify CORS settings in `CORS_ORIGINS`

- Login works locally but not in production:
  - check `SECURE_COOKIES`
  - check `COOKIE_SAMESITE`
  - check Render and Vercel origins

- Rate limiting behaves unexpectedly:
  - verify Redis connectivity
  - verify `REDIS_URL`
