"""
Smoke Tests: SQL Persistence
============================
Exercises the SQLGeometryRepository to ensure the abstraction holds.
"""

from __future__ import annotations

import os
import sys
import uuid

# Force SQL repo
os.environ["USE_SQL_REPOSITORY"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.db.models import GeometryRecord
from app.main import app
from app.dependencies import get_geometry_repository
from app.repositories.sqlalchemy_repo import SQLGeometryRepository


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

def run_all() -> None:
    print("\nBuildDesk · SQL Persistence Layer Smoke Tests")

    init_db()

    project_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    payload = {
        "shape_type": "rectangle",
        "project_id": project_id,
        "tenant_id": tenant_id,
        "dimensions": {"length": 96.0, "width": 26.0},
    }

    # ── 1. Create via API ────────────────────────────────────────────────────
    section("1. POST /api/v1/geometry (Create & Save via SQL)")
    
    resp_post = client.post("/api/v1/geometry", json=payload, headers={"X-Tenant-ID": tenant_id})
    if resp_post.status_code != 200:
        fail("api POST", f"Failed to generate and save: {resp_post.text}")
    
    geom_id = resp_post.json()["geometry_id"]
    ok("api POST", f"Returned geometry_id: {geom_id}")

    # ── 2. Verify Database State ─────────────────────────────────────────────
    section("2. Verify Database State")
    
    db: Session = SessionLocal()
    try:
        record = db.query(GeometryRecord).filter(GeometryRecord.id == geom_id).first()
        if not record:
            fail("db fetch", f"geometry_id {geom_id} not found in database")
        
        if record.project_id != project_id:
            fail("db schema", f"Expected project_id {project_id}, got {record.project_id}")
            
        if "pieces" not in record.payload:
            fail("db payload", "Saved payload is missing expected structure")
            
        ok("db fetch", "Geometry accurately stored in SQL Backend")
    finally:
        db.close()

    # ── 3. Retrieve via API ──────────────────────────────────────────────────
    section("3. GET /api/v1/geometry/{id} (Retrieve)")
    
    resp_get = client.get(f"/api/v1/geometry/{geom_id}", headers={"X-Tenant-ID": tenant_id})
    if resp_get.status_code != 200:
        fail("api GET", f"Failed to retrieve {geom_id}: {resp_get.text}")
        
    data = resp_get.json()
    if data["geometry_id"] != geom_id:
        fail("api GET", "Mismatch in retrieved geometry ID")
        
    ok("api GET", "Retrieved full GeometryResponse identically")

    print(f"\n{'═' * 60}")
    print(f"  All SQL persistence smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
