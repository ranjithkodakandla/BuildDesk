#!/usr/bin/env python3
"""
Phase 15 deployment readiness checks (local / CI).

Validates configuration and migration state without requiring live GCP credentials.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "database_url_set",
        bool(settings.database_url),
        settings.database_url.split("@")[-1] if settings.database_url else "missing",
    ))
    checks.append((
        "jwt_secret_not_default",
        settings.jwt_secret_key != "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
        or settings.app_env != "production",
        "production must override JWT secret",
    ))
    checks.append((
        "sql_repository_mode",
        True,
        f"use_sql_repository={settings.use_sql_repository}",
    ))

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    head = script.get_current_head()
    checks.append(("alembic_head_known", bool(head), head or "none"))

    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks.append(("database_connectivity", True, "ok"))
    except Exception as exc:
        checks.append(("database_connectivity", False, str(exc)))

    # GCS: document live validation requirement
    use_local = os.getenv("USE_LOCAL_STORAGE", "True").lower() in ("true", "1", "yes")
    checks.append((
        "artifact_storage_mode",
        True,
        "local mock" if use_local else f"GCS bucket {os.getenv('STORAGE_BUCKET', '')}",
    ))

    print("BuildDesk Phase 15 Deployment Readiness")
    print("=" * 50)
    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {name}: {detail}")

    print("\nLive cloud validation (manual):")
    print("  - Cloud Run health: GET /api/v1/health")
    print("  - Cloud SQL: alembic upgrade head on production DSN")
    print("  - GCS: set USE_LOCAL_STORAGE=false and STORAGE_BUCKET")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
