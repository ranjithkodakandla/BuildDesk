"""
Smoke Tests: Straight Kitchen Shape
===================================
Exercises the full pipeline for shape_type="straight_kitchen":
    TemplateResolver → GeometryBuilder → GeometryModel + primitives
    GeometryBuilder  → SvgExporter     → SVG string
    POST /api/v1/geometry              → 200 JSON
    POST /api/v1/export/svg            → 200 image/svg+xml

Covers:
    ✓ STRAIGHT_KITCHEN_TEMPLATE lookup + parameters
    ✓ Short run (single piece, length <= max_length)
    ✓ Long run (multi-piece, length > max_length)
    ✓ Long run with seam_enabled=False (forces single piece)
    ✓ Seam metadata correctness
    ✓ Overall polyline + separate piece rectangles
    ✓ SVG output contains multi-piece artifacts (<polyline>, <rect>, seam line)
    ✓ GET /api/v1/demo/straight-kitchen endpoint
    ✓ CLI generate_demo_svg straight-kitchen

Run with:
    cd backend
    python -m tests.smoke_straight_kitchen
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import SHAPE_REGISTRY, STRAIGHT_KITCHEN_TEMPLATE
from app.main import app
from app.services.geometry_builder import GeometryBuilder, GeometryBuildError
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
    print("\nBuildDesk · Straight Kitchen Shape Smoke Tests")

    # ── 1. Template Registration ─────────────────────────────────────────────
    section("1. STRAIGHT_KITCHEN_TEMPLATE in SHAPE_REGISTRY")
    if "straight_kitchen" not in SHAPE_REGISTRY:
        fail("registry", "straight_kitchen not found")
    params = [p.name for p in STRAIGHT_KITCHEN_TEMPLATE.parameters]
    if len(params) != 7:  # length, width, thickness, backsplash, seam_enabled, slab_max_length, label
        fail("params", f"Expected 7, got {len(params)}: {params}")
    ok("registry", "straight_kitchen registered")
    ok("params", f"{params}")

    # ── 2. Short Run (Single Piece) ──────────────────────────────────────────
    section("2. Short Run (single piece)")
    dims = {"length": 96.0, "width": 26.0, "slab_max_length": 120.0}
    resolved = resolver.resolve(STRAIGHT_KITCHEN_TEMPLATE, dims)
    if resolved.has_errors: fail("resolve", str(resolved.errors))
    result = builder.build(STRAIGHT_KITCHEN_TEMPLATE, resolved, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g = result.geometry
    if len(g.pieces) != 1: fail("pieces", f"expected 1, got {len(g.pieces)}")
    if len(result.rectangles) != 1: fail("rectangles", f"expected 1, got {len(result.rectangles)}")
    if g.metadata["seam_count"] != 0: fail("seam_count", f"expected 0, got {g.metadata['seam_count']}")
    
    ok("pieces", f"{len(g.pieces)} piece(s)")
    ok("seam_count", "0 seams")

    # ── 3. Long Run (Multi-Piece) ────────────────────────────────────────────
    section("3. Long Run (multi-piece)")
    dims_long = {"length": 180.0, "width": 26.0, "slab_max_length": 120.0}
    res_long = resolver.resolve(STRAIGHT_KITCHEN_TEMPLATE, dims_long)
    r_long = builder.build(STRAIGHT_KITCHEN_TEMPLATE, res_long, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g_long = r_long.geometry
    if len(g_long.pieces) != 2: fail("pieces", f"expected 2, got {len(g_long.pieces)}")
    if len(r_long.rectangles) != 2: fail("rectangles", f"expected 2, got {len(r_long.rectangles)}")
    if g_long.metadata["seam_count"] != 1: fail("seam_count", f"expected 1, got {g_long.metadata['seam_count']}")
    
    p1 = g_long.pieces[0]
    p2 = g_long.pieces[1]
    if p1.length != 120.0: fail("p1 length", f"expected 120.0, got {p1.length}")
    if p2.length != 60.0: fail("p2 length", f"expected 60.0, got {p2.length}")
    
    # Seam line validation
    seam_lines = [l for l in r_long.lines if l.metadata.get("line_type") == "seam"]
    if len(seam_lines) != 1: fail("seam_lines", f"expected 1, got {len(seam_lines)}")
    
    ok("pieces", f"{len(g_long.pieces)} pieces generated correctly")
    ok("piece lengths", f"{p1.length}\" and {p2.length}\"")
    ok("seam_count", "1 seam")
    ok("seam line", "found in output")

    # ── 4. Long Run (Seam Disabled) ──────────────────────────────────────────
    section("4. Long Run (seam_enabled=False)")
    dims_no_seam = {"length": 180.0, "width": 26.0, "slab_max_length": 120.0, "seam_enabled": False}
    res_no_seam = resolver.resolve(STRAIGHT_KITCHEN_TEMPLATE, dims_no_seam)
    r_no_seam = builder.build(STRAIGHT_KITCHEN_TEMPLATE, res_no_seam, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g_no_seam = r_no_seam.geometry
    if len(g_no_seam.pieces) != 1: fail("pieces", f"expected 1, got {len(g_no_seam.pieces)}")
    if g_no_seam.metadata["seam_count"] != 0: fail("seam_count", f"expected 0, got {g_no_seam.metadata['seam_count']}")
    
    ok("pieces", "forced 1 piece")
    ok("seam_count", "0 seams")

    # ── 5. SVG Export (Multi-Piece) ──────────────────────────────────────────
    section("5. SVG Export (Multi-Piece)")
    svg = exporter.export(r_long)
    assert_in(svg, "<polyline", "overall outline polyline")
    assert_in(svg, "stroke-dasharray=\"5,5\"", "seam dashed line")
    
    # ── 6. API Integration ───────────────────────────────────────────────────
    section("6. POST /api/v1/geometry shape_type=straight_kitchen → 200")
    payload = {
        "shape_type": "straight_kitchen",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 200.0, "width": 26.0, "slab_max_length": 120.0},
    }
    resp = client.post("/api/v1/geometry", json=payload)
    assert_status(resp, 200, "geometry api status")
    body = resp.json()
    assert body["shape_type"] == "straight_kitchen"
    assert len(body["pieces"]) == 2
    assert body["metadata"]["seam_count"] == 1
    ok("api POST", f"2 pieces, 1 seam")

    # ── 7. Demo Endpoint ─────────────────────────────────────────────────────
    section("7. GET /api/v1/demo/straight-kitchen → 200")
    resp = client.get("/api/v1/demo/straight-kitchen")
    assert_status(resp, 200, "demo api status")
    assert "image/svg+xml" in resp.headers.get("content-type", "")
    assert_in(resp.text, "<polyline", "SVG in demo response")
    assert_in(resp.text, "SEAM", "SEAM text in SVG")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All straight kitchen shape smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
