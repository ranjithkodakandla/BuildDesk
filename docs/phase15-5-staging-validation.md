# Phase 15.5 — Live Staging Validation Report

**Date:** 2026-05-29  
**Branch:** `feat/phase15-5-live-staging-validation`  
**Staging API:** `https://builddesk-api-149130710868.us-central1.run.app`  
**GCP project (documented):** `stonedesk-app`

---

## Executive summary

| Area | Result |
|------|--------|
| Live health / Cloud SQL connectivity | **PASS** |
| Live authenticated workflows | **BLOCKED** — `POST /auth/register` returns **500** on deployed revision |
| Local regression (pytest + pilot) | **PASS** — 71 pytest, pilot E2E ~2.6s |
| Production config audit | **Gaps found** — JWT secret, GCS, tenant bootstrap (fix committed, needs redeploy) |
| Browser E2E | **Not automated** — operator checklist below |

**Go / No-Go:** **No-Go for production** until redeploy with tenant bootstrap + JWT/GCS config. **Conditional Go** for continued staging after one Cloud Run deploy.

---

## Task 1 — Live Cloud Validation

| Check | Endpoint | Result | Notes |
|-------|----------|--------|-------|
| Health | `GET /api/v1/health` | **PASS** | `database: cloudsql-postgres-connected`, `tenant_mode: true` |
| Public shapes | `GET /api/v1/shapes` | **PASS** | 5 templates returned |
| Auth gate | `GET /api/v1/projects` (no token) | **PASS** | 401 — tenant context required |
| Register | `POST /api/v1/auth/register` | **FAIL** | **500 Internal Server Error** |
| Login | `POST /api/v1/auth/login` | **Not run** | Blocked by register |
| Tenant isolation | — | **Not run** | Blocked |
| Hierarchy / assemblies / packages / RFIs / search / exports | — | **Not run** | Blocked |
| Tenant branding | `PUT /tenant/profile` | **Not run** | Blocked |

### Root cause (auth 500)

Cloud SQL enforces `users.tenant_id → tenants.id` FK. Register creates a user without ensuring a `tenants` row exists when `X-Tenant-ID` is a new UUID.

**Fix (on branch):** `_ensure_tenant_exists()` in `app/api/auth.py` — auto-creates tenant on register. **Requires Cloud Run redeploy to validate live.**

### Staging script

`backend/scripts/run_staging_validation.py` — full live workflow runner (httpx). Executed against Cloud Run; stopped at auth. Re-run after deploy:

```bash
STAGING_API_URL=https://builddesk-api-149130710868.us-central1.run.app \
STAGING_UNIT_COUNT=200 \
python backend/scripts/run_staging_validation.py
```

---

## Task 2 — Production Config Audit

| Item | Status | Finding |
|------|--------|---------|
| `JWT_SECRET_KEY` | **UNSAFE** | Default in `config.py`; **not** in `deploy.sh` until Phase 15.5 update adds `BUILDDESK_JWT_SECRET` secret |
| `DATABASE_URL` | **OK** | Wired via Secret Manager in `deploy.sh` |
| Secret Manager | **Partial** | DB secret referenced; JWT secret must exist in GCP |
| Cloud SQL | **OK** | Health reports `cloudsql-postgres-connected` |
| Cloud Run env | **Partial** | `APP_ENV`, `USE_SQL_REPOSITORY` set; `USE_LOCAL_STORAGE=false` added in deploy script |
| GCS bucket | **NOT WIRED** | `CloudStorageService` GCS upload is placeholder; local mock default |
| CORS | **Review** | `.env.gcp.example` lists example origins; must match real frontend URL |
| Health probes | **OK** | `/api/v1/health` suitable for liveness/readiness |
| Tenant bootstrap | **FIXED in code** | Pending deploy |
| Alembic on Cloud SQL | **Assumed** | Live DB may be behind head `a8f1c2d3e4b5` — run `alembic upgrade head` via proxy before deploy |

