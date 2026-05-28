"""
Smoke Tests: Persistence Layer
==============================
Exercises the repository abstraction and persistence flow:
    GeometryRepository (Protocol)
    InMemoryGeometryRepository (Implementation)
    FastAPI Depends(get_geometry_repository)
    POST /api/v1/geometry           → Saves GeometryResponse to repo
    GET  /api/v1/geometry/{id}      → Retrieves GeometryResponse from repo
    GET  /api/v1/geometry/{id}      → 404 for invalid ID

Run with:
    cd backend
    python -m tests.smoke_persistence
"""

import sys
import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_geometry_repository

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"

client = TestClient(app)

PROJECT_ID = str(uuid.uuid4())
TENANT_ID  = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · Persistence Layer Smoke Tests")

    repo = get_geometry_repository()

    # ── 1. Create via API ────────────────────────────────────────────────────
    section("1. POST /api/v1/geometry (Create & Save)")
    
    payload = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96.0, "width": 26.0},
    }
    
    create_resp = client.post("/api/v1/geometry", json=payload)
    assert_status(create_resp, 200, "create geometry API status")
    
    data = create_resp.json()
    geom_id = data["geometry_id"]
    
    ok("api POST", f"Returned geometry_id: {geom_id}")

    # ── 2. Repository state ──────────────────────────────────────────────────
    section("2. Verify Repository State")
    
    record = repo.get_by_id(uuid.UUID(geom_id))
    if not record:
        fail("repo fetch", f"geometry_id {geom_id} not found in in-memory repo")
    
    if str(record.geometry_id) != geom_id:
        fail("repo data mismatch", "UUIDs do not match")
        
    ok("repo", f"Geometry accurately stored in InMemoryGeometryRepository")

    # ── 3. Retrieve via API ──────────────────────────────────────────────────
    section("3. GET /api/v1/geometry/{id} (Retrieve)")
    
    get_resp = client.get(f"/api/v1/geometry/{geom_id}")
    assert_status(get_resp, 200, "get geometry API status")
    
    fetched_data = get_resp.json()
    if fetched_data["geometry_id"] != geom_id:
        fail("api fetch mismatch", "Fetched UUID does not match created UUID")
        
    if len(fetched_data["pieces"]) != 1:
        fail("api fetch pieces", f"Expected 1 piece, got {len(fetched_data['pieces'])}")
        
    ok("api GET", "Retrieved full GeometryResponse identically")

    # ── 4. Retrieve missing ──────────────────────────────────────────────────
    section("4. GET /api/v1/geometry/{missing_id} (404)")
    
    fake_id = str(uuid.uuid4())
    miss_resp = client.get(f"/api/v1/geometry/{fake_id}")
    assert_status(miss_resp, 404, "missing geometry returns 404")
    
    ok("api GET 404", "Missing geometry correctly handled")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All persistence smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
