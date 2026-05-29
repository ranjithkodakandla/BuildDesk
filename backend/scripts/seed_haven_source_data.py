#!/usr/bin/env python3
"""
Seed BuildDesk from StoneDesk SourceData_export Excel (Haven On Main New).

Reads Parts List + Project Info, creates unit types (one per Unit+Drawing kit),
assemblies with real dimensions/edges/sinks, and generates a fabrication PDF.

Usage:
  python scripts/seed_haven_source_data.py \\
    --xlsx "/path/to/SourceData_export (29).xlsx"
"""
from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path

import httpx
import pandas as pd

BASE_URL = __import__("os").environ.get(
    "STAGING_API_URL",
    "https://builddesk-api-149130710868.us-central1.run.app",
).rstrip("/")
POLL_TIMEOUT_S = int(__import__("os").environ.get("REFERENCE_POLL_TIMEOUT_S", "300"))
ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "source-data-haven"
DEFAULT_XLSX = Path("/Users/ranjithkodakandla/Downloads/SourceData_export (29).xlsx")

_EDGE_SIDE_MAP = {
    "T": "back",
    "B": "front",
    "L": "left",
    "R": "right",
}


def _parse_edges(edge_per_side: str | None) -> list[dict]:
    if not edge_per_side or not isinstance(edge_per_side, str):
        return []
    edges = []
    for chunk in edge_per_side.split(","):
        chunk = chunk.strip()
        if ":" not in chunk:
            continue
        side, finish = chunk.split(":", 1)
        side = side.strip().upper()
        finish = finish.strip().lower()
        pos = _EDGE_SIDE_MAP.get(side)
        if not pos:
            continue
        if finish in ("none", "raw", ""):
            etype = "raw"
        elif "polish" in finish:
            etype = "polished"
        elif "ease" in finish:
            etype = "eased"
        else:
            etype = "finished"
        edges.append({"position": pos, "edge_type": etype, "notes": finish})
    return edges


def _part_type_from_name(name: str) -> str:
    n = (name or "").lower()
    if "splash" in n or "apron" in n:
        return "loose_piece"
    if "island" in n:
        return "island_top"
    return "main_top"


def _assembly_type_from_part_type(part_type_name: str) -> str:
    n = (part_type_name or "").lower()
    if "vanity" in n:
        return "vanity"
    if "kitchen" in n or "range" in n or "island" in n or "perimeter" in n:
        return "kitchen"
    return "custom"


def _read_project_info(xlsx: Path) -> dict:
    info = pd.read_excel(xlsx, sheet_name="Project Info", header=None)
    meta: dict[str, str] = {}
    for i in range(len(info) - 1):
        label = info.iloc[i, 1]
        if pd.isna(label):
            continue
        label = str(label).strip()
        val = info.iloc[i + 1, 1]
        if pd.notna(val):
            meta[label] = str(val).strip()
    return meta


def _load_parts(xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name="Parts List")
    df = df.dropna(subset=["Part #", "Length (in)", "Width (in)"], how="any")
    return df


