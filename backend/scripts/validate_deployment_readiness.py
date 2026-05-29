#!/usr/bin/env python3
"""
Phase 16 deployment readiness checks (local / CI).

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
from app.startup_checks import run_startup_checks


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "database_url_set",
        bool(settings.database_url),
        settings.database_url.split("@")[-1] if settings.database_url else "missing",
    ))
    checks.append((
        "jwt_secret_not_default",
        not settings.jwt_secret_is_default or not settings.is_production,
        "ok" if not settings.jwt_secret_is_default else "default (dev only)",
    ))
    checks.append((
        "sql_repository_mode",
        settings.use_sql_repository,
        f"use_sql_repository={settings.use_sql_repository}",
    ))
    checks.append((
        "artifact_storage_mode",
        True,
        f"{settings.artifact_storage_mode} bucket={settings.storage_bucket}",
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

    print("BuildDesk Phase 16 Deployment Readiness")
    print("=" * 50)
    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {name}: {detail}")

    print("\nStartup checks (production rules):")
    for sc in run_startup_checks(settings):
        mark = "PASS" if sc.ok else "FAIL"
        if sc.level == "error" and not sc.ok:
            failed += 1
        print(f"  [{mark}] {sc.name} ({sc.level}): {sc.detail}")

    print("\nLive cloud validation:")
    print("  - Cloud Run: GET /api/v1/health")
    print("  - GCS: USE_LOCAL_STORAGE=false + service account storage.objectAdmin")
    print("  - CORS: browser preflight from frontend origin")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
