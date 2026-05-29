#!/usr/bin/env python3
"""
Seed a BuildDesk project that mirrors sheet 100-01 from the reference PDF:
  "BULL OUTDOOR" / Boca Grande / Colonial White / QTY 45 / ITEM 16360

Piece dimensions and fabrication semantics taken from the Virgin Surfaces shop drawing.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE_URL = os.getenv(
    "STAGING_API_URL",
    "https://builddesk-api-149130710868.us-central1.run.app",
).rstrip("/")
POLL_TIMEOUT_S = int(os.getenv("REFERENCE_POLL_TIMEOUT_S", "180"))
ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts" / "reference-validation"


def _part(
    name: str,
    length: float,
    depth: float,
    *,
    edges: list | None = None,
    splashes: list | None = None,
    cutouts: list | None = None,
    notes: str | None = None,
) -> dict:
    return {
        "part_type": "main_top",
        "name": name,
        "dimensions": {"length": length, "depth": depth, "thickness": 3.0},
        "edges": edges or [],
        "splashes": splashes or [],
        "cutouts": cutouts or [],
        "holes": [],
        "notes": notes,
    }


def _edge(position: str, edge_type: str, notes: str = "") -> dict:
    return {"position": position, "edge_type": edge_type, "notes": notes}


def bull_outdoor_assembly_payload(project_id: str, unit_type_id: str) -> dict:
    """Six-piece layout matching reference sheet 100-01 with edges, cutouts, and notes."""
    return {
        "project_id": project_id,
        "unit_type_id": unit_type_id,
        "name": "BULL OUTDOOR — Splashes (3 sides Polish)",
        "assembly_type": "custom",
        "variant": "standard",
        "notes": [
            {
                "content": "REF 100-01: X=3mm round polish; splashes 3-side polish; raw bottom on splashes."
            },
            {"content": "REF: Grain horizontal on pieces 1-3; Break corners on splashes 4-6; QTY 45."},
        ],
        "parts": [
            _part(
                "Piece 1 — Top w/ Top Mount Sink",
                28.5,
                30.0,
                edges=[
                    _edge("left", "polished", "3mm round (ref: X)"),
                    _edge("front", "polished", "3mm round"),
                    _edge("right", "raw", "wall"),
                    _edge("back", "raw", "wall"),
                ],
                cutouts=[
                    {
                        "cutout_type": "sink",
                        "mount_type": "drop_in",
                        "dimensions": {"length": 17.5, "depth": 17.5},
                        "center_x": 14.25,
                        "center_y": 15.0,
                        "notes": "Top mount sink; R1/8 corners per reference",
                    }
                ],
                notes="R1/2 outer corners; grain horizontal",
            ),
            _part(
                "Piece 2 — Wing",
                31.0,
                9.0,
                edges=[
                    _edge("left", "polished"),
                    _edge("front", "polished"),
                    _edge("right", "raw"),
                    _edge("back", "raw"),
                ],
                notes="R1/2 bottom-left; grain horizontal",
            ),
            _part(
                "Piece 3 — Main Top",
                40.5,
                30.0,
                edges=[
                    _edge("left", "polished"),
                    _edge("front", "polished"),
                    _edge("right", "polished"),
                    _edge("back", "polished"),
                ],
                notes="Polished all outside edges; R1/2 all corners",
            ),
            _part(
                "Piece 4 — Splash",
                28.5,
                4.0,
                edges=[
                    _edge("left", "polished", "3-side polish"),
                    _edge("back", "polished", "3-side polish"),
                    _edge("right", "polished", "3-side polish"),
                    _edge("front", "raw", "raw bottom"),
                ],
                notes="Break corners",
            ),
            _part(
                "Piece 5 — Splash",
                31.0,
                4.0,
                edges=[
                    _edge("left", "polished"),
                    _edge("back", "polished"),
                    _edge("right", "polished"),
                    _edge("front", "raw"),
                ],
                notes="Break corners",
            ),
            _part(
                "Piece 6 — Splash",
                40.5,
                4.0,
                edges=[
                    _edge("left", "polished"),
                    _edge("back", "polished"),
                    _edge("right", "polished"),
                    _edge("front", "raw"),
                ],
                notes="Break corners",
            ),
        ],
    }


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    tenant_id = str(uuid.uuid4())
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    def headers(token: str | None = None) -> dict:
        h = {"X-Tenant-ID": tenant_id}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    email = f"bull_ref_{uuid.uuid4().hex[:8]}@builddesk.accept"
    pwd = "BullOutdoorRef123!"
    print(f"[1/8] Register tenant {tenant_id[:8]}…")
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "role": "admin"},
        headers=headers(),
    ).raise_for_status()
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
        headers=headers(),
    ).json()["access_token"]
    h = headers(token)

    print("[2/8] Tenant branding (Virgin Surfaces–style metadata)…")
    client.put(
        "/api/v1/tenant/profile",
        json={
            "company_name": "Virgin Surfaces (Reference Validation)",
            "default_footer": "BULL OUTDOOR · ITEM 16360 · 3CM Colonial White · QTY 45",
            "standard_notes": "ALL PARTS MADE TO SIZE UNLESS NOTED. Keep grain same direction.",
        },
        headers=h,
    ).raise_for_status()

    print("[3/8] Create project BULL OUTDOOR / Boca Grande…")
    project = client.post(
        "/api/v1/projects",
        json={
            "name": "BULL OUTDOOR",
            "client_name": "Boca Grande",
            "material": "3CM Colonial White Granite",
            "address": "ITEM # 16360",
            "status": "draft",
            "hierarchy_config": {
                "has_buildings": False,
                "has_floors": False,
                "has_unit_types": True,
            },
        },
        headers=h,
    ).json()
    project_id = project["project_id"]

    print("[4/8] Unit type + qty 45 units…")
    ut = client.post(
        f"/api/v1/projects/{project_id}/unit-types",
        json={"code": "BO-100-01", "name": "Bull Outdoor Sheet 100-01", "sort_order": 1},
        headers=h,
    ).json()
    unit_type_id = ut["unit_type_id"]
    bulk = client.post(
        f"/api/v1/projects/{project_id}/units/bulk",
        json={"start_number": 1, "end_number": 45, "prefix": "", "unit_type_id": unit_type_id},
        headers=h,
    ).json()
    print(f"      Created {bulk.get('created_count', '?')} units")

    print("[5/8] Create 6-part reference assembly…")
    asm = client.post(
        "/api/v1/assemblies",
        json=bull_outdoor_assembly_payload(project_id, unit_type_id),
        headers=h,
    )
    asm.raise_for_status()
    assembly_id = asm.json()["assembly_id"]
    print(f"      assembly_id={assembly_id}")

    print("[6/8] Generate fabrication package (Rev 100-01)…")
    t0 = time.perf_counter()
    client.post(
        f"/api/v1/projects/{project_id}/package/generate",
        json={
            "version": "100-01",
            "revision_notes": "Reference validation — BULL OUTDOOR Splashes 3-side polish",
        },
        headers=h,
    ).raise_for_status()

    status_body = None
    for _ in range(POLL_TIMEOUT_S):
        st = client.get(f"/api/v1/projects/{project_id}/package/status", headers=h)
        status_body = st.json()
        if status_body["status"] == "ready":
            break
        if status_body["status"] == "generation_failed":
            raise RuntimeError(status_body.get("generation_error", "generation_failed"))
        time.sleep(1)
    else:
        raise TimeoutError("package generation timeout")

    gen_s = time.perf_counter() - t0
    package_id = status_body["package_id"]
    storage_ref = status_body.get("storage_reference", "")

    print(f"[7/8] Download PDF ({gen_s:.1f}s)…")
    pdf = client.get(f"/api/v1/projects/{project_id}/package/pdf", headers=h)
    pdf.raise_for_status()
    pdf_path = ARTIFACTS / "builddesk_bull_outdoor_100-01.pdf"
    pdf_path.write_bytes(pdf.content)
    if pdf.content[:4] != b"%PDF":
        raise RuntimeError("downloaded file is not a PDF")

    manifest = {
        "reference_sheet": "100-01",
        "reference_title": "BULL OUTDOOR Splashes (3 sides Polish) — Colonial White",
        "tenant_id": tenant_id,
        "email": email,
        "password": pwd,
        "project_id": project_id,
        "unit_type_id": unit_type_id,
        "assembly_id": assembly_id,
        "package_id": package_id,
        "storage_reference": storage_ref,
        "generation_seconds": round(gen_s, 2),
        "pdf_bytes": len(pdf.content),
        "pdf_path": str(pdf_path),
        "frontend_workspace_url": f"https://builddesk-web-149130710868.us-central1.run.app/projects/{project_id}",
        "api_base": BASE_URL,
    }
    manifest_path = ARTIFACTS / "reference_seed_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[8/8] Wrote {pdf_path} ({len(pdf.content)} bytes)")
    print(f"      Manifest: {manifest_path}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
