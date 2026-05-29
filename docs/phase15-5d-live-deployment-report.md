# FINAL LIVE DEPLOYMENT VALIDATION REPORT

**Phase:** 15.5d — Full Deploy + Live Closure  
**Date:** 2026-05-29  
**Branch:** `feat/phase15-5-live-staging-validation`  
**GCP project:** `stonedesk-app`  
**Service:** `builddesk-api` (us-central1)

---

## Executive summary

BuildDesk was deployed to Cloud Run with Cloud SQL at Alembic head `a8f1c2d3e4b5`, auth/register was restored, a package-manifest FK ordering bug was fixed and redeployed, and the full live staging validation script passed **11/11** steps including **200 units** in **15.09s**.

**Final verdict: CONDITIONAL GO**

Staging/pilot use on the live stack is validated. Full production launch remains blocked on durable artifact storage (GCS), browser CORS configuration, and committing the package-repository hotfix.

---

## Deployment summary

| Item | Value |
|------|--------|
| Service URL | `https://builddesk-api-149130710868.us-central1.run.app` |
| Latest revision | `builddesk-api-00015-jv4` (prior: `00014-sgr`, `00013-pnt`) |
| Container image | `us-central1-docker.pkg.dev/stonedesk-app/builddesk-repo/builddesk-api:8f94d01` |
| Cloud SQL | `stonedesk-app:us-central1:builddesk-db` |
| Alembic head | `a8f1c2d3e4b5` |
| Secrets | `BUILDDESK_DATABASE_URL`, `BUILDDESK_JWT_SECRET` |
| Env | `APP_ENV=production`, `USE_SQL_REPOSITORY=true`, `USE_LOCAL_STORAGE=true` |

### Commands executed (this session)

```bash
# Baseline
cd backend && source .venv/bin/activate && pytest   # 71 passed
cd frontend && npm test && npm run build             # 17 passed, build OK

# Live debugging — package FK fix
# Edit: app/repositories/package_repository.py — session.flush() before package_pages insert
pytest -q                                            # 71 passed

# Redeploy
cd backend
GCP_PROJECT_ID=stonedesk-app \
CLOUDSQL_INSTANCE=stonedesk-app:us-central1:builddesk-db \
./scripts/deploy.sh

# Full live validation
STAGING_UNIT_COUNT=200 STAGING_POLL_TIMEOUT_S=300 \
python scripts/run_staging_validation.py           # 11/11 passed
```

Earlier in Phase 15.5d (same branch): Secret Manager JWT secret created; Cloud SQL Proxy + `alembic upgrade head`; initial deploy to `00014-sgr`; register 201 confirmed.

---

## Migration state

- Cloud SQL upgraded from `b2c3d4e5f6g7` through Phase 14/15 chain to **`a8f1c2d3e4b5` (head)**.
- Health reports `database=cloudsql-postgres-connected`, `tenant_mode=true`.

---

## Live validation matrix

| Step | Result | Duration | Notes |
|------|--------|----------|-------|
| health | PASS | 0.36s | Cloud SQL connected |
| auth_register_login | PASS | 1.89s | Register + login + JWT |
| tenant branding | PASS | 0.70s | Canyon Staging Co profile |
| project_hierarchy | PASS | 1.54s | Building/floor/unit types |
| bulk_units (200) | PASS | 0.73s | 200 units created |
| assemblies | PASS | 1.53s | Create, duplicate, SVG preview |
| search | PASS | 0.31s | Project hit returned |
| package_generate | PASS | 1.04s | PDF 9034B, poll **0.32s**, 1 attempt |
| exports | PASS | 2.01s | 3 export jobs queued |
| revision_and_ops | PASS | 3.31s | Revision, approval, RFI |
| tenant_isolation | PASS | 1.66s | Cross-tenant blocked |
| **Total** | **11/11** | **15.09s** | `failed: 0` |

Artifact: `artifacts/staging_validation_report.json`

---

## Incidents resolved

### 1. Register 500 (resolved — revision 00014-sgr)

