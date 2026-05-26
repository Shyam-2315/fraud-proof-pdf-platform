# PDFCraft Bug Fix Report

## 1. Shared Anonymous Usage Mismatch

**Bug**  
Normal browser usage showed `2`, while Incognito from the same IP showed `1`.

**Cause**  
Visitor usage was incrementing, but shared anonymous IP usage could fall behind. Status then reflected only the lower IP-side count for a new browser on the same IP.

**Fix**  
Every successful anonymous PDF generation now increments both `visitor.free_usage_count` and `anonymous_ip_usage.anonymous_pdf_count` exactly once through the success path. Shared status is always returned as `max(visitor_usage, ip_usage)` and never as a sum.

## 2. Anonymous PDF Generation Returned 500

**Bug**  
Anonymous PDF generation could return `500`.

**Cause**  
The MongoDB anonymous IP usage upsert previously conflicted by updating the same array fields with both `$setOnInsert` and `$addToSet`.

**Fix**  
The repository now keeps operators separated:

- `$inc` only updates `anonymous_pdf_count`
- `$addToSet` only updates identity arrays
- `$setOnInsert` only sets static insert fields
- `$set` only updates timestamps

Null values are excluded from array updates.

## 3. Wrong API Paths on the Deployed Frontend

**Bug**  
Frontend requests could resolve to bad production paths such as relative `/api/...`, `//api/...`, or `/production/api/...`.

**Cause**  
API path construction was not consistently normalized from the configured backend origin.

**Fix**  
The frontend uses the central `apiUrl()` helper for backend requests, with base/path normalization around `VITE_API_BASE_URL`. Static source tests were added to guard against broken production API path patterns.

## 4. Status Could Load Before Identify

**Bug**  
The Generate page could request visitor status before the visitor session bootstrap was complete.

**Cause**  
Identify and status calls were not centrally sequenced, and repeated calls could race each other.

**Fix**  
Frontend visitor bootstrap now:

- caches a successful identify in-memory for the active session
- locks concurrent identify requests
- calls identify before status
- retries status once after `401` or `404` by forcing re-identification

If the retry still fails, the customer sees: `We could not start your session. Please refresh and try again.`

## 5. Authenticated Plan Limit Could Be Masked by Rate Limiting

**Bug**  
An authenticated over-limit request could receive a rate-limit response before the expected plan-limit response.

**Cause**  
The PDF generate route applied rate limiting before plan-limit handling for authenticated traffic.

**Fix**  
Anonymous PDF generation remains rate-limited, while authenticated PDF generation now reaches plan-limit handling without being masked by anonymous-style generate throttling. Existing authenticated over-limit behavior remains the expected `403` upgrade response.

## 6. Performance Improvements

### Backend

- Avoided duplicate visitor resolution in `/api/pdf/generate` for anonymous requests.
- Reused a single shared-usage snapshot for anonymous generate decisions and response shaping.
- Moved the free-limit check ahead of IP intelligence and risk evaluation for blocked anonymous attempts.
- Added request-scoped visitor resolution caching.
- Added slow-endpoint timing logs for:
  - `/api/visitor/identify`
  - `/api/visitor/status`
  - `/api/pdf/generate`
- Cached public config in memory and added `Cache-Control` headers.
- Cached the local IP intelligence JSON in memory after first load.
- Added short Redis connect/read timeouts with graceful fallback.
- Cached PDF output directory creation.
- Added or strengthened Mongo indexes for visitors, generated PDFs, behavior events, and anonymous IP usage.

### Frontend

- Added in-memory identify caching and concurrency locking.
- Sequenced identify before status on Generate and Usage flows.
- Removed duplicate generate-page behavior calls that were adding unnecessary round trips.
- Continued using backend-returned usage values instead of local usage math.

## 7. Honest Limitation

PDFCraft is fraud-resistant and abuse-resistant, not impossible to bypass. Advanced attackers with rotating residential IPs, fresh devices, or paid anti-detection tooling can still require stronger controls such as CAPTCHA, account reputation, payment verification, or higher-grade external intelligence providers.
