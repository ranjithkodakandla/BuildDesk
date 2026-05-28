"""
Smoke Tests: PostgreSQL Integration
===================================
Tests that the BuildDesk PostgreSQL layer is fully functional, ensuring:
- Connection succeeds
- Migrations apply successfully
- CRUD works against the database
- Multi-tenancy works against Postgres
"""

import sys
import uuid
import subprocess
import os

# We will test against the local dockerized postgres
POSTGRES_URL = "postgresql+psycopg://builddesk:password@localhost:5432/builddesk"

# Set environment explicitly for the test client
os.environ["USE_SQL_REPOSITORY"] = "true"
os.environ["DATABASE_URL"] = POSTGRES_URL

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PASS = "✓"
FAIL = "✗"

def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {PASS}  [{label}]{suffix}")

def fail(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {FAIL}  [{label}]{suffix}")
    sys.exit(1)

def run_cmd(cmd: str) -> bool:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command failed: {cmd}")
        print(res.stderr)
        return False
    return True

def run_all() -> None:
    print("\nBuildDesk · PostgreSQL Integration Smoke Tests")
    
    # ── 1. Apply Migrations to Postgres ──────────────────────────────────────
    section("1. Alembic Migration against Postgres")
    if not run_cmd(f"USE_SQL_REPOSITORY=true DATABASE_URL='{POSTGRES_URL}' alembic upgrade head"):
        fail("migration", "Failed to apply migrations to PostgreSQL")
    ok("migration", "Applied Alembic schema to PostgreSQL")

    # ── 2. Create Geometry ───────────────────────────────────────────────────
    section("2. Geometry Persistence (CRUD)")
    tenant_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    payload = {
        "shape_type": "rectangle",
        "project_id": project_id,
        "tenant_id": tenant_id,
        "dimensions": {"length": 100, "width": 50}
    }
    
    resp_create = client.post("/api/v1/geometry", json=payload, headers={"X-Tenant-ID": tenant_id})
    if resp_create.status_code != 200:
        fail("api POST", f"Failed to save to Postgres: {resp_create.text}")
    geom_id = resp_create.json()["geometry_id"]
    ok("create", f"Saved geometry to Postgres: {geom_id}")

    # ── 3. Retrieve Geometry ─────────────────────────────────────────────────
    section("3. Retrieve Geometry")
    resp_get = client.get(f"/api/v1/geometry/{geom_id}", headers={"X-Tenant-ID": tenant_id})
    if resp_get.status_code != 200:
        fail("api GET", "Failed to retrieve geometry from Postgres")
    ok("retrieve", "Retrieved successfully")

    # ── 4. Multi-Tenant Isolation ────────────────────────────────────────────
    section("4. Tenant Isolation")
    tenant_b = str(uuid.uuid4())
    resp_bad = client.get(f"/api/v1/geometry/{geom_id}", headers={"X-Tenant-ID": tenant_b})
    if resp_bad.status_code != 404:
        fail("isolation", "Tenant B could access Tenant A's geometry")
    ok("isolation", "Postgres enforced tenant isolation (404)")

    print(f"\n{'═' * 60}")
    print("  All PostgreSQL integration smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
