# Phase 15.5b — Deploy Recovery & Live Revalidation

**Branch:** `feat/phase15-5-live-staging-validation`  
**GCP project:** `stonedesk-app`  
**Cloud Run service:** `builddesk-api` (`us-central1`)  
**Cloud SQL instance:** `stonedesk-app:us-central1:builddesk-db`  
**Service URL:** `https://builddesk-api-149130710868.us-central1.run.app`

---

## Pre-deploy status (automated audit)

| Check | Result |
|-------|--------|
| Branch | `feat/phase15-5-live-staging-validation` @ `f0aa8b8` |
| Uncommitted | `artifacts/pilot_package.pdf`, `artifacts/staging_validation_report.json` only |
| Backend pytest | **71 / 71** |
| Frontend | **17 / 17**, build OK |
| Live `GET /health` | **PASS** (`cloudsql-postgres-connected`) |
| Live `POST /auth/register` | **FAIL 500** (old revision — tenant FK fix not deployed) |

---

## Operator checklist (copy-paste)

### A. Authenticate & select project

```bash
gcloud auth login
gcloud config set project stonedesk-app
```

### B. Verify / create secrets (Secret Manager)

```bash
# List secrets
gcloud secrets list --project=stonedesk-app

# DATABASE_URL — must exist (update if connection string changed)
gcloud secrets versions access latest --secret=BUILDDESK_DATABASE_URL --project=stonedesk-app | head -c 40 && echo "..."

# JWT — create if missing (one-time)
openssl rand -hex 32 | gcloud secrets create BUILDDESK_JWT_SECRET --data-file=- --project=stonedesk-app 2>/dev/null \
  || openssl rand -hex 32 | gcloud secrets versions add BUILDDESK_JWT_SECRET --data-file=- --project=stonedesk-app
```

Expected Cloud Run secret env mapping (in `deploy.sh`):

- `DATABASE_URL` ← `BUILDDESK_DATABASE_URL:latest`
- `JWT_SECRET_KEY` ← `BUILDDESK_JWT_SECRET:latest`

### C. IAM for Cloud Run service account (if not already granted)

```bash
PROJECT_NUMBER=$(gcloud projects describe stonedesk-app --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding stonedesk-app \
  --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding stonedesk-app \
  --member="serviceAccount:${SA}" --role="roles/cloudsql.client"
```

### D. Run Alembic migrations on Cloud SQL (via Auth Proxy)

```bash
# Terminal 1 — start proxy
cloud-sql-proxy stonedesk-app:us-central1:builddesk-db

# Terminal 2 — migrate (replace USER/PASSWORD)
cd backend
source .venv/bin/activate
export DATABASE_URL="postgresql+psycopg://builddesk_user:YOUR_PASSWORD@127.0.0.1:5432/builddesk"
alembic current
alembic upgrade head
# Expected head: a8f1c2d3e4b5
```

### E. Deploy to Cloud Run (local docker build — recommended)

```bash
cd backend

export GCP_PROJECT_ID=stonedesk-app
export GCP_REGION=us-central1
export CLOUDSQL_INSTANCE=stonedesk-app:us-central1:builddesk-db

# Builds linux/amd64, pushes to Artifact Registry, deploys with secrets + Cloud SQL
./scripts/deploy.sh
```

**Or via Makefile:**

```bash
cd backend
CLOUDSQL_INSTANCE=stonedesk-app:us-central1:builddesk-db \
GCP_PROJECT_ID=stonedesk-app \
make deploy-cloudsql
```

**Environment flags deployed:**

| Variable | Value | Notes |
|----------|-------|-------|
| `APP_ENV` | `production` | |
| `USE_SQL_REPOSITORY` | `true` | |
| `USE_LOCAL_STORAGE` | `true` | **Required until GCS upload is implemented** |
| `DATABASE_URL` | secret | Cloud SQL socket DSN |
| `JWT_SECRET_KEY` | secret | Non-default signing key |

Optional post-deploy CORS (if browser calls API directly):

```bash
gcloud run services update builddesk-api \
  --region=us-central1 --project=stonedesk-app \
  --update-env-vars ALLOWED_ORIGINS=http://localhost:5173,https://YOUR_FRONTEND_ORIGIN
```

### F. Post-deploy smoke (immediate)

```bash
export CLOUD_RUN_URL=https://builddesk-api-149130710868.us-central1.run.app

cd backend
make check-staging-health

# Register must return 201 (not 500)
TENANT_ID=$(uuidgen)
curl -sS -w "\nHTTP %{http_code}\n" -X POST "$CLOUD_RUN_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"email":"deploy-smoke@example.com","password":"StagingPass123!","role":"admin"}'
```

### G. Full live revalidation (after deploy succeeds)

```bash
cd backend
source .venv/bin/activate
STAGING_API_URL=https://builddesk-api-149130710868.us-central1.run.app \
STAGING_UNIT_COUNT=200 \
STAGING_POLL_TIMEOUT_S=300 \
python scripts/run_staging_validation.py
```

Or:

```bash
cd backend && make staging-validate
```

Report written to `artifacts/staging_validation_report.json`.

---

## cloudbuild.yaml note

`cloudbuild.yaml` is now aligned with `deploy.sh` (Cloud SQL + secrets). Prefer `deploy.sh` locally on Apple Silicon (forces `linux/amd64`). Cloud Build requires log-writer IAM on the build service account.

---

## What this deploy fixes

- **Tenant bootstrap on register** (`_ensure_tenant_exists` in `auth.py`)
- **Phase 15** package retry / `generation_error` metadata (requires migration `a8f1c2d3e4b5`)
- **JWT** from Secret Manager (not code default)

---

## Known limitations after deploy

1. **GCS not implemented** — PDFs stored on container filesystem (`USE_LOCAL_STORAGE=true`). Artifacts survive until instance recycle; not durable across scale-out.
2. **CORS** — set `ALLOWED_ORIGINS` if frontend is not using Vite proxy.
3. **Large packages (200+ units)** — may take 30–120s; poll `/package/status`.

---

## Human approval required

- Executing `deploy.sh` / `gcloud run deploy` (cloud mutation)
- Creating/updating Secret Manager values
- Running migrations against production Cloud SQL
