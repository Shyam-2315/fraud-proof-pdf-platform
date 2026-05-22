# Architecture

## Full System Architecture

```mermaid
flowchart TB
  Customer[Customer Frontend on 3025] --> Backend[Backend 8025]
  Admin[Admin Frontend on 3035] --> Backend
  Backend --> Mongo[(MongoDB :27225)]
  Backend --> Redis[(Redis :6385)]
  Backend --> Files[Generated PDF storage]
  Backend --> Engine[Internal fraud engine]
  Engine --> Models[Model artifacts]
```

The backend is the single source of truth. The customer-facing PDFCraft app in
`frontend/` and the internal admin dashboard in `pdfcraft-guardian-main/` are
separate frontends that both call the same FastAPI backend on port `8025`.

## Backend Module Structure

- `app/routes`: HTTP API routes
- `app/services`: business workflows
- `app/repositories`: Mongo access
- `app/fraud_engine`: identity graph, feature builder, rule engine, ML model, training services
- `app/schemas`: request/response models
- `scripts`: demo, training, synthetic data, final checks

## Frontend Module Structure

- `frontend/`: customer-facing PDFCraft app on port `3025`
- `pdfcraft-guardian-main/`: internal admin dashboard on port `3035`
- Both frontends use `VITE_API_BASE_URL` to call the backend on port `8025`
- Customer UI must not link to admin routes or expose internal fraud/ML details

## Data Collections

- `visitors`
- `generated_pdfs`
- `users`
- `refresh_tokens`
- `user_usage`
- `fraud_events`
- `visitor_identity_links`
- `fraud_feature_snapshots`
- `risk_score_snapshots`
- `fraud_decisions`
- `fraud_training_events`
- `fraud_labels`
- `ml_model_versions`
- `admin_audit_logs`

## API Groups

- `/api/public`: public customer config
- `/api/visitor`: anonymous visitor identify/status
- `/api/pdf`: generation, history, download
- `/api/auth`: signup, login, refresh, logout, me
- `/api/account`: account usage
- `/api/admin`: protected admin dashboard, events, visitors, PDFs, audit, ML

## Fraud Engine Architecture

```mermaid
flowchart LR
  Request[Request] --> Visitor[Visitor service]
  Visitor --> Graph[Identity graph]
  Graph --> Features[Feature builder]
  Features --> Rules[Rule engine]
  Features --> ML[Optional ML]
  Rules --> Decision[Decision engine]
  ML --> Decision
  Decision --> Snapshots[Snapshots and training events]
  Decision --> Response[Customer-safe response]
```

## ML Pipeline Architecture

```mermaid
flowchart TD
  Synthetic[Synthetic generator] --> CSV[CSV dataset]
  CSV --> Train[Training service]
  RealEvents[Collected training events] --> Train
  Labels[Admin labels] --> Train
  Train --> Classifier[Classifier artifact]
  Train --> Isolation[Isolation Forest artifact]
  Classifier --> Registry[Model registry]
  Isolation --> Registry
  Registry --> Candidate[Candidate version]
  Candidate --> Active[Safe activation]
```

## Deployment Architecture

Docker Compose starts five services on fixed project ports:

- Backend: `8025`
- Customer frontend: `3025`
- Admin frontend: `3035`
- MongoDB host: `27225`
- Redis host: `6385`

The project intentionally avoids common ports like `3000`, `8000`, `8010`, `5432`, `6379`, and `27017`.
