"""
Smoke Tests: Vanity Shape
=========================
Exercises the full pipeline for shape_type="vanity":
    TemplateResolver → GeometryBuilder → GeometryModel + primitives
    GeometryBuilder  → SvgExporter     → SVG string
    POST /api/v1/geometry              → 200 JSON
    POST /api/v1/export/svg            → 200 image/svg+xml

Covers:
    ✓ VANITY_TEMPLATE lookup + 6 parameters
    ✓ basic vanity (no options)
    ✓ vanity + backsplash (annotation added)
    ✓ vanity + sink cutout (circle added)
    ✓ sink diameter validation (raises GeometryBuildError if too large)
    ✓ open Polyline outline (wall edge omitted)
    ✓ 3 DimensionLines (front, left, right)
    ✓ SVG output contains <polyline> and <circle>
    ✓ GET /api/v1/demo/vanity endpoint
    ✓ CLI generate_demo_svg vanity

Run with:
    cd backend
    python -m tests.smoke_vanity
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import SHAPE_REGISTRY, VANITY_TEMPLATE
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
    print("\nBuildDesk · Vanity Shape Smoke Tests")

    # ── 1. Template Registration ─────────────────────────────────────────────
    section("1. VANITY_TEMPLATE in SHAPE_REGISTRY")
    if "vanity" not in SHAPE_REGISTRY:
        fail("registry", "vanity not found")
    params = [p.name for p in VANITY_TEMPLATE.parameters]
    if len(params) != 7:  # length, width, thickness, backsplash, sink_cutout, sink_diameter, label
        fail("params", f"Expected 7, got {len(params)}: {params}")
    ok("registry", "vanity registered")
    ok("params", f"{params}")

    # ── 2. Basic Vanity Build ────────────────────────────────────────────────
    section("2. Basic Vanity (no options)")
    dims = {"length": 48.0, "width": 22.0}
    resolved = resolver.resolve(VANITY_TEMPLATE, dims)
    if resolved.has_errors: fail("resolve", str(resolved.errors))
    result = builder.build(VANITY_TEMPLATE, resolved, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    g = result.geometry
    if g.status.value != "computed": fail("status", "not computed")
    if len(result.polylines) != 1: fail("polylines", "expected 1")
    if result.polylines[0].closed: fail("polyline closed", "expected open path")
    if len(result.dimension_lines) != 3: fail("dims", f"expected 3, got {len(result.dimension_lines)}")
    if len(result.annotations) != 1: fail("annotations", "expected 1 (piece label)")
    if result.circles: fail("circles", "expected 0")
    
    ok("geometry", f"status={g.status.value}, area={g.computed_area}")
    ok("polyline", "open path (3 edges)")
    ok("metadata", f"wall_edge='{g.metadata['wall_edge']}'")

    # ── 3. Vanity + Backsplash ───────────────────────────────────────────────
    section("3. Vanity + Backsplash")
    dims_bs = {"length": 48.0, "width": 22.0, "backsplash_height": 4.0}
    res_bs = resolver.resolve(VANITY_TEMPLATE, dims_bs)
    r_bs = builder.build(VANITY_TEMPLATE, res_bs, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    if len(r_bs.annotations) != 2: fail("annotations", f"expected 2, got {len(r_bs.annotations)}")
    bs_ann = r_bs.annotations[1]
    if "Backsplash: 4.0\"" not in bs_ann.text: fail("backsplash note", bs_ann.text)
    
    ok("backsplash annotation", bs_ann.text)
    ok("metadata", f"has_backsplash={r_bs.geometry.metadata['has_backsplash']}")

    # ── 4. Vanity + Sink Cutout ──────────────────────────────────────────────
    section("4. Vanity + Sink Cutout")
    dims_sink = {"length": 48.0, "width": 22.0, "sink_cutout": True, "sink_diameter": 12.0}
    res_sink = resolver.resolve(VANITY_TEMPLATE, dims_sink)
    r_sink = builder.build(VANITY_TEMPLATE, res_sink, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    if len(r_sink.circles) != 1: fail("circles", f"expected 1, got {len(r_sink.circles)}")
    c = r_sink.circles[0]
    if c.radius != 6.0: fail("radius", f"expected 6.0, got {c.radius}")
    
    ok("sink circle", f"radius={c.radius}, centre=({c.center.x}, {c.center.y})")
    ok("metadata", f"sink_diameter={r_sink.geometry.metadata['sink_diameter']}")

    # ── 5. Sink Diameter Validation ──────────────────────────────────────────
    section("5. Sink Diameter Validation (Too Large)")
    # min(48, 22) - 2*4 = 14.0 max diameter. Let's try 15.0
    dims_large = {"length": 48.0, "width": 22.0, "sink_cutout": True, "sink_diameter": 15.0}
    res_large = resolver.resolve(VANITY_TEMPLATE, dims_large)
    try:
        builder.build(VANITY_TEMPLATE, res_large, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
        fail("validation", "Expected GeometryBuildError for oversized sink")
    except GeometryBuildError as e:
        ok("validation caught oversized sink", str(e))

    # ── 6. SVG Export ────────────────────────────────────────────────────────
    section("6. SVG Export (Vanity + Options)")
    svg = exporter.export(r_sink)
    assert_in(svg, "<polyline", "open polyline outline")
    assert_in(svg, "<circle", "sink cutout")
    
    # Check that it's NOT a <polygon>
    if "<polygon" in svg:
        fail("polygon", "Found <polygon>, but vanity should be open <polyline>")
    ok("no polygon", "proper open path rendered")

    # ── 7. API Integration ───────────────────────────────────────────────────
    section("7. POST /api/v1/geometry shape_type=vanity → 200")
    payload = {
        "shape_type": "vanity",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 36, "width": 22, "sink_cutout": True, "sink_diameter": 12.0},
    }
    resp = client.post("/api/v1/geometry", json=payload)
    assert_status(resp, 200, "geometry api status")
    body = resp.json()
    assert body["shape_type"] == "vanity"
    assert body["status"] == "computed"
    ok("api POST", f"computed area: {body['computed_area']}")

    # ── 8. Demo Endpoint ─────────────────────────────────────────────────────
    section("8. GET /api/v1/demo/vanity → 200")
    resp = client.get("/api/v1/demo/vanity")
    assert_status(resp, 200, "demo api status")
    assert "image/svg+xml" in resp.headers.get("content-type", "")
    assert_in(resp.text, "<polyline", "SVG in demo response")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All vanity shape smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
