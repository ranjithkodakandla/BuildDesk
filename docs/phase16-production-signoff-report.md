# PHASE 16 PRODUCTION SIGN-OFF REPORT

**Date:** 2026-05-29  
**Branch:** `feat/phase16-production-signoff` → **`canonical-phase16`** @ `3425c68`  
**GCP project:** `stonedesk-app`  
**Service:** `builddesk-api` revision `builddesk-api-00019-6p8` (image `3425c68`)

---

## Executive summary

Phase 16 implemented durable **GCS artifact storage**, production **CORS/env hardening**, **API proxy downloads** for GCS objects, realistic **load validation**, and operator/browser documentation. Live staging re-validated **11/11** with `gs://` package references.

**Final verdict: CONDITIONAL GO**

Backend pilot on Cloud Run + GCS is production-capable for controlled rollout. Full **GO** requires a hosted production frontend origin in CORS and completed manual browser sign-off.

---

## GCS validation

| Item | Status |
|------|--------|
| Bucket | `gs://builddesk-artifacts-stonedesk-app` (us-central1) |
| IAM | `storage.objectAdmin` for `149130710868-compute@developer.gserviceaccount.com` |
| Cloud Run env | `USE_LOCAL_STORAGE=false`, `STORAGE_BUCKET=builddesk-artifacts-stonedesk-app` |
| Package upload | `gs://builddesk-artifacts-stonedesk-app/projects/.../packages/{id}.pdf` |
| Download path | API proxies bytes (no signed-URL key on Cloud Run) |
| Local dev | `USE_LOCAL_STORAGE=true` unchanged |

---

## Deployment / config validation

| Check | Result |
|-------|--------|
| `deploy.sh` | GCS bucket, CORS, `GCP_PROJECT_ID` env vars |
| `cloudbuild.yaml` | Aligned substitutions |
| `.env.gcp.example` | Documented GCS + CORS |
| Startup checks | JWT, bucket, CORS warnings in production |
| `ALLOWED_ORIGINS` parsing | Fixed (comma-separated string) |
| CORS preflight | **PASS** for `http://localhost:5173` |

---

## Live API validation

| Suite | Result |
|-------|--------|
| Staging (`run_staging_validation.py`) | **11/11**, 200 units, ~19.5s |
| Load (`run_load_validation.py`) | **PASS**, 8 assemblies, 200 units, ~9.5s |
| pytest | **76/76** |
| frontend test/build | **17/17**, build OK |

### Load metrics (live)

| Metric | Value |
|--------|-------|
| Assembly setup | 2.99s (8 assemblies) |
| Bulk 200 units | 0.72s |
| Package poll | 1.93s |
| PDF size | 19,517 bytes |
| PDF download | 0.47s |
| Total | 9.53s |

---

## Browser validation

- Documented in `docs/phase16-browser-validation.md`
- CORS confirmed for Vite dev origin
- Manual UI click-through: **recommended**, not automated in CI

---

## Security review

| Area | Finding |
|------|---------|
| JWT | Secret Manager wired; startup rejects default in production |
| Tenant isolation | Re-validated in staging script |
| GCS access | Scoped to service account; downloads require JWT |
| CORS | Explicit allowlist (not `*`) with credentials |
| Public Cloud Run | API unauthenticated at edge; protected routes require JWT |

---

## Operational readiness

| Capability | Status |
|------------|--------|
| Durable PDFs | Yes (GCS) |
| Export artifacts | Yes (GCS via `upload_bytes`) |
| Deploy script | Updated |
| Load script | `make load-validate` |
| Monitoring/alerts | Not in scope |

---

## Remaining risks

1. Production frontend URL not in `ALLOWED_ORIGINS` until hosted.
2. Manual browser sign-off pending (operator checklist).
3. Very large packages (300+ units, dense drawings) not load-tested to SLA.
4. GCS costs/retention lifecycle not configured.

---

## Final verdict

**CONDITIONAL GO**

Approved for **pilot production** with Cloud Run + Cloud SQL + GCS when operators use documented origins and complete the 5-minute browser smoke. Upgrade to **GO** after production frontend deployment + manual sign-off + optional load test at full drawing fidelity.

---

## References

- `docs/phase16-browser-validation.md`
- `artifacts/staging_validation_report.json`
- `artifacts/load_validation_report.json`
- `backend/app/services/cloud_storage.py`
