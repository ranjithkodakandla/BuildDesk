#!/usr/bin/env python3
"""
Phase 16 — Realistic load validation against live or local API.

Creates higher assembly density (multiple types × assembly kinds × parts),
bulk unit schedule, then measures package generation latency and PDF size.

Usage:
  STAGING_API_URL=https://builddesk-api-....run.app python scripts/run_load_validation.py
  LOAD_UNIT_COUNT=200 LOAD_ASSEMBLY_TYPES=4 python scripts/run_load_validation.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List

import httpx

BASE_URL = os.getenv(
    "STAGING_API_URL",
    os.getenv("LOAD_API_URL", "https://builddesk-api-149130710868.us-central1.run.app"),
).rstrip("/")
UNIT_COUNT = int(os.getenv("LOAD_UNIT_COUNT", "200"))
ASSEMBLY_TYPES = int(os.getenv("LOAD_ASSEMBLY_TYPES", "4"))
PARTS_PER_ASSEMBLY = int(os.getenv("LOAD_PARTS_PER_ASSEMBLY", "6"))
POLL_TIMEOUT_S = int(os.getenv("LOAD_POLL_TIMEOUT_S", "600"))


def _part(name: str, length: float) -> Dict[str, Any]:
    return {
        "part_type": "main_top",
        "name": name,
        "dimensions": {"length": length, "depth": 25.5, "thickness": 1.25},
    }


def main() -> int:
    tenant_id = str(uuid.uuid4())
    email = f"load_{uuid.uuid4().hex[:8]}@example.com"
    password = "LoadTestPass123!"
    client = httpx.Client(base_url=BASE_URL, timeout=180.0)
    metrics: Dict[str, Any] = {"base_url": BASE_URL, "unit_count": UNIT_COUNT}

    def headers(token: str | None = None) -> Dict[str, str]:
        h = {"X-Tenant-ID": tenant_id}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    t0 = time.perf_counter()
    health = client.get("/api/v1/health").json()
    metrics["health"] = health

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "admin"},
        headers=headers(),
    )
    reg.raise_for_status()
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=headers(),
    ).json()["access_token"]

    project_id = client.post(
        "/api/v1/projects",
        json={
            "name": "Load Test Tower",
            "client_name": "Phase16 GC",
            "material": "Quartz 3cm",
            "hierarchy_config": {
                "has_buildings": True,
                "has_floors": True,
                "has_unit_types": True,
            },
        },
        headers=headers(token),
    ).json()["project_id"]

    building_id = client.post(
        f"/api/v1/projects/{project_id}/buildings",
        json={"name": "Tower A", "code": "A", "sort_order": 1},
        headers=headers(token),
    ).json()["building_id"]
    floor_id = client.post(
        f"/api/v1/projects/{project_id}/floors",
        json={"building_id": building_id, "name": "Level 3", "number": 3, "sort_order": 1},
        headers=headers(token),
    ).json()["floor_id"]

    unit_type_ids: List[str] = []
    for i in range(max(2, ASSEMBLY_TYPES // 2)):
        ut = client.post(
            f"/api/v1/projects/{project_id}/unit-types",
            json={"code": f"T{i+1}", "name": f"Type T{i+1}", "is_mirror": i % 2 == 1},
            headers=headers(token),
        ).json()["unit_type_id"]
        unit_type_ids.append(ut)

    asm_kinds = ["kitchen", "vanity", "island", "laundry"][:ASSEMBLY_TYPES]
    t_asm = time.perf_counter()
    for ut_id in unit_type_ids:
        for kind in asm_kinds:
            parts = [_part(f"Part {j+1}", 72 + j * 12) for j in range(PARTS_PER_ASSEMBLY)]
            client.post(
                "/api/v1/assemblies",
                json={
                    "project_id": project_id,
                    "unit_type_id": ut_id,
                    "name": f"{kind.title()} {ut_id[:8]}",
                    "assembly_type": kind,
                    "parts": parts,
                },
                headers=headers(token),
            ).raise_for_status()
    metrics["assembly_setup_s"] = round(time.perf_counter() - t_asm, 2)
    metrics["assemblies_created"] = len(unit_type_ids) * len(asm_kinds)

    t_units = time.perf_counter()
    bulk = client.post(
        f"/api/v1/projects/{project_id}/units/bulk",
        json={
            "start_number": 1,
            "end_number": UNIT_COUNT,
            "prefix": "20",
            "increment": 1,
            "building_id": building_id,
            "floor_id": floor_id,
            "unit_type_id": unit_type_ids[0],
            "variant": "standard",
        },
        headers=headers(token),
    ).json()
    metrics["bulk_units_s"] = round(time.perf_counter() - t_units, 2)
    metrics["units_created"] = bulk.get("created_count", UNIT_COUNT)

    t_gen = time.perf_counter()
    client.post(
        f"/api/v1/projects/{project_id}/package/generate",
        json={"version": "Load-1", "issued_by": "load-script"},
        headers=headers(token),
    ).raise_for_status()

    status_body = None
    for _ in range(POLL_TIMEOUT_S):
        status_body = client.get(
            f"/api/v1/projects/{project_id}/package/status",
            headers=headers(token),
        ).json()
        if status_body["status"] == "ready":
            break
        if status_body["status"] == "generation_failed":
            print("GENERATION FAILED:", status_body.get("generation_error"))
            return 1
        time.sleep(1)
    else:
        print("Poll timeout")
        return 1

    metrics["package_poll_s"] = round(time.perf_counter() - t_gen, 2)
    metrics["generation_attempts"] = status_body.get("generation_attempts")
    metrics["storage_reference"] = status_body.get("storage_reference")
    metrics["page_count"] = status_body.get("page_count")

    t_pdf = time.perf_counter()
    pdf = client.get(
        f"/api/v1/projects/{project_id}/package/pdf",
        headers=headers(token),
    )
    pdf.raise_for_status()
    metrics["pdf_download_s"] = round(time.perf_counter() - t_pdf, 2)
    metrics["pdf_bytes"] = len(pdf.content)
    metrics["total_s"] = round(time.perf_counter() - t0, 2)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "load_validation_report.json")
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
