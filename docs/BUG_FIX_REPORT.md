# Bug Fix Report

## 1. Browser and Incognito Quota Mismatch

Issue:

- Standard browsing and Incognito/private browsing could report different anonymous usage counts for the same user on the same network.

Cause:

- Visitor-local usage and shared anonymous IP usage were not always advancing in lockstep.

Fix:

- Anonymous PDF success updates both visitor usage and shared anonymous IP usage.
- Status responses use the maximum of visitor and shared-IP usage rather than splitting the view by browser context.

## 2. MongoDB Upsert Conflict

Issue:

- Anonymous PDF generation could fail with a server error during shared IP usage updates.

Cause:

- The same fields were being targeted by incompatible upsert operators during MongoDB updates.

Fix:

- Upsert operations were separated cleanly across `$inc`, `$addToSet`, `$setOnInsert`, and `$set`.
- Null values are excluded from array updates.

## 3. Frontend API URL Wrong Paths

Issue:

- Customer frontend requests could resolve to broken production paths such as relative `/api/...`, duplicated slashes, or malformed production URLs.

Cause:

- API URL construction was not consistently normalized from a configured backend base URL.

Fix:

- The frontend now uses a centralized `apiUrl()` helper for backend requests.
- Static tests guard against broken production path patterns.

## 4. Identify and Status Ordering

Issue:

- The customer app could request visitor status before visitor identification was complete.

Cause:

- Identify and status requests were not sequenced centrally.

Fix:

- Frontend visitor bootstrapping now identifies before status checks.
- Repeated identify requests are de-duplicated.
- A safe retry path exists when the first status request races a stale session.

## 5. Authenticated Plan Limit Versus Rate Limit Conflict

Issue:

- An authenticated user over their monthly plan limit could receive a generic rate-limit response instead of the intended plan-limit message.

Cause:

- Rate limiting could trigger before authenticated plan-limit handling.

Fix:

- Authenticated generate requests now reach plan-limit enforcement without being masked by anonymous-style rate limiting.

## 6. SMTP Email Debugging and OTP Delivery

Issue:

- OTP verification records could be created successfully while Gmail SMTP delivery still failed.

Cause:

- Gmail on port `587` was not using the full `EHLO -> STARTTLS -> EHLO -> LOGIN` sequence.
- Gmail app passwords copied with spaces were not normalized.
- Safe production diagnostics around missing SMTP config and send failures were incomplete.

Fix:

- Port `587` now uses `SMTP + EHLO + STARTTLS + EHLO + LOGIN`.
- Port `465` uses `SMTP_SSL`.
- SMTP password whitespace is stripped before login.
- Missing production SMTP config logs exact missing variable names server-side.
- Customer-facing failures remain safe and generic.
- OTP values and SMTP passwords are never logged in production.
- Admin-only SMTP diagnostics were added through `/api/admin/email/status` and `/api/admin/email/test`.

## 7. Frontend Verification UX

Issue:

- The verification flow was functional but not polished enough for production review.

Cause:

- Signup, login, and verify-email flows lacked a product-grade transition around unverified accounts and resend timing.

Fix:

- Signup redirects directly into verification.
- Login gives a clean verification prompt for unverified accounts.
- Verify Email page now includes prefilled email, six-digit entry, resend cooldown, loading states, and clean success/error messages.

## 8. Security and Review Readiness

Issue:

- The repository needed a cleaner review posture around generated files, local env tracking, and example configuration hygiene.

Fix:

- Local `.env` files are being removed from version control and ignored.
- Cache artifacts and generated files are being excluded from review commits.
- Example configuration files use placeholders instead of personal deployment values.

## Honest Limitation

PDFCraft is fraud-resistant, not impossible to bypass. Email verification proves control of an inbox, not unique human identity. High-risk production traffic can still justify stronger controls such as CAPTCHA, payment verification, reputation systems, or external device intelligence.
