# PDFCraft / Fraud Proof PDF Platform

PDFCraft is a customer-facing SaaS for generating downloadable PDFs with anonymous and authenticated usage limits. Fraud Proof PDF Platform is the internal backend and admin system used to enforce sophisticated fraud detection and prevention mechanisms.

The platform is designed to be fraud-resistant rather than "fraud proof": the customer experience stays simple, while the backend combines multi-signal identity continuity, rule-based risk scoring, synthetic data ML training, and admin review tools.

## What Problem It Solves

- Gives customers a clean PDF generation workflow with account-based usage control.
- Preserves a simple free tier without exposing internal fraud controls in the customer UI.
- Helps internal reviewers detect repeated limit bypass attempts across cookies, storage resets, device fingerprints, behavior, and network signals.
- Supports a reviewable path from explainable rules to candidate ML models.
- Enables fraud-resistant cross-browser anonymous usage tracking by IP quota.

## Main Features

- **Anonymous Usage Control**: Two-PDF limit with fraud-resistant cross-browser tracking by IP quota
- **Authentication & Authorization**: Customer signup, login, token refresh, logout, and account usage views
- **Usage Limits**: Logged-in monthly usage limits by plan with synchronization across browsers
- **Secure Access**: Secure PDF download with ownership checks
- **Customer/Admin Separation**: Clean customer UI and protected admin system
- **Admin Dashboard**: Full visibility into fraud metrics and user activity
- **Fraud Detection**: 
  - Fraud events and decision history
  - Identity graph with confidence scoring
  - Feature snapshots for debugging
  - Rule engine with explainable scoring
  - ML fraud engine with scikit-learn models
- **ML Operations**:
  - Synthetic fraud dataset generation
  - Candidate model training, versioning, and activation
  - Safe fallback to rule engine when no active model exists
- **Operational Support**: Health, readiness, backup, and deployment scripts

## Recent Changes (May 2026)

### Anonymous Usage Tracking Improvements
- ✅ **Finalized fraud-resistant shared anonymous usage tracking** (May 25)
- ✅ **Cross-browser anonymous usage synchronization by IP quota** (May 25)
- ✅ **Fixed shared anonymous usage tracking across browsers** (May 25)
- Cleaned Python cache artifacts for production readiness
- Pinned Python runtime to 3.11 for consistent Render deployments

### Deployment & Hosting
- ✅ **Prepared for free-tier hosting** (May 25)
- ✅ **Database deployment ready** (May 25)
- ✅ **Final commit - production deployable** (May 22)

## Architecture Overview

```
project-root/
  ├── frontend/                 # Customer-facing PDFCraft app
  ├── pdfcraft-guardian-main/   # Internal admin dashboard
  ├── backend/                  # FastAPI API, persistence, abuse-prevention, ML
  ├── deploy/                   # Reverse proxy configuration (Nginx)
  ├── scripts/                  # Operational checks and backup helpers
  ├── docs/                     # Deployment, architecture, demo, and review docs
  ├── docker-compose.yml        # Local development
  ├── docker-compose.prod.yml   # Production configuration
  ├── start.sh                  # Quick start script
  └── stop.sh                   # Shutdown script
```

### Service Endpoints (Local Development)

| Service | URL / Port |
| --- | --- |
| Customer frontend | `http://localhost:3025` |
| Admin frontend | `http://localhost:3035/admin/login` |
| Backend API | `http://localhost:8025` |
| MongoDB host port | `27225` |
| Redis host port | `6385` |

## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Backend** | FastAPI, Pydantic, MongoDB, Redis |
| **Customer Frontend** | React, Vite, TypeScript |
| **Admin Frontend** | React, Vite, TypeScript, TanStack Router |
| **Deployment** | Docker Compose, Nginx |
| **ML/Fraud** | scikit-learn, Random Forest, Logistic Regression, Isolation Forest |
| **Language Composition** | Python (58.2%), TypeScript (39.6%), CSS (0.9%), Shell (0.6%), JavaScript (0.6%), Dockerfile (0.1%) |

## Free Hosting Option

Recommended free-tier deployment split:

