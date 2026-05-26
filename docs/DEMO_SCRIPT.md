# Demo Script

## Goal

Demonstrate that PDFCraft provides a clean customer experience while enforcing anonymous quotas, email verification, authenticated limits, and internal admin visibility.

## Demo Setup

Before the walkthrough:

1. Start the local stack or deploy the latest backend and frontend builds.
2. Confirm MongoDB, Redis, and SMTP are reachable.
3. Open the customer frontend.
4. Open the admin frontend in a separate tab.

## Customer Demo

### 1. Anonymous Usage

1. Open the customer app landing page.
2. Navigate to `/generate`.
3. Generate PDF 1 anonymously.
4. Generate PDF 2 anonymously.
5. Attempt PDF 3.
6. Show that the customer receives a clean signup/login prompt rather than an internal error.

### 2. Incognito and Safari Shared Usage

1. Open the same app in an Incognito or private browsing window.
2. Go to `/generate`.
3. Show that the shared anonymous usage state follows the network-level quota logic instead of resetting as a brand-new free session.
4. If Safari or another browser is available, repeat the check to show shared anonymous quota continuity.

### 3. Signup

1. Open `/signup`.
2. Register a new account.
3. Show the success transition into `/verify-email`.
4. Explain that the account is created as unverified until email ownership is confirmed.

### 4. OTP Verification

1. Retrieve the verification email.
2. Enter the six-digit OTP on `/verify-email`.
3. Show successful verification and redirect to login.
4. Show the resend button and cooldown behavior.

### 5. Login

1. Log in with the newly verified account.
2. Show that login succeeds normally after verification.
3. If useful, attempt login with an unverified account to show the clean verification prompt.

### 6. Logged-In PDF Generation

1. Generate a PDF as an authenticated customer.
2. Open usage history or account pages.
3. Download a generated PDF from the authenticated history view.

## Admin Demo

### 7. Admin Visibility

1. Open the admin dashboard.
2. Log in with an admin account or admin API key.
3. Show:
   - dashboard summary
   - recent events
   - visitor list
   - generated PDFs
   - audit logs
4. Explain that admin tools are internal-only and are not exposed in the customer product.

### 8. Email Operations Visibility

1. Call `GET /api/admin/email/status`.
2. Show SMTP readiness details without exposing the SMTP password.
3. Optionally call `POST /api/admin/email/test` to send a safe non-OTP test email.

## Suggested Talk Track

- Start with product value: fast PDF generation with a clean free-to-account funnel.
- Show that anonymous usage is limited fairly across browsing modes.
- Show that OTP verification protects account ownership without exposing infrastructure details to the customer.
- Close by showing that admins have the visibility needed to debug and review activity without leaking those internal controls to end users.

## Optional Supporting Commands

Backend tests:

```bash
docker exec fraud-pdf-backend python -m pytest
```

Frontend build:

```bash
cd frontend && npm run build
```

Backend compile check:

```bash
python3 -m compileall -q backend/app backend/tests
```
