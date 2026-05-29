# Phase 15 — Deployment Validation Notes

## Automated (local / CI)

```bash
cd backend
source .venv/bin/activate
python scripts/validate_deployment_readiness.py
alembic upgrade head
pytest
python scripts/run_pilot_workflow.py
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy DSN (SQLite dev, Postgres/Cloud SQL prod) |
| `USE_SQL_REPOSITORY` | `true` for production persistence |
| `JWT_SECRET_KEY` | Must be non-default in production |
| `USE_LOCAL_STORAGE` | `true` for local PDF artifacts; `false` for GCS |
| `STORAGE_BUCKET` | GCS bucket name when not using local storage |

## Live GCP validation (requires credentials)

These steps require project access and were not executed in the Phase 15 automated session:

1. **Cloud Run** — Deploy image, confirm `GET /api/v1/health` returns `database: connected`.
2. **Cloud SQL** — Run `alembic upgrade head` via Cloud SQL Auth Proxy; confirm head `a8f1c2d3e4b5`.
3. **GCS** — Set `USE_LOCAL_STORAGE=false`, generate a package, confirm `gs://` storage reference and download.
4. **Secrets** — Confirm `BUILDDESK_DATABASE_URL` and `JWT_SECRET_KEY` in Secret Manager.

## Clean database bootstrap

```bash
alembic upgrade head
```

On empty Postgres/SQLite, all migrations from `304c157197b5` through `a8f1c2d3e4b5` must apply without error.

If a local `builddesk.db` was created before Phase 14 migrations, delete it or run `alembic upgrade head` on a fresh file — stale schemas cause pilot/workflow failures (e.g. missing `units.status`). The pilot script now runs `alembic upgrade head` automatically at startup.
