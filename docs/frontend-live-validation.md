# Frontend Live Validation

**Date:** 2026-05-29  
**Branch:** `feat/frontend-live-validation`

---

## Deployment strategy (Task 1)

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **Cloud Run (nginx static)** | **Selected** | Same GCP project/Artifact Registry as API; SPA `try_files`; no Firebase site setup; IAM already working |
| Firebase Hosting | Deferred | Firebase site not provisioned; CLI error on default site |
| GCS static only | Rejected | No native SPA fallback for client routes |
| Vercel | Rejected | Extra vendor; CORS/origin management outside current GCP footprint |

---

## Live deployment (Task 2)

| Item | Value |
|------|--------|
| **Frontend URL** | https://builddesk-web-149130710868.us-central1.run.app |
| **Service** | `builddesk-web` revision `builddesk-web-00001-48s` |
| **API** | https://builddesk-api-149130710868.us-central1.run.app |
| **Build** | Vite production + `VITE_API_BASE_URL` → `/api/v1` on API host |
| **CORS** | API `ALLOWED_ORIGINS` includes frontend URL + `http://localhost:5173` (revision `builddesk-api-00020-msm`) |

Deploy:

```bash
cd frontend
./scripts/deploy-hosting.sh
```

---

## Runtime fixes applied

1. **`resolveApiV1Base()`** — production requests target `{API}/api/v1/...` (fixes broken `/projects` paths).
2. **Authenticated downloads** — package PDF + exports use `fetch` + Bearer token (fixes `window.open` 401).
3. **SVG preview** — blob URL via authenticated axios (fixes unauthenticated `<img src>`).
4. **Export download** — correct `bd_token` / `bd_tenant_id` localStorage keys.
5. **`deploy.sh` CORS** — gcloud `^;^` delimiter for comma-separated `ALLOWED_ORIGINS`.

---

## E2E validation (Task 3) — Playwright vs live stack

Command:

```bash
cd frontend
FRONTEND_URL=https://builddesk-web-149130710868.us-central1.run.app npx playwright test e2e/
```

| Workflow | Browser E2E | Notes |
|----------|-------------|-------|
| Register | **PASS** | `live-smoke.spec.ts` |
| Login | **PASS** | Implicit via register session |
| Tenant settings | **PASS** | Settings tab, Company name field visible |
| Project creation | **PASS** | + New Project → workspace |
| Hierarchy tab | **PASS** | Tab navigation |
| Assemblies | **Partial** | Tab exists; create/SVG not automated |
| Package generation | **Partial** | Packages tab loads; generate not automated |
| PDF download | **Partial** | Fix deployed; not clicked in E2E |
| Revision / approval / RFI | **Not automated** | API-validated in Phase 16 scripts |
| Search | **Not automated** | Tab present on workspace |
| Exports modal | **PASS** | Modal opens/closes |
| Branding save | **Partial** | UI loads; save not clicked in E2E |

**Playwright:** 2/2 tests passed (~10s).

Screenshots on failure: `frontend/test-results/`.

---

## Deployment hardening (Task 4)

| Area | Status |
|------|--------|
| `VITE_API_BASE_URL` in `.env.production` | Configured |
| Auth persistence (`bd_token`, `bd_tenant_id`) | Working |
| SPA routing (nginx `try_files`) | Working |
| CORS | Verified preflight from frontend origin |
| Error handling (401 → logout) | Unchanged, working |

---

## FRONTEND LIVE VALIDATION REPORT

### Configuration

- **Hosting:** Cloud Run `builddesk-web` (nginx:alpine)
- **API base:** `https://builddesk-api-149130710868.us-central1.run.app/api/v1`
- **Auth:** JWT in localStorage; `X-Tenant-ID` on register/login + interceptor

### Bugs found & fixed

| Bug | Fix |
|-----|-----|
| Production API paths missing `/api/v1` | `resolveApiV1Base()` |
| PDF/export download 401 | Authenticated `fetch` downloads |
| SVG preview 401 | Blob URL from axios |
| Export wrong localStorage keys | `bd_token` / `bd_tenant_id` |
| CORS comma in gcloud deploy | `^;^` env delimiter |

### Remaining blockers

- Full browser walkthrough of package generate → PDF download, assemblies editor, RFI/approval UI not yet automated.
- Firebase Hosting optional path documented but not used.
- Custom domain / TLS for branded URL not configured.

### Readiness verdict

**CONDITIONAL GO**

Deployed frontend successfully talks to live API for core auth and navigation flows. **GO** for pilot UI requires extended Playwright coverage or manual sign-off on package/assembly/RFI paths.

---

## References

- `frontend/e2e/live-smoke.spec.ts`
- `frontend/e2e/workspace-flows.spec.ts`
- `docs/phase16-browser-validation.md`