- **Customer Frontend**: Vercel (from `frontend/`)
- **Admin Frontend**: Vercel (from `pdfcraft-guardian-main/`)
- **Backend**: Render (from `backend/`)
- **Database**: MongoDB Atlas M0 (free tier)
- **Cache**: Upstash Redis (free tier)

This keeps local Docker development unchanged while allowing online review and demonstration without a VPS.

## Local Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+

### Getting Started

1. **Copy environment files**:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp pdfcraft-guardian-main/.env.example pdfcraft-guardian-main/.env
```

2. **Start the stack**:
```bash
./start.sh
```

3. **Access the applications**:
- Customer app: `http://localhost:3025`
- Admin app: `http://localhost:3035/admin/login`
- API docs: `http://localhost:8025/docs` (when `ENABLE_API_DOCS=true`)

4. **Stop the stack**:
```bash
./stop.sh
```

## API Endpoints

- **Health check**: `http://localhost:8025/health`
- **Readiness check**: `http://localhost:8025/ready`
- **Public config**: `http://localhost:8025/api/public/config`
- **API documentation**: `http://localhost:8025/docs` (when enabled)

## Customer Demo Flow

1. Open the customer app at `http://localhost:3025`
2. Generate two PDFs anonymously to test the limit
3. Attempt a third PDF generation and confirm the login/signup gate
4. Register a new account or log in
5. Generate PDFs as an authenticated customer
6. Explore customer features:
   - `/usage` - View monthly usage quota
   - `/history` - Review previously generated PDFs
   - `/account` - Manage account settings
7. Download a previously generated PDF

*Note: Customer-facing screens and API responses do not expose fraud, ML, identity graph, or internal risk terminology.*

## Admin Demo Flow

1. Navigate to `http://localhost:3035/admin/login`
2. Authenticate using the seeded admin account (or admin API key in local development)
3. Explore the admin dashboard:
   - **Dashboard**: Overview cards with fraud metrics
   - **Events**: View recent fraud detection events
   - **Visitors**: Analyze visitor profiles and identity links
   - **PDFs**: Monitor PDF generation activity
   - **Audit Logs**: Track all system and admin actions
   - **ML Section**: Inspect active model and start candidate training
4. Investigate specific visitors and review fraud decisions with reasoning

## ML Fraud Engine Demo

Generate synthetic fraud data and train a candidate model:

```bash
# Generate synthetic fraud dataset
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py

# Train candidate ML models
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py \
  --synthetic-csv data/synthetic_fraud_dataset.csv \
  --auto-activate=false

# Run final demo verification
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
```

### Key ML Capabilities

- **Multi-Signal Identity**: Combines cookie, local storage, fingerprint, device profile, behavior, and IP signals
- **Explainable Scoring**: Rule engine provides transparent fraud risk justification
- **Synthetic Bootstrapping**: Generates realistic fraud scenarios for cold-start training
- **Safe Model Activation**: Candidate review flow before promoting models to production
- **Graceful Fallback**: Rule engine remains active if no ML model is deployed

## Testing Commands

```bash
# Python syntax check
python3 -m compileall -q backend/app backend/scripts backend/tests

# Verify Docker configuration
docker compose config
docker compose -f docker-compose.prod.yml config

# Run backend tests
docker exec -it fraud-pdf-backend python -m pytest

# Build frontend
docker exec -it fraud-pdf-frontend npm run build
docker exec -it fraud-pdf-admin-frontend npm run build

# Check production environment
python3 scripts/check_production_env.py --env backend/.env.production.example
```

## Recent Cleanup & Review Notes

- ✅ Generated caches and build artifacts removed
- ✅ Tracked local environment files cleaned
- ✅ Windows metadata files excluded
- ✅ Dead customer-frontend admin/TanStack routes removed
- ✅ Separate admin app preserved at `pdfcraft-guardian-main/`
- ✅ Local development ports maintained
- ✅ Demo, documentation, and ML/fraud engine code retained for review

For detailed cleanup information, see:
- [CODE_REVIEW_READY.md](docs/CODE_REVIEW_READY.md) - Code review checklist
- [CLEANUP_REPORT.md](docs/CLEANUP_REPORT.md) - Detailed cleanup actions