`gcloud run services describe` was **not executed** (credentials path blocked in automation sandbox). Manual verification recommended.

---

## Task 3 — Async Package Validation

### Live (200–300 units)

**Not executed** — blocked at authentication.

### Local proxy (pilot workflow, SQLite, 150 units)

| Phase | Observation |
|-------|-------------|
| Full pilot E2E | **~2.6s** total (150 units, 3 package generations, exports, RFI, approvals) |
| Package poll (first) | Typically **< 2s** on local SQLite |
| Bottleneck at scale | PDF rendering CPU in same process as API (`BackgroundTasks`) — expect **30–120s+** for 200+ units on Cloud Run single instance |

### Expected live behavior (post-redeploy)

- `generation_attempts` / `generation_error` visible on failure (Phase 15)
- `POST .../retry-generation` for recovery
- Storage likely `local://` inside container unless GCS enabled — **artifacts not durable across instance restarts**

---

## Task 4 — Browser Workflow Validation

Automated browser tests were **not run** (no Playwright/Cypress in repo). Frontend points to live API via `frontend/.env` (`VITE_API_BASE_URL`).

### Operator checklist (manual)

| Workflow | UI surface | API dependency | Staging status |
|----------|------------|----------------|----------------|
| Login / Register | `LoginPage`, `RegisterPage` | Auth | **Blocked** until live register fixed |
| Project list / create | `DashboardPage` | `/projects` | Pending |
| Hierarchy + bulk units | `WorkspacePage` → `HierarchyPanel` | hierarchy + bulk | Pending |
| Assemblies | `AssembliesPanel` | `/assemblies` | Pending |
| Package generate + poll | `PackagesPanel` | package generate/status | Pending |
| Revisions list | `PackagesPanel` | `/packages` | Pending |
| Approval transitions | `PackagesPanel` / queues | transition API | Pending |
| Search / queues | `DashboardPage` | `/search` | Pending |
| Tenant branding | `TenantSettingsPanel` | `/tenant/profile` | Pending |
| PDF download | Packages panel | `/package/pdf` | Pending |

### Usability notes (code review, not live UI)

- Package panel polls status — adequate for async generation
- Bulk unit form supports multifamily scale
- No in-app indicator for `generation_error` text yet — operators may need API/status JSON

---

## Task 5 — Security findings

| Finding | Severity | Mitigation |
|---------|----------|------------|
| Auth register 500 leaks no detail | Medium | Fixed tenant bootstrap |
| Default JWT secret in code | **High** | Secret Manager + deploy.sh update |
| GCS not production-ready | **High** | Implement upload + `USE_LOCAL_STORAGE=false` |
| Import/export project_id guards | Low | Fixed in Phase 15 |
| Cross-tenant API | Low | Repository scoping + tests |

---

## Remaining blockers

1. **Redeploy Cloud Run** with `feat/phase15-5` (tenant bootstrap + Phase 15 hardening).
2. **Run `alembic upgrade head`** on Cloud SQL (`a8f1c2d3e4b5`).
3. **Create `BUILDDESK_JWT_SECRET`** in Secret Manager.
4. **Wire GCS** or accept ephemeral PDF storage on Cloud Run disk.
5. **Re-run** `run_staging_validation.py` after deploy.
6. **Manual browser pass** using checklist above.
7. **Configure CORS** for production frontend origin.

---

## Go / No-Go recommendation

| Environment | Recommendation |
|-------------|----------------|
| **Production SaaS** | **No-Go** |
| **Internal staging** | **Go after one redeploy + migration + secrets** |
| **Local / CI** | **Go** — 71 pytest, pilot green |

---

## Suggested commit message

```
feat(phase-15.5): live staging validation tooling and auth tenant bootstrap

Add staging validation script and report, bootstrap tenants on register for
Cloud SQL FK compliance, and harden deploy.sh secrets/GCS env documentation.
```
