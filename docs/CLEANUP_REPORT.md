# Cleanup Report

## Files / Folders Removed

Removed from the repository working tree:

- tracked local env files:
  - `backend/.env`
  - `frontend/.env`
  - `pdfcraft-guardian-main/.env`
- tracked generated Python caches under:
  - `backend/app/**/__pycache__/`
  - `backend/scripts/__pycache__/`
  - `backend/tests/__pycache__/`
- customer frontend dead code:
  - `frontend/src/routes/`
  - `frontend/src/components/ui/`
  - `frontend/src/lib/`
  - `frontend/src/hooks/`
  - customer-side admin pages/components/API files
  - unused customer TanStack router/server files
- Windows metadata files:
  - `*:Zone.Identifier`
- temporary / generated frontend artifacts:
  - `frontend/bun.lock`
  - `frontend/bunfig.toml`
  - `frontend/components.json`
  - `frontend/wrangler.jsonc`
  - `frontend/.lovable/`
- temporary cookie artifact:
  - `cookies-deleted.txt`

## Files Kept Intentionally

- `backend/scripts/final_demo_check.py`
- `backend/scripts/demo_fraud_scenarios.py`
- `backend/scripts/generate_synthetic_fraud_dataset.py`
- `backend/scripts/train_fraud_models.py`
- all backend fraud/ML engine code
- `pdfcraft-guardian-main/` admin frontend
- `docs/` review, architecture, deployment, demo, and report material
- `tests/` and `backend/tests/`
- `scripts/backup_mongo.sh`
- `scripts/restore_mongo.sh`
- `scripts/backup_storage.sh`
- `scripts/check_production_env.py`

## Questionable Files Not Removed

- `tests/.pytest_cache/`
  - not removed because the directory is owned by `nobody:nogroup` and was not writable from this workspace session
  - recommended follow-up on the host:
    `sudo rm -rf tests/.pytest_cache`

## Files Changed / Created

- created root `.gitignore`
- updated backend env examples
- added `pdfcraft-guardian-main/.env.production.example`
- updated `docker-compose.yml`
- updated `docker-compose.prod.yml`
- updated `deploy-prod.sh`
- updated `deploy/nginx/conf.d/pdfcraft.conf`
- updated `scripts/check_production_env.py`
- updated `frontend/scripts/customer-ui-forbidden-scan.mjs`
- updated admin frontend review cleanup in:
  - `pdfcraft-guardian-main/src/routes/__root.tsx`
  - `pdfcraft-guardian-main/src/routes/admin.dashboard.tsx`
  - `pdfcraft-guardian-main/src/routes/admin.ml.tsx`
- updated `README.md`
- updated `docs/DEPLOYMENT.md`
- created `docs/CODE_REVIEW_READY.md`
- created `docs/CLEANUP_REPORT.md`

## Verification Commands Run

```bash
python3 -m compileall -q backend/app backend/scripts backend/tests
node frontend/scripts/customer-ui-forbidden-scan.mjs
python3 scripts/check_production_env.py --env backend/.env.production.example
docker compose config
docker compose -f docker-compose.prod.yml config
find . \( -type d \( -name '__pycache__' -o -name 'node_modules' -o -name 'dist' -o -name '.pytest_cache' \) -o -type f -name '*Zone.Identifier' \) | sort
```

## Verification Result

- `python3 -m compileall ...`: PASS
- customer UI forbidden-word scan: PASS
- production env checker against example file: PASS for structure, expected FAIL for placeholder secrets
- `docker compose config`: FAIL in this environment because `docker` is not installed in this WSL distro
- `docker compose -f docker-compose.prod.yml config`: FAIL in this environment because `docker` is not installed in this WSL distro
- residual clutter scan: only `tests/.pytest_cache/` remains

## Pass / Fail Summary

- Repository cleanup: PASS with one documented residual cache directory
- Documentation cleanup: PASS
- Deployment/readiness docs: PASS
- Docker-backed runtime validation: BLOCKED by local environment
