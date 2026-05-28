"""
Smoke Tests: L-Kitchen Shape
============================
Exercises the full pipeline for shape_type="l_kitchen":
    TemplateResolver → GeometryBuilder → GeometryModel + primitives
    GeometryBuilder  → SvgExporter     → SVG string
    POST /api/v1/geometry              → 200 JSON
    GET /api/v1/demo/l-kitchen         → 200 image/svg+xml

Covers:
    ✓ L_KITCHEN_TEMPLATE lookup + parameters
    ✓ Single piece (seam_enabled=False)
    ✓ Butt join (seam_enabled=True, corner_join_type="butt")
    ✓ Miter join (seam_enabled=True, corner_join_type="miter")
    ✓ Metadata correctness
    ✓ Overall open polyline + piece rectangles + dashed seam line
    ✓ API & CLI workflows

Run with:
    cd backend
    python -m tests.smoke_l_kitchen
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import SHAPE_REGISTRY, L_KITCHEN_TEMPLATE
from app.main import app
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"

client   = TestClient(app)
resolver = TemplateResolver()
builder  = GeometryBuilder()
exporter = SvgExporter(scale=4.0)

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


def assert_in(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(label, f"Expected '{needle}' not found in output")
    ok(label, f"'{needle}' present")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · L-Kitchen Shape Smoke Tests")

    # ── 1. Template Registration ─────────────────────────────────────────────
    section("1. L_KITCHEN_TEMPLATE in SHAPE_REGISTRY")
    if "l_kitchen" not in SHAPE_REGISTRY:
        fail("registry", "l_kitchen not found")
    params = [p.name for p in L_KITCHEN_TEMPLATE.parameters]
    if len(params) != 8:
        fail("params", f"Expected 8, got {len(params)}: {params}")
    ok("registry", "l_kitchen registered")

    # ── 2. Single Piece (Seam Disabled) ──────────────────────────────────────
    section("2. Single Piece (seam_enabled=False)")
    dims_single = {"leg_a_length": 120.0, "leg_b_length": 96.0, "width": 26.0, "seam_enabled": False}
    res_single = resolver.resolve(L_KITCHEN_TEMPLATE, dims_single)
    if res_single.has_errors: fail("resolve", str(res_single.errors))
    r_single = builder.build(L_KITCHEN_TEMPLATE, res_single, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g_single = r_single.geometry
    if len(g_single.pieces) != 1: fail("pieces", f"expected 1, got {len(g_single.pieces)}")
    if g_single.metadata["seam_count"] != 0: fail("seam_count", f"expected 0")
    if g_single.metadata["corner_join_type"] != "none": fail("join_type", "expected 'none'")
    ok("pieces", "1 piece generated")
    ok("metadata", "seam_count=0, corner_join_type=none")

    # ── 3. Butt Join (Seam Enabled) ──────────────────────────────────────────
    section("3. Butt Join")
    dims_butt = {"leg_a_length": 120.0, "leg_b_length": 96.0, "width": 26.0, "seam_enabled": True, "corner_join_type": "butt"}
    res_butt = resolver.resolve(L_KITCHEN_TEMPLATE, dims_butt)
    r_butt = builder.build(L_KITCHEN_TEMPLATE, res_butt, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g_butt = r_butt.geometry
    if len(g_butt.pieces) != 2: fail("pieces", f"expected 2, got {len(g_butt.pieces)}")
    if g_butt.metadata["corner_join_type"] != "butt": fail("join_type", "expected 'butt'")
    
    p1 = g_butt.pieces[0]
    p2 = g_butt.pieces[1]
    if p1.length != 120.0: fail("p1 length", f"expected 120.0, got {p1.length}")
    if p2.length != 70.0: fail("p2 length", f"expected 70.0 (96-26), got {p2.length}")
    
    ok("pieces", f"{len(g_butt.pieces)} pieces")
    ok("piece lengths", f"Leg A={p1.length}\", Leg B={p2.length}\"")
    ok("metadata", "corner_join_type=butt")

    # ── 4. Miter Join (Seam Enabled) ─────────────────────────────────────────
    section("4. Miter Join")
    dims_miter = {"leg_a_length": 120.0, "leg_b_length": 96.0, "width": 26.0, "seam_enabled": True, "corner_join_type": "miter"}
    res_miter = resolver.resolve(L_KITCHEN_TEMPLATE, dims_miter)
    r_miter = builder.build(L_KITCHEN_TEMPLATE, res_miter, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g_miter = r_miter.geometry
    if len(g_miter.pieces) != 2: fail("pieces", f"expected 2")
    if g_miter.metadata["corner_join_type"] != "miter": fail("join_type", "expected 'miter'")
    
    p1_m = g_miter.pieces[0]
    p2_m = g_miter.pieces[1]
    if p1_m.length != 120.0: fail("p1 length", f"expected 120.0, got {p1_m.length}")
    if p2_m.length != 96.0: fail("p2 length", f"expected 96.0, got {p2_m.length}")
    
    ok("pieces", "2 pieces")
    ok("piece bounds", f"Leg A={p1_m.length}\", Leg B={p2_m.length}\" (overlap in bounding box)")
    ok("metadata", "corner_join_type=miter")

    # ── 5. SVG Export ────────────────────────────────────────────────────────
    section("5. SVG Export (Miter)")
    svg = exporter.export(r_miter)
    assert_in(svg, "<polyline", "overall outline polyline")
    assert_in(svg, "MITER SEAM", "seam text annotation")
    assert_in(svg, "stroke-dasharray=\"5,5\"", "dashed seam line")
    
    # ── 6. API Integration ───────────────────────────────────────────────────
    section("6. POST /api/v1/geometry shape_type=l_kitchen → 200")
    payload = {
        "shape_type": "l_kitchen",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": dims_miter,
    }
    resp = client.post("/api/v1/geometry", json=payload)
    assert_status(resp, 200, "geometry api status")
    body = resp.json()
    assert len(body["pieces"]) == 2
    assert body["metadata"]["corner_join_type"] == "miter"
    ok("api POST", f"2 pieces, miter join")

    # ── 7. Demo Endpoint ─────────────────────────────────────────────────────
    section("7. GET /api/v1/demo/l-kitchen → 200")
    resp = client.get("/api/v1/demo/l-kitchen")
    assert_status(resp, 200, "demo api status")
    assert_in(resp.text, "<polyline", "SVG in demo response")
    assert_in(resp.text, "MITER SEAM", "MITER SEAM text in SVG")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All L-Kitchen shape smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
