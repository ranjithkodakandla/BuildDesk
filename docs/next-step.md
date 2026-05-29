# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 15.5 — Live Staging Validation (partial live; fixes on branch) |
| Git branch         | `feat/phase15-5-live-staging-validation` |
| Test baseline      | Backend `71 / 71` pytest; frontend `17 / 17`; production build succeeds |
| Migration state    | Head `a8f1c2d3e4b5` (package generation metadata) |
| Pilot workflow     | `backend/scripts/run_pilot_workflow.py` passing end-to-end |
| Deployment script  | `backend/scripts/validate_deployment_readiness.py` |

---

## Immediate Next Milestone

**Phase 16 — Staging Redeploy & Full Live Verification**

Phase 15.5 identified a live auth blocker (tenant FK on register). Fix is committed; full live workflow validation requires redeploy.

### Next Execution Target

1. Create `BUILDDESK_JWT_SECRET` in Secret Manager; verify `BUILDDESK_DATABASE_URL`.
2. `alembic upgrade head` on Cloud SQL (head `a8f1c2d3e4b5`).
3. Deploy `feat/phase15-5-live-staging-validation` to Cloud Run (`make deploy-gcp` / `deploy.sh`).
4. Re-run `python backend/scripts/run_staging_validation.py` (200+ units).
5. Manual browser checklist in `docs/phase15-5-staging-validation.md`.

---

## Pending Blockers

- Live `POST /auth/register` returns 500 until redeploy with tenant bootstrap fix.
- GCS artifact persistence not implemented (placeholder upload path).
- `gcloud` service env audit requires operator credentials.
