# Fraud Proof PDF Platform

Production-oriented FastAPI backend foundation for a demo PDF generation platform with fraud detection.

## Phase 1 Completed Features

- FastAPI backend with application lifespan startup and shutdown hooks
- MongoDB connection using Motor async client
- Redis connection using Redis async client
- Health endpoints for the API, MongoDB, and Redis
- Request ID middleware
- Request logging middleware with method, path, status code, duration, and client IP
- CORS configured for local frontend development
- Environment-based configuration with `pydantic-settings`
- Docker and Docker Compose setup for backend, MongoDB, and Redis
- One-command startup, stop, logs, and reset scripts

Authentication, PDF generation, and fraud detection are intentionally not implemented in this phase.

## Phase 2 Visitor Tracking

Phase 2 adds anonymous visitor identification for later fraud detection and free usage limit enforcement.

Completed visitor tracking features:

- Anonymous `anon_id` HTTP-only cookie handling
- Visitor matching by cookie ID, local storage ID, fingerprint hash, then session ID
- UUID string visitor IDs instead of MongoDB ObjectIds
- MongoDB-backed `visitors` collection
- Bounded signal arrays for local storage IDs, session IDs, fingerprint hashes, IP addresses, and user agents
- Visitor status API with free usage count, limit, remaining free uses, risk fields, and tracked signal counts
- Startup indexes for visitor lookup and status queries

Still not implemented in this phase:

- Authentication
- Final fraud blocking
- Redis rate limiting

## Phase 3 PDF Generation And Free Limit

Phase 3 adds demo PDF generation for anonymous visitors with a two-use free limit.

Completed PDF generation features:

- `POST /api/pdf/generate` creates a local demo PDF file
- `GET /api/pdf/history` lists generated PDFs for the current anonymous visitor
- Anonymous visitors can generate `2` PDFs for free
- The third generation attempt is blocked with `FREE_LIMIT_REACHED`
- Visitor `free_usage_count` increments only after successful PDF record creation
- Generated PDF metadata is stored in MongoDB

The backend still does not implement authentication, frontend UI, advanced fraud scoring, or PDF download endpoints.

## Free Usage Rule

Anonymous visitors must call `/api/visitor/identify` first. The backend uses the `anon_id` cookie to load the visitor.

- First PDF generation succeeds and leaves `remaining_free_uses` at `1`
- Second PDF generation succeeds and leaves `remaining_free_uses` at `0`
- Third PDF generation returns `403` and asks the user to login

## Safe Port Mapping

This project avoids common host ports already used by other projects.

| Service | Host Port | Container Port |
| --- | ---: | ---: |
| Backend FastAPI | `8025` | `8025` |
| Future frontend | `3025` | Not implemented yet |
| MongoDB | `27225` | `27017` |
| Redis | `6385` | `6379` |

## Setup Commands

Start the full stack:

```bash
./start.sh
```

Stop services:

```bash
./stop.sh
```

Follow logs:

```bash
./logs.sh
```

Reset local containers and project volumes, then restart:

```bash
./reset.sh
```

The startup script copies `backend/.env.example` to `backend/.env` if the local environment file is missing.

## Health Check URLs

- API: http://localhost:8025/health
- MongoDB: http://localhost:8025/health/db
- Redis: http://localhost:8025/health/redis
- OpenAPI docs: http://localhost:8025/docs

## Visitor APIs

- Identify visitor: `POST http://localhost:8025/api/visitor/identify`
- Visitor status: `GET http://localhost:8025/api/visitor/status`
- Generate PDF: `POST http://localhost:8025/api/pdf/generate`
- PDF history: `GET http://localhost:8025/api/pdf/history`

Example identify request:

```bash
curl -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -d '{
    "local_storage_id": "local-test-123",
    "session_id": "session-test-123",
    "fingerprint_hash": "fingerprint-test-123",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-US",
      "platform": "Win32",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }' \
  -c cookies.txt
```

Example status request:

```bash
curl http://localhost:8025/api/visitor/status -b cookies.txt
```

## PDF Generation Test Commands

First, identify visitor:

```bash
curl -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -d '{
    "local_storage_id": "local-test-123",
    "session_id": "session-test-123",
    "fingerprint_hash": "fingerprint-test-123",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-US",
      "platform": "Win32",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }' \
  -c cookies.txt
```

Generate PDF 1:

```bash
curl -X POST http://localhost:8025/api/pdf/generate \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "title": "Demo PDF 1",
    "content": "This is the first free PDF generated by anonymous visitor."
  }'
```

Generate PDF 2:

```bash
curl -X POST http://localhost:8025/api/pdf/generate \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "title": "Demo PDF 2",
    "content": "This is the second free PDF generated by anonymous visitor."
  }'
```

Generate PDF 3 should be blocked:

```bash
curl -i -X POST http://localhost:8025/api/pdf/generate \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "title": "Demo PDF 3",
    "content": "This third request should be blocked because the free limit is reached."
  }'
```

Check status:

```bash
curl http://localhost:8025/api/visitor/status -b cookies.txt
```

Check PDF history:

```bash
curl http://localhost:8025/api/pdf/history -b cookies.txt
```

Expected behavior:

- PDF 1 response has `success: true`, `free_usage_count: 1`, `remaining_free_uses: 1`
- PDF 2 response has `success: true`, `free_usage_count: 2`, `remaining_free_uses: 0`
- PDF 3 response is HTTP `403` with reason `FREE_LIMIT_REACHED`

## Phase 4 Fraud Detection Engine

Phase 4 adds a fraud detection layer for anonymous reidentification and free-limit abuse signals. It does not use external VPN APIs yet, and it does not aggressively block IP addresses because dynamic IPs can affect legitimate users.

Fraud detection features:

