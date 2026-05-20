# Architecture

## Full System Architecture

```mermaid
flowchart TB
  Browser[Customer/Admin browser] --> Frontend[React/Vite frontend :3025]
  Frontend --> Backend[FastAPI backend :8025]
  Backend --> Mongo[(MongoDB :27225)]
  Backend --> Redis[(Redis :6385)]
  Backend --> Files[Generated PDF storage]
  Backend --> Engine[Internal fraud engine]
  Engine --> Models[Model artifacts]
```

## Backend Module Structure

- `app/routes`: HTTP API routes
- `app/services`: business workflows
- `app/repositories`: Mongo access
- `app/fraud_engine`: identity graph, feature builder, rule engine, ML model, training services
- `app/schemas`: request/response models
- `scripts`: demo, training, synthetic data, final checks

## Frontend Module Structure

- `src/pages`: customer and admin routes
- `src/components`: shared UI, customer widgets, admin navigation
- `src/api`: customer/admin API clients
- `src/context`: auth state
- `src/utils`: customer identity helpers

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

Docker Compose starts four services on fixed project ports:

- Backend: `8025`
- Frontend: `3025`
- MongoDB host: `27225`
- Redis host: `6385`

The project intentionally avoids common ports like `3000`, `8000`, `8010`, `5432`, `6379`, and `27017`.