- **Cause:** New users’ `X-Tenant-ID` had no `tenants` row (FK).
- **Fix:** `_ensure_tenant_exists()` on register (already on branch).
- **Proof:** HTTP 201 + JWT on live register.

### 2. Package generate 500 at 200 units (resolved — revision 00015-jv4)

- **Cause:** `package_pages` inserted before `project_packages` row flushed → `ForeignKeyViolation` on large manifests.
- **Fix:** `session.flush()` in `PackageRepository.save_package()` before child page inserts.
- **Status:** Fix deployed; **not yet committed** to git (working tree change).

---

## Performance observations

| Area | Observation |
|------|-------------|
| API latency (200-unit run) | Full script **15s** wall clock; bulk units **0.73s** |
| PDF generation | Background poll **0.32s** for ~9KB PDF (minimal assembly set in staging) |
| Cloud Run | Cold/warm not isolated; revision 00015 serves 100% traffic |
| Cloud SQL | No connection errors during validation |
| Container storage | `USE_LOCAL_STORAGE=true` → `local:///app/.../mock_gcs/{package_id}.pdf` (ephemeral) |

**Note:** Staging creates one unit type + limited assemblies; PDF size/latency will grow with full multifamily drawing sets. Re-benchmark with production-like assembly counts before SLA commitments.

---

## Security findings

| Finding | Severity | Status |
|---------|----------|--------|
| Cloud Run `--allow-unauthenticated` | Medium | By design for API; JWT on protected routes |
| JWT secret in Secret Manager | OK | `BUILDDESK_JWT_SECRET` created and wired |
| Tenant isolation | OK | Live cross-tenant test passed |
| CORS | Low–Med | Dev proxy documented; direct browser→API may need `ALLOWED_ORIGINS` |
| Artifacts on container disk | Med | Not durable across scale-to-zero / new instances |

---

## Operations review

- **Cloud Run:** Deploy via `backend/scripts/deploy.sh`; image tag = `git rev-parse --short HEAD` (currently `8f94d01` with uncommitted layer for FK fix).
- **Cloud SQL:** Proxy on port 5433 used for migrations; instance linked on deploy.
- **GCS:** `CloudStorageService` still local/mock; `USE_LOCAL_STORAGE=true` intentional until GCS implemented.
- **Retries:** Package PDF `MAX_GENERATION_ATTEMPTS=2`; staging succeeded on attempt 1.
- **Monitoring:** No custom dashboards/alerts validated in this phase.

---

## Remaining blockers

1. **Commit** `package_repository.py` flush fix (deployed but uncommitted).
2. **GCS persistence** — PDFs/exports lost on instance recycle without bucket upload.
3. **CORS / frontend live URL** — manual browser checklist in `docs/phase15-5-staging-validation.md` not executed in this run.
4. **Image tag collision** — Redeploy reused tag `8f94d01` with new digest; prefer commit + new tag for traceability.
5. **bcrypt/passlib warning** in logs (`__about__`) — non-blocking; track dependency pin.

---

## Production readiness assessment

| Criterion | Staging | Production |
|-----------|---------|------------|
| Unit tests 71/71 | Yes | Yes |
| Live health + DB | Yes | Yes |
| Live auth | Yes | Yes |
| Live E2E script 200 units | Yes | Yes |
| Durable artifacts | No | No |
| GCS + signed URLs | No | No |
| Browser E2E | Not run | Not run |

---

## Final verdict

**CONDITIONAL GO**

The live deployed stack is suitable for **controlled staging/pilot** workloads with operator awareness of ephemeral PDF storage and the uncommitted hotfix. **GO** for general production requires GCS artifact persistence, committed deploy artifact, CORS/browser sign-off, and load testing with realistic assembly/page counts.

---

## References

- `docs/phase15-5-staging-validation.md`
- `docs/phase15-5b-deploy-recovery.md`
- `artifacts/staging_validation_report.json`
- `backend/scripts/run_staging_validation.py`