- Risk score and risk level updates during visitor identification
- Fraud event storage in `fraud_events`
- Active blocked entity storage in `blocked_entities`
- Fingerprint blocking when cumulative risk reaches `90`
- Visitor blocking when the anonymous free limit is reached
- Public demo/debug fraud endpoints

New fraud APIs:

- Fraud events: `GET http://localhost:8025/api/fraud/events`
- Fraud summary: `GET http://localhost:8025/api/fraud/summary`

Risk score rules:

| Signal | Points | Event |
| --- | ---: | --- |
| Missing cookie but known fingerprint | `25` | `COOKIE_MISSING_BUT_FINGERPRINT_MATCHED` |
| New local storage ID | `15` | `LOCAL_STORAGE_CHANGED` |
| New session ID | `5` | `SESSION_CHANGED` |
| New IP for known fingerprint | `20` | `NEW_IP_FOR_FINGERPRINT` |
| Three or more IPs | `25` | `MULTIPLE_IPS_DETECTED` |
| Five or more sessions | `20` | `TOO_MANY_SESSIONS` |
| VPN/proxy placeholder headers | `30` | `VPN_PROXY_SUSPECTED` |
| Free limit already reached | `40` | `FREE_LIMIT_REACHED` |

Risk levels:

- `LOW`: 0-39
- `MEDIUM`: 40-69
- `HIGH`: 70+

Blocked entities:

- `VISITOR` is blocked when the free limit is reached
- `FINGERPRINT` is blocked when cumulative risk score reaches `90`
- IPs are not blocked by default in Phase 4

Fraud detection test commands:

Check fraud events:

```bash
curl http://localhost:8025/api/fraud/events
```

Check fraud summary:

```bash
curl http://localhost:8025/api/fraud/summary
```

Simulate session change:

```bash
curl -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -c cookies.txt \
  -d '{
    "local_storage_id": "local-test-123",
    "session_id": "session-test-new-999",
    "fingerprint_hash": "fingerprint-test-123",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-US",
      "platform": "Win32",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }'
```

Simulate cookie deletion but same fingerprint:

```bash
rm -f cookies-deleted.txt

curl -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -d '{
    "local_storage_id": "local-test-123",
    "session_id": "session-after-cookie-delete",
    "fingerprint_hash": "fingerprint-test-123",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-US",
      "platform": "Win32",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }' \
  -c cookies-deleted.txt
```

Expected:

- The system recognizes the same visitor through fingerprint or local storage
- `is_new_visitor` is `false`
- `risk_score` increases
- `fraud_events` contains `COOKIE_MISSING_BUT_FINGERPRINT_MATCHED`

Simulate VPN/proxy header:

```bash
curl -X POST http://localhost:8025/api/visitor/identify \
  -H "Content-Type: application/json" \
  -H "x-vpn: true" \
  -b cookies.txt \
  -c cookies.txt \
  -d '{
    "local_storage_id": "local-test-123",
    "session_id": "session-vpn-test",
    "fingerprint_hash": "fingerprint-test-123",
    "device_info": {
      "screen": "1920x1080",
      "timezone": "Asia/Kolkata",
      "language": "en-US",
      "platform": "Win32",
      "hardware_concurrency": 8,
      "device_memory": 8,
      "touch_support": 0
    }
  }'
```

Fingerprint block behavior:

- Risk score is cumulative and capped at `100`
- When a visitor reaches risk score `90`, the current fingerprint is added to `blocked_entities`
- Future attempts with that fingerprint create a blocked visitor or keep the existing visitor blocked

## Cookie Behavior

The identify endpoint sets an `anon_id` cookie when needed.

- `httponly=true`
- `samesite=lax`
- `secure=false` for local development
- `max_age=2592000` seconds, or 30 days

## MongoDB Visitor Collection

Visitor documents are stored in the `visitors` collection. Each document uses a UUID string `_id` and tracks cookie IDs, browser storage IDs, session IDs, fingerprint hashes, IP addresses, user agents, device info, free usage count, risk fields, and timestamps.

Generated PDF metadata is stored in the `generated_pdfs` collection. Each document uses a UUID string `_id` and records visitor ID, title, content, file name, file path, generation type, creation time, IP address, and fingerprint hash.

Fraud events are stored in the `fraud_events` collection. Active blocked visitors and fingerprints are stored in the `blocked_entities` collection.

Indexes are created on startup for:

Visitor indexes:

- `cookie_id`
- `local_storage_ids`
- `session_ids`
- `fingerprint_hashes`
- `primary_fingerprint_hash`
- `last_seen_at`

Generated PDF indexes:

- `visitor_id`
- `user_id`
- `created_at`
- `generation_type`

Fraud event indexes:

- `visitor_id`
- `event_type`
- `severity`
- `created_at`

Blocked entity indexes:

- `entity_type`, `entity_value`, `is_active`
- `created_at`
- `expires_at`

## Testing Phase 2

Start the stack:

```bash
./start.sh
```

Verify the existing health endpoints:

```bash
curl http://localhost:8025/health
curl http://localhost:8025/health/db
curl http://localhost:8025/health/redis
```

Then run the visitor identify and status curl commands above.

## Docker Services

- `backend`: FastAPI app served by Uvicorn on host port `8025`
- `mongodb`: MongoDB exposed on host port `27225`
- `redis`: Redis exposed on host port `6385`

Container names:

- `fraud-pdf-backend`
- `fraud-pdf-mongodb`
- `fraud-pdf-redis`

Docker resources:

- Network: `fraud_pdf_network`
- Volumes: `fraud_pdf_mongo_data`, `fraud_pdf_redis_data`

## Environment

Edit `backend/.env` to override local settings.

Required defaults are documented in `backend/.env.example`.

## Next Phase

Build free usage enforcement and fraud scoring on top of visitor tracking.
