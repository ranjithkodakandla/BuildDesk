"""
Phase 6: Pilot Validation Workflow Script
Executes a full multifamily countertop fabrication workflow via FastAPI TestClient.
Simulates a frontend client making HTTP requests.
"""

import sys
import os
import json
import uuid
from typing import Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup system path to import app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.db.models import Base
from app.db.session import engine, SessionLocal
from app.models.fabrication import AssemblyType, CutoutType, EdgeType, MountType, PartType, Position, SplashType
from app.models.hierarchy import UnitVariant

# Override engine to ensure we don't mess up dev DB, or just use dev DB since it's local.
# We'll use the main app to hit the real local SQLite DB.
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# We need a valid JWT token. We can simulate a login.
def get_auth_token() -> str:
    # First register or login
    email = f"pilot_{uuid.uuid4()}@builddesk.com"
    pwd = "password123"
    tenant_id = str(uuid.uuid4())
    
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "role": "admin"
    }, headers={"X-Tenant-ID": tenant_id})
    
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd
    }, headers={"X-Tenant-ID": tenant_id})
    res_json = res.json()
    if "access_token" not in res_json:
        print("Login failed:", res_json)
    return res_json["access_token"]

def run():
    print("Starting Pilot Validation Workflow...")
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Project Creation
    print("1. Creating Project...")
    res = client.post("/api/v1/projects", json={
        "name": "The Highland Residences",
        "client_name": "Highland Construction",
        "material": "Calacatta Quartz 3cm",
        "address": "789 Highland Ave, Denver CO",
        "status": "draft",
        "hierarchy_config": {
            "has_buildings": True,
            "has_floors": True,
            "has_unit_types": True
        }
    }, headers=headers)
    assert res.status_code == 201, res.text
    project_id = res.json()["project_id"]

    # 2. Hierarchy & Buildings
    print("2. Building Hierarchy...")
    # Add Building
    res = client.post(f"/api/v1/projects/{project_id}/buildings", json={
        "name": "North Tower",
        "code": "NT",
        "sort_order": 1
    }, headers=headers)
    building_id = res.json()["building_id"]

    # Add Floors
    floor_ids = []
    for f in range(1, 6):
        res = client.post(f"/api/v1/projects/{project_id}/floors", json={
            "building_id": building_id,
            "name": f"Floor {f}",
            "number": f,
            "sort_order": f
        }, headers=headers)
        floor_ids.append(res.json()["floor_id"])

    # 3. Unit Types
    print("3. Defining Unit Types...")
    unit_types = {}
    
    # Type A
    res = client.post(f"/api/v1/projects/{project_id}/unit-types", json={
        "code": "A1",
        "name": "1 Bed / 1 Bath",
        "is_mirror": False,
        "is_ada": False,
        "sort_order": 1
    }, headers=headers)
    ut_a1 = res.json()
    unit_types["A1"] = ut_a1["unit_type_id"]

    # Type A-MIR
    res = client.post(f"/api/v1/projects/{project_id}/unit-types", json={
        "code": "A1-MIR",
        "name": "1 Bed / 1 Bath (Mirror)",
        "is_mirror": True,
        "is_ada": False,
        "base_type_id": ut_a1["unit_type_id"],
        "sort_order": 2
    }, headers=headers)
    unit_types["A1-MIR"] = res.json()["unit_type_id"]

    # Type B1
    res = client.post(f"/api/v1/projects/{project_id}/unit-types", json={
        "code": "B1",
        "name": "2 Bed / 2 Bath",
        "is_mirror": False,
        "is_ada": False,
        "sort_order": 3
    }, headers=headers)
    unit_types["B1"] = res.json()["unit_type_id"]

    # 4. Units (Simulate creating ~150 units across 5 floors using Bulk API)
    print("4. Instantiating Units (150 units using Bulk Engine)...")
    for f_idx, floor_id in enumerate(floor_ids):
        floor_num = f_idx + 1
        # Floor 1: 101 - 130
        client.post(f"/api/v1/projects/{project_id}/units/bulk", json={
            "building_id": building_id,
            "floor_id": floor_id,
            "unit_type_id": unit_types["A1"],
            "start_number": 1,
            "end_number": 10,
            "prefix": f"{floor_num}0",
            "variant": "standard"
        }, headers=headers)
        
        client.post(f"/api/v1/projects/{project_id}/units/bulk", json={
            "building_id": building_id,
            "floor_id": floor_id,
            "unit_type_id": unit_types["A1-MIR"],
            "start_number": 11,
            "end_number": 20,
            "prefix": f"{floor_num}",
            "variant": "MIR"
        }, headers=headers)
        
        client.post(f"/api/v1/projects/{project_id}/units/bulk", json={
            "building_id": building_id,
            "floor_id": floor_id,
            "unit_type_id": unit_types["B1"],
            "start_number": 21,
            "end_number": 30,
            "prefix": f"{floor_num}",
            "variant": "standard"
        }, headers=headers)

    # 5. Assemblies
    print("5. Configuring Assemblies...")
    
    def create_assembly(name, asm_type, ut_id, parts, notes=[]):
        res = client.post(f"/api/v1/assemblies", json={
            "project_id": project_id,
            "unit_type_id": ut_id,
            "name": name,
            "assembly_type": asm_type.value,
            "variant": "standard",
            "parts": parts,
            "notes": notes
        }, headers=headers)
        assert res.status_code == 201, res.text
        return res.json()

    # A1 Kitchen
    asm_a1 = create_assembly(
        "A1 Kitchen", 
        AssemblyType.KITCHEN, 
        unit_types["A1"],
        parts=[
            {
                "part_type": PartType.MAIN_TOP.value,
                "name": "Main Sink Run",
                "dimensions": {"length": 110.0, "depth": 25.5, "thickness": 1.25},
                "edges": [
                    {"position": Position.FRONT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.LEFT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.RIGHT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.BACK.value, "edge_type": EdgeType.RAW.value}
                ],
                "cutouts": [
                    {
                        "cutout_type": CutoutType.SINK.value,
                        "mount_type": MountType.UNDERMOUNT.value,
                        "dimensions": {"length": 30.0, "depth": 18.0},
                        "center_x": 55.0,
                        "center_y": 12.0
                    }
                ],
                "holes": [
                    {"diameter": 1.375, "center_x": 55.0, "center_y": 3.5, "purpose": "Faucet"},
                    {"diameter": 1.375, "center_x": 48.0, "center_y": 3.5, "purpose": "Soap Dispenser"}
                ],
                "splashes": [
                    {"splash_type": SplashType.BACKSPLASH.value, "dimensions": {"length": 110.0, "depth": 4.0}},
                    {"splash_type": SplashType.LEFT_SPLASH.value, "dimensions": {"length": 24.25, "depth": 4.0}},
                    {"splash_type": SplashType.RIGHT_SPLASH.value, "dimensions": {"length": 24.25, "depth": 4.0}}
                ]
            }
        ],
        notes=[{"content": "Template required for wall scribing."}]
    )

    # A1-MIR Kitchen (we duplicate from A1 Kitchen)
    print("   Duplicating Assembly for A1-MIR...")
    client.post(f"/api/v1/assemblies/{asm_a1['assembly_id']}/duplicate", json={
        "new_name": "A1 Kitchen (Mirror)",
        "new_unit_type_id": unit_types["A1-MIR"],
        "variant": "MIR"
    }, headers=headers)

    # B1 L-Shape Kitchen
    create_assembly(
        "B1 Kitchen", 
        AssemblyType.KITCHEN, 
        unit_types["B1"],
        parts=[
            {
                "part_type": PartType.MAIN_TOP.value,
                "name": "Sink Run",
                "dimensions": {"length": 90.0, "depth": 25.5},
                "edges": [
                    {"position": Position.FRONT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.LEFT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.BACK.value, "edge_type": EdgeType.RAW.value},
                    {"position": Position.RIGHT.value, "edge_type": EdgeType.RAW.value} # Seam
                ],
                "cutouts": [
                    {"cutout_type": "sink", "mount_type": "undermount", "dimensions": {"length": 32, "depth": 18}, "center_x": 45, "center_y": 12.5}
                ],
                "holes": [
                    {"diameter": 1.375, "center_x": 45, "center_y": 4, "purpose": "Faucet"}
                ],
                "splashes": [{"splash_type": "backsplash", "dimensions": {"length": 90, "depth": 4}}]
            },
            {
                "part_type": PartType.LEFT_RETURN.value,
                "name": "Range Run",
                "dimensions": {"length": 60.0, "depth": 25.5},
                "edges": [
                    {"position": Position.FRONT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.RIGHT.value, "edge_type": EdgeType.EASED.value},
                    {"position": Position.BACK.value, "edge_type": EdgeType.RAW.value},
                    {"position": Position.LEFT.value, "edge_type": EdgeType.RAW.value} # Seam
                ],
                "cutouts": [
                    {"cutout_type": "cooktop", "mount_type": "drop_in", "dimensions": {"length": 30, "depth": 21}, "center_x": 30, "center_y": 12.5}
                ],
                "splashes": [{"splash_type": "backsplash", "dimensions": {"length": 60, "depth": 4}}]
            }
        ],
        notes=[{"content": "Dogleg seam requires clear epoxy color match."}]
    )

    # 6. SVG Preview Test
    print("6. Validating SVG Previews...")
    assemblies_res = client.get(f"/api/v1/assemblies?project_id={project_id}", headers=headers)
    assemblies = assemblies_res.json().get("assemblies", [])
    for asm in assemblies:
        svg_res = client.get(f"/api/v1/assemblies/{asm['assembly_id']}/preview/svg", headers=headers)
        assert svg_res.status_code == 200
        assert b"<svg" in svg_res.content

    # 7. Generate Package
    print("7. Generating PDF Package (Async)...")
    pkg_res = client.post(f"/api/v1/projects/{project_id}/package/generate", json={
        "version": "Rev 1 - Pilot",
        "issued_by": "BuildDesk Pilot Script"
    }, headers=headers)
    assert pkg_res.status_code == 200, pkg_res.text

    # Poll until ready
    import time
    print("   Polling for completion...", end="")
    max_retries = 30
    for _ in range(max_retries):
        status_res = client.get(f"/api/v1/projects/{project_id}/package/status", headers=headers)
        if status_res.json()["status"] == "ready":
            print(" Done!")
            break
        elif status_res.json()["status"] == "generation_failed":
            print(" Failed!")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print(" Timeout!")
        sys.exit(1)

    # 8. Download PDF Artifact
    print("8. Saving PDF Artifact...")
    pdf_res = client.get(f"/api/v1/projects/{project_id}/package/download", headers=headers)
    assert pdf_res.status_code == 200

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    pdf_out_path = os.path.join(out_dir, "pilot_package.pdf")
    with open(pdf_out_path, "wb") as f:
        f.write(pdf_res.content)
    
    # 9. Export operational reports
    print("9. Generating Operational Exports (Phase 10)...")
    
    # Schedule CSV
    res = client.post(f"/api/v1/projects/{project_id}/exports", json={"export_type": "schedule", "format": "csv"}, headers=headers)
    assert res.status_code == 201
    
    # Fabrication XLSX
    res = client.post(f"/api/v1/projects/{project_id}/exports", json={"export_type": "fabrication", "format": "xlsx"}, headers=headers)
    assert res.status_code == 201

    # Summary CSV
    res = client.post(f"/api/v1/projects/{project_id}/exports", json={"export_type": "summary", "format": "csv"}, headers=headers)
    assert res.status_code == 201

    # 10. Revision Workflow
    print("10. Testing Revision Workflow (Phase 11)...")
    
    pkg_res_2 = client.post(f"/api/v1/projects/{project_id}/package/generate", json={
        "version": "Rev A",
        "issued_by": "Pilot Script",
        "revision_notes": "Added ADA units, updated kitchen edge profiles"
    }, headers=headers)
    assert pkg_res_2.status_code == 200
    
    print("   Polling for Rev A completion...", end="", flush=True)
    for _ in range(30):
        status_res = client.get(f"/api/v1/projects/{project_id}/package/status", headers=headers)
        if status_res.json()["status"] == "ready":
            print(" Done!")
            break
        elif status_res.json()["status"] == "generation_failed":
            print(" Failed!")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(1)
        
    list_res = client.get(f"/api/v1/projects/{project_id}/packages", headers=headers)
    assert list_res.status_code == 200
    packages = list_res.json()["packages"]
    assert len(packages) == 2
    print([p["version"] for p in packages])
    assert packages[0]["version"] == "Rev A"
    assert packages[1]["version"] == "Rev 1 - Pilot"

    print(f"✅ Pilot validation workflow completed successfully. PDF saved to {pdf_out_path}.")
    print("✅ Exports generated successfully in background.")
    print("✅ Revision workflow preserved history correctly.")

if __name__ == "__main__":
    run()