def _build_part_row(row: pd.Series, piece_idx: int) -> dict:
    length = float(row["Length (in)"])
    depth = float(row["Width (in)"])
    notes_parts = []
    if pd.notna(row.get("Notes")):
        notes_parts.append(str(row["Notes"]))
    if pd.notna(row.get("Radius (in)")):
        notes_parts.append(f"R{row['Radius (in)']}")
    if pd.notna(row.get("Orientation")) and str(row["Orientation"]).lower() != "auto":
        notes_parts.append(f"grain {str(row['Orientation']).lower()}")
    if pd.notna(row.get("Edge Manual Note")):
        notes_parts.append(str(row["Edge Manual Note"]))

    part: dict = {
        "part_type": _part_type_from_name(str(row.get("Part Type", ""))),
        "name": f"Piece {piece_idx} — {row['Part #']}",
        "dimensions": {"length": length, "depth": depth, "thickness": 3.0},
        "edges": _parse_edges(row.get("Edge Per-Side")),
        "splashes": [],
        "cutouts": [],
        "holes": [],
        "notes": "; ".join(notes_parts) if notes_parts else None,
    }

    sink_n = row.get("Sink Cutouts")
    try:
        sink_n = int(sink_n) if pd.notna(sink_n) else 0
    except (TypeError, ValueError):
        sink_n = 0
    if sink_n > 0:
        co_len = min(24.0, length * 0.55)
        co_dep = min(24.0, depth * 0.55)
        mount = "drop_in"
        st = str(row.get("Sink Type", "")).lower()
        if "under" in st:
            mount = "undermount"
        part["cutouts"].append(
            {
                "cutout_type": "sink",
                "mount_type": mount,
                "dimensions": {"length": co_len, "depth": co_dep},
                "center_x": length / 2,
                "center_y": depth / 2,
                "notes": str(row.get("Sink Type", "Sink")),
            }
        )
        if "ada" in st:
            part["notes"] = (part["notes"] or "") + "; Top mount Sink ADA"

    tap = row.get("Tap Holes")
    try:
        tap = int(tap) if pd.notna(tap) else 0
    except (TypeError, ValueError):
        tap = 0
    for t in range(min(tap, 3)):
        part["holes"].append(
            {
                "diameter": 1.375,
                "center_x": length * (0.35 + t * 0.15),
                "center_y": depth * 0.85,
                "purpose": "faucet",
            }
        )

    return part


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    args = parser.parse_args()
    xlsx = args.xlsx.expanduser().resolve()
    if not xlsx.exists():
        raise SystemExit(f"Excel not found: {xlsx}")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    meta = _read_project_info(xlsx)
    parts_df = _load_parts(xlsx)
    project_name = meta.get("Project Name", "Haven On Main New")
    material = f"{meta.get('Thickness', '3CM')} {meta.get('Material', 'Granite')}".strip()
    job = meta.get("Job Number", "101")

    print(f"Source: {xlsx.name}")
    print(f"Project: {project_name} | {material} | Job {job}")
    print(f"Parts rows: {len(parts_df)} (deduped per Unit+Drawing+Part#)")

    tenant_id = str(uuid.uuid4())
    client = httpx.Client(base_url=BASE_URL, timeout=180.0)

    def headers(token: str | None = None) -> dict:
        h = {"X-Tenant-ID": tenant_id}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    email = f"haven_{uuid.uuid4().hex[:8]}@builddesk.accept"
    pwd = "HavenSource123!"
    print(f"[1] Register tenant {tenant_id[:8]}…")
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

    print("[2] Create project…")
    project = client.post(
        "/api/v1/projects",
        json={
            "name": project_name,
            "client_name": meta.get("Customer") or "StoneDesk Import",
            "material": material,
            "address": f"Job #{job}",
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

    # One unit type per (Unit, Drawing) so each sheet gets its own PDF page
    deduped = parts_df.drop_duplicates(subset=["Unit", "Drawing", "Part #"], keep="first")
    groups = deduped.groupby(["Unit", "Drawing"], dropna=False)

    unit_type_ids: dict[tuple, str] = {}
    assembly_ids: list[str] = []
    sort_order = 0

    print(f"[3] Create {len(groups)} unit types + assemblies…")
    for (unit_code, drawing), grp in groups:
        sort_order += 1
        unit_code = str(unit_code).strip()
        drawing = str(drawing).strip()
        type_code = re.sub(r"[^A-Za-z0-9]+", "-", f"{unit_code}-{drawing}")[:40].strip("-")
        ut = client.post(
            f"/api/v1/projects/{project_id}/unit-types",
            json={
                "code": type_code,
                "name": f"{unit_code} · Sheet {drawing}",
                "sort_order": sort_order,
            },
            headers=h,
        )
        ut.raise_for_status()
        unit_type_id = ut.json()["unit_type_id"]
        unit_type_ids[(unit_code, drawing)] = unit_type_id

        client.post(
            f"/api/v1/projects/{project_id}/units",
            json={
                "name": f"Unit {unit_code}",
                "code": f"{unit_code}-{drawing}",
                "unit_type_id": unit_type_id,
            },
            headers=h,
        ).raise_for_status()

        part_rows = grp.sort_values("Part #")
        part_payloads = [
            _build_part_row(row, i + 1) for i, (_, row) in enumerate(part_rows.iterrows())
        ]
        primary_type = str(part_rows.iloc[0].get("Part Type", "custom"))
        asm_type = _assembly_type_from_part_type(primary_type)
        if len(part_payloads) >= 4:
            asm_type = "custom"

        asm = client.post(
            "/api/v1/assemblies",
            json={
                "project_id": project_id,
                "unit_type_id": unit_type_id,
                "name": f"{project_name} — {unit_code} — {drawing}",
                "assembly_type": asm_type,
                "variant": "standard",
                "notes": [
                    {
                        "content": f"Imported from SourceData_export · Unit {unit_code} · Drawing {drawing}"
                    }
                ],
                "parts": part_payloads,
            },
            headers=h,
        )
        asm.raise_for_status()
        assembly_ids.append(asm.json()["assembly_id"])

    print(f"      {len(unit_type_ids)} unit types, {len(assembly_ids)} assemblies")

    rev = f"{job}-export"
    print(f"[4] Generate package ({rev})…")
    t0 = time.perf_counter()
    client.post(
        f"/api/v1/projects/{project_id}/package/generate",
        json={"version": rev, "revision_notes": f"SourceData import {xlsx.name}"},
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

    print(f"[5] Download PDF ({gen_s:.1f}s)…")
    pdf = client.get(f"/api/v1/projects/{project_id}/package/pdf", headers=h)
    pdf.raise_for_status()
    pdf_path = ARTIFACTS / f"haven_on_main_{job}.pdf"
    pdf_path.write_bytes(pdf.content)

    manifest = {
        "source_xlsx": str(xlsx),
        "project_name": project_name,
        "material": material,
        "job_number": job,
        "tenant_id": tenant_id,
        "email": email,
        "password": pwd,
        "project_id": project_id,
        "unit_type_count": len(unit_type_ids),
        "assembly_count": len(assembly_ids),
        "part_rows_imported": int(parts_df["Part #"].nunique()),
        "package_id": package_id,
        "generation_seconds": round(gen_s, 2),
        "pdf_bytes": len(pdf.content),
        "pdf_path": str(pdf_path),
        "frontend_workspace_url": f"https://builddesk-web-149130710868.us-central1.run.app/projects/{project_id}",
        "api_base": BASE_URL,
    }
    manifest_path = ARTIFACTS / "haven_seed_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[6] Wrote {pdf_path} ({len(pdf.content):,} bytes)")
    print(f"      Manifest: {manifest_path}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
