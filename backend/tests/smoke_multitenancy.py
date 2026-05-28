"""
Smoke Tests: Multi-Tenant Isolation
===================================
Exercises tenant scoping on the persistence layer and API.
Verifies that Tenant A cannot access Tenant B's data.
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.main import app

PASS = "✓"
FAIL = "✗"

client = TestClient(app)

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

def assert_status(resp, expected: int, label: str) -> None:
    if resp.status_code != expected:
        fail(label, f"Expected HTTP {expected}, got {resp.status_code}: {resp.text[:200]}")

def run_suite(backend: str) -> None:
    print(f"\nBuildDesk · Multi-Tenant Smoke Tests [{backend}]")

    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    payload = {
        "shape_type": "rectangle",
        "project_id": project_id,
        "tenant_id": tenant_a,  # In the request body (will also check against header)
        "dimensions": {"length": 96.0, "width": 26.0},
    }

    # ── 1. Tenant A Creates Geometry ─────────────────────────────────────────
    section("1. Tenant A Creates Geometry")
    resp_create = client.post("/api/v1/geometry", json=payload, headers={"X-Tenant-ID": tenant_a})
    assert_status(resp_create, 200, "create geometry")
    geom_id = resp_create.json()["geometry_id"]
    ok("Tenant A", f"Created geometry: {geom_id}")

    # ── 2. Tenant A Retrieves Geometry ───────────────────────────────────────
    section("2. Tenant A Retrieves Geometry")
    resp_get_a = client.get(f"/api/v1/geometry/{geom_id}", headers={"X-Tenant-ID": tenant_a})
    assert_status(resp_get_a, 200, "tenant a retrieval")
    ok("Tenant A", "Successfully retrieved own geometry")

    # ── 3. Tenant B Attempts Retrieval ───────────────────────────────────────
    section("3. Tenant B Attempts Retrieval (Isolation)")
    resp_get_b = client.get(f"/api/v1/geometry/{geom_id}", headers={"X-Tenant-ID": tenant_b})
    assert_status(resp_get_b, 404, "tenant b isolation")
    ok("Tenant B", "404 - Cannot retrieve Tenant A's geometry")

    # ── 4. Demo Workflow ─────────────────────────────────────────────────────
    section("4. Demo Workflow Compatibility")
    resp_demo = client.get("/api/v1/demo/rectangle")
    assert_status(resp_demo, 200, "demo endpoint")
    if "X-BuildDesk-Demo" not in resp_demo.headers:
        fail("demo endpoint", "Missing demo header")
    ok("Demo API", "Functions correctly without explicit tenant header")


def run_all() -> None:
    # Run with InMemory repository
    os.environ["USE_SQL_REPOSITORY"] = "false"
    run_suite("In-Memory Backend")

    # Run with SQL repository
    os.environ["USE_SQL_REPOSITORY"] = "true"
    
    # Must initialize the DB if testing SQL
    from app.db.session import init_db
    init_db()
    
    run_suite("SQL Backend")

    print(f"\n{'═' * 60}")
    print(f"  All Multi-Tenant Isolation smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