## Security Notes

⚠️ **Important Security Considerations**

- Do not commit local `.env` files to version control
- Replace all placeholder secrets before production deployment
- Keep MongoDB and Redis private in production environments
- Enable secure cookies and trusted proxy headers only in intended production topology
- Keep internal fraud terminology out of the customer frontend
- Admin dashboard stores credentials in `sessionStorage`, not in source code
- Use environment variables for all sensitive configuration
- Implement proper database backups and disaster recovery

## Deployment Guide

### Production Deployment

For VPS + Docker Compose deployment: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

### Free Tier Deployment

For free-tier review and demo hosting: See [docs/FREE_HOSTING.md](docs/FREE_HOSTING.md)

### Expected Production Domains

Update these placeholders in your deployment configuration:

- **Customer App**: `https://pdfcraft.yourdomain.com`
- **Admin App**: `https://admin.pdfcraft.yourdomain.com`
- **API Backend**: `https://api.pdfcraft.yourdomain.com`

## Known Limitations

⚠️ **Current Limitations & Future Work**

| Limitation | Impact | Planned Solution |
| --- | --- | --- |
| **Local Docker volumes** | Single-instance only; multi-instance needs shared storage | S3 or Cloudflare R2 object storage |
| **Ephemeral file storage** | PDFs/models lost on Render redeploy | External object storage (S3/R2) |
| **Client-side refresh tokens** | Security risk in strict production | Move to HttpOnly secure cookies |
| **ML as decision support** | Should not be sole enforcement | Rule engine fallback (✓ implemented) |
| **Manual model training** | Free hosting skips online retraining | Local training + manual artifact upload |
| **Billing system** | Not yet implemented | Future enhancement |

## Next Improvements (Roadmap)

1. **Object Storage Integration**
   - Move generated PDFs to S3/Cloudflare R2
   - Enable horizontal scaling and multi-instance deployments
   - Persist model artifacts across deployments

2. **Security Hardening**
   - Implement stronger secret management (Vault/AWS Secrets Manager)
   - Add CI/CD checks for builds, tests, and forbidden terminology scans
   - Enforce RBAC for admin access

3. **Observability & Monitoring**
   - Add distributed tracing for request debugging
   - Monitor fraud decision drift over time
   - Track model performance metrics and retraining needs
   - Dashboard for fraud trends and anomalies

4. **ML Enhancements**
   - Scheduled automated retraining pipeline
   - Model evaluation and A/B testing framework
   - Advanced deep learning experiments (GPU support for autoencoders, sequence models)
   - Federated learning for privacy-preserving training

5. **Product Features**
   - Implement customer billing and subscription management
   - Enhanced analytics and usage reporting
   - Advanced admin investigation tools
   - Customer communication for blocked attempts

## Documentation

For detailed information, see:

- **[LEAD_REPORT.md](docs/LEAD_REPORT.md)** - Comprehensive project overview and design decisions
- **[INTERVIEW_EXPLANATION.md](docs/INTERVIEW_EXPLANATION.md)** - Interview Q&A and explanation
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[FREE_HOSTING.md](docs/FREE_HOSTING.md)** - Free tier hosting setup
- **[CODE_REVIEW_READY.md](docs/CODE_REVIEW_READY.md)** - Code review checklist
- **[CLEANUP_REPORT.md](docs/CLEANUP_REPORT.md)** - Detailed cleanup report

## Contributing

When submitting changes:

1. Keep customer-facing UI free of fraud/ML terminology
2. Update documentation for significant changes
3. Add tests for new features
4. Verify both local Docker setup and free-tier hosting path
5. Run syntax checks before committing

## License

[Add your license information here]

## Support & Questions

For questions about deployment, architecture, or fraud detection logic, refer to the documentation in `docs/` or review the comments in the respective source files.

---

**Last Updated**: May 26, 2026  
**Latest Changes**: Finalized fraud-resistant cross-browser anonymous usage tracking with IP quota synchronization  
**Repository**: [Shyam-2315/fraud-proof-pdf-platform](https://github.com/Shyam-2315/fraud-proof-pdf-platform)
