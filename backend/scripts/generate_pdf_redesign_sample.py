#!/usr/bin/env python3
"""Generate a single-assembly sample PDF for layout comparison."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.exporters.package_pdf_exporter import PackagePdfExporter
from app.models.fabrication import (
    Assembly,
    AssemblyType,
    Cutout,
    CutoutType,
    Dimensions,
    EdgeTreatment,
    EdgeType,
    MountType,
    Part,
    PartType,
    Position,
)
from app.models.hierarchy import Project, ProjectStatus, UnitVariant
from app.models.project_package import PackageSummary, ProjectPackage, UnitTypeGroup
from app.models.tenant import Tenant

ROOT = Path(__file__).resolve().parents[2]


def build_sample_pdf() -> bytes:
    tid = uuid.uuid4()
    pid = uuid.uuid4()
    aid = uuid.uuid4()
    ut = uuid.uuid4()
    part_id = uuid.uuid4()

    def edge(pos: Position, et: EdgeType) -> EdgeTreatment:
        return EdgeTreatment(part_id=part_id, position=pos, edge_type=et)

    parts = [
        Part(
            assembly_id=aid,
            part_type=PartType.MAIN_TOP,
            name="Piece 1 - Top w/ Sink",
            dimensions=Dimensions(length=28.5, depth=30.0, thickness=3.0),
            notes="grain horizontal",
            edges=[
                edge(Position.LEFT, EdgeType.POLISHED),
                edge(Position.FRONT, EdgeType.POLISHED),
                edge(Position.RIGHT, EdgeType.RAW),
                edge(Position.BACK, EdgeType.RAW),
            ],
            cutouts=[
                Cutout(
                    part_id=part_id,
                    cutout_type=CutoutType.SINK,
                    mount_type=MountType.DROP_IN,
                    dimensions=Dimensions(length=17.5, depth=17.5),
                    center_x=14.25,
                    center_y=15.0,
                )
            ],
        )
    ]
    for n, l, d in [
        ("Piece 2 - Wing", 31.0, 9.0),
        ("Piece 3 - Main Top", 40.5, 30.0),
        ("Piece 4 - Splash", 28.5, 4.0),
        ("Piece 5 - Splash", 31.0, 4.0),
        ("Piece 6 - Splash", 40.5, 4.0),
    ]:
        parts.append(
            Part(
                assembly_id=aid,
                part_type=PartType.MAIN_TOP,
                name=n,
                dimensions=Dimensions(length=l, depth=d, thickness=3.0),
                edges=[
                    edge(Position.LEFT, EdgeType.POLISHED),
                    edge(Position.FRONT, EdgeType.RAW),
                    edge(Position.RIGHT, EdgeType.RAW),
                    edge(Position.BACK, EdgeType.POLISHED),
                ],
            )
        )

    asm = Assembly(
        assembly_id=aid,
        project_id=pid,
        tenant_id=tid,
        unit_type_id=ut,
        name="Kitchen A",
        assembly_type=AssemblyType.CUSTOM,
        variant=UnitVariant.STANDARD,
        parts=parts,
    )
    proj = Project(
        project_id=pid,
        tenant_id=tid,
        name="Haven On Main New",
        client_name="Demo Client",
        material="3CM Granite",
        status=ProjectStatus.draft,
    )
    tenant = Tenant(
        tenant_id=tid,
        name="BuildDesk",
        slug="builddesk",
        contact_email="demo@builddesk.app",
        company_name="BuildDesk",
    )
    group = UnitTypeGroup(
        unit_type_id=ut,
        unit_type_code="1A",
        unit_type_name="Kitchen A",
        unit_count=12,
        unit_codes=["101"],
        assembly_types=["custom"],
    )
    pkg = ProjectPackage(
        project_id=pid,
        tenant_id=tid,
        package_id=uuid.uuid4(),
        version="Rev A",
        status="ready",
        generated_at=datetime.now(timezone.utc),
    )
    summary = PackageSummary(
        total_units=12, total_assemblies=1, total_parts=6, total_area_sqft=42.0
    )
    return PackagePdfExporter().export(
        proj, pkg, tenant, [group], {f"{ut}::custom": [asm]}, summary
    )


def main() -> int:
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts/pdf-redesign-after.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build_sample_pdf()
    out.write_bytes(data)
    print(f"Wrote {out} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
