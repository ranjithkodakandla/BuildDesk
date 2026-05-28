"""
Smoke Tests: Island Shape
=========================
Exercises the full pipeline for shape_type="island":
    TemplateResolver → GeometryBuilder → GeometryModel + primitives
    GeometryBuilder  → SvgExporter     → SVG string
    POST /api/v1/geometry              → 200 JSON
    POST /api/v1/export/svg            → 200 image/svg+xml

Covers:
    ✓ SHAPE_REGISTRY["island"] lookup
    ✓ ISLAND_TEMPLATE has 5 parameters
    ✓ island geometry build — valid payload → computed
    ✓ island area and perimeter correct
    ✓ 1 GeometryPiece with correct dimensions
    ✓ corner_radius stored in geometry metadata
    ✓ closed Polyline outline produced
    ✓ 4 DimensionLines (all four sides)
    ✓ TextAnnotation at centre
    ✓ island SVG exported — polygon present
    ✓ island SVG — dimension lines rendered
    ✓ POST /api/v1/geometry shape_type=island → 200
    ✓ POST /api/v1/export/svg shape_type=island → 200 SVG
    ✗ island missing required parameter → 422
    ✗ island below min_value → 422

Run with:
    cd backend
    python -m tests.smoke_island
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import ISLAND_TEMPLATE, SHAPE_REGISTRY
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

VALID_PAYLOAD = {"length": 72, "width": 36, "corner_radius": 2.0}


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


def assert_in(svg: str, needle: str, label: str) -> None:
    if needle not in svg:
        fail(label, f"Expected '{needle}' not in output")
    ok(label, f"'{needle}' present")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · Island Shape Smoke Tests")

    # ── 1. SHAPE_REGISTRY lookup ─────────────────────────────────────────────
    section("1. SHAPE_REGISTRY['island'] present")
    if "island" not in SHAPE_REGISTRY:
        fail("registry", "island not in SHAPE_REGISTRY")
    ok("registry", f"keys={list(SHAPE_REGISTRY.keys())}")

    # ── 2. ISLAND_TEMPLATE parameters ───────────────────────────────────────
    section("2. ISLAND_TEMPLATE has 5 parameters")
    params = [p.name for p in ISLAND_TEMPLATE.parameters]
    if len(params) != 5:
        fail("param count", f"Expected 5, got {len(params)}: {params}")
    for expected in ["length", "width", "thickness", "corner_radius", "label"]:
        if expected not in params:
            fail("param names", f"Missing '{expected}' in {params}")
    ok("params", f"{params}")

    # ── 3. Build valid island geometry ────────────────────────────────────────
    section("3. Valid island payload → GeometryModel computed")
    resolved = resolver.resolve(ISLAND_TEMPLATE, VALID_PAYLOAD)
    if resolved.has_errors:
        fail("resolver", str(resolved.errors))
    result = builder.build(
        ISLAND_TEMPLATE, resolved,
        uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID),
    )
    g = result.geometry
    if g.status.value != "computed":
        fail("status", f"Expected computed, got {g.status}")
    ok("status", f"status={g.status.value}")
    ok("template_id", f"matches: {g.template_id == ISLAND_TEMPLATE.template_id}")

    # ── 4. Area and perimeter ────────────────────────────────────────────────
    section("4. Area and perimeter correct")
    expected_area  = 72 * 36
    expected_perim = 2 * (72 + 36)
    if g.computed_area != expected_area:
        fail("area", f"Expected {expected_area}, got {g.computed_area}")
    if g.computed_perimeter != expected_perim:
        fail("perimeter", f"Expected {expected_perim}, got {g.computed_perimeter}")
    ok("area",      f"{g.computed_area} in²")
    ok("perimeter", f"{g.computed_perimeter} in")

    # ── 5. GeometryPiece ─────────────────────────────────────────────────────
    section("5. GeometryPiece dimensions correct")
    if len(g.pieces) != 1:
        fail("piece count", f"Expected 1, got {len(g.pieces)}")
    p = g.pieces[0]
    assert p.length    == 72.0
    assert p.width     == 36.0
    assert p.thickness == 0.75   # default
    assert p.area      == expected_area
    ok("piece", f"label='{p.label}' | {p.length}\" × {p.width}\" × {p.thickness}\" | area={p.area} in²")
    ok("notes", f"'{p.notes[:60]}'")

    # ── 6. Corner radius in geometry metadata ────────────────────────────────
    section("6. corner_radius stored in geometry metadata")
    if g.metadata.get("corner_radius") != 2.0:
        fail("corner_radius", f"Expected 2.0, got {g.metadata.get('corner_radius')}")
    if g.metadata.get("exposed_edges") != ["bottom", "right", "top", "left"]:
        fail("exposed_edges", f"Got {g.metadata.get('exposed_edges')}")
    ok("corner_radius", f"corner_radius={g.metadata['corner_radius']}\"")
    ok("exposed_edges", f"{g.metadata['exposed_edges']}")

    # ── 7. Closed Polyline outline ────────────────────────────────────────────
    section("7. Closed Polyline outline produced")
    if len(result.polylines) != 1:
        fail("polylines", f"Expected 1, got {len(result.polylines)}")
    poly = result.polylines[0]
    if not poly.closed:
        fail("closed", "Polyline must be closed=True for island")
    if len(poly.points) != 4:
        fail("points", f"Expected 4 corner points, got {len(poly.points)}")
    ok("polyline", f"closed={poly.closed} | points={len(poly.points)} | label='{poly.label}'")
    ok("corners", f"BL={poly.points[0]} BR={poly.points[1]} TR={poly.points[2]} TL={poly.points[3]}")

    # ── 8. 4 DimensionLines ──────────────────────────────────────────────────
    section("8. 4 DimensionLines (all four sides)")
    if len(result.dimension_lines) != 4:
        fail("dim count", f"Expected 4, got {len(result.dimension_lines)}")
    texts = [d.display_text for d in result.dimension_lines]
    ok("dim_lines", f"display_texts={texts}")

    # ── 9. TextAnnotation ────────────────────────────────────────────────────
    section("9. TextAnnotation at centre")
    if len(result.annotations) != 1:
        fail("annotations", f"Expected 1, got {len(result.annotations)}")
    ann = result.annotations[0]
    ok("annotation", f"text='{ann.text}' | pos=({ann.position.x}, {ann.position.y})")

    # ── 10. Island SVG — polygon present ─────────────────────────────────────
    section("10. Island SVG export — polygon rendered")
    svg = exporter.export(result)
    assert_in(svg, "<polygon", "polygon element")
    assert_in(svg, 'fill="#f0f4f8"', "fill colour")

    # ── 11. Island SVG — dimension lines rendered ────────────────────────────
    section("11. Island SVG — 4 dimension lines rendered")
    # 4 dim lines × 4 SVG elements each (ext1 + ext2 + main + text) = at least 8 <line>
    line_count = svg.count("<line ")
    if line_count < 8:
        fail("line count", f"Expected ≥8 <line> elements, got {line_count}")
    ok("line count", f"{line_count} <line> elements")

    # ── 12. POST /api/v1/geometry island → 200 ──────────────────────────────
    section("12. POST /api/v1/geometry shape_type=island → 200")
    payload = {
        "shape_type": "island",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 72, "width": 36},
    }
    resp = client.post("/api/v1/geometry", json=payload)
    assert_status(resp, 200, "geometry island 200")
    body = resp.json()
    assert body["status"] == "computed"
    assert body["shape_type"] == "island"
    ok("geometry API", f"status={body['status']} | area={body['computed_area']} in²")

    # ── 13. POST /api/v1/export/svg island → 200 SVG ─────────────────────────
    section("13. POST /api/v1/export/svg shape_type=island → 200 image/svg+xml")
    resp = client.post("/api/v1/export/svg", json=payload)
    assert_status(resp, 200, "export island 200")
    ct = resp.headers.get("content-type", "")
    if "svg" not in ct:
        fail("content-type", f"Expected svg, got '{ct}'")
    svg_body = resp.text
    assert_in(svg_body, "<polygon", "polygon in API SVG")
    ok("content-type", f"content-type={ct}")
    ok("svg length",   f"len={len(svg_body)} chars")

    # ── 14. Missing required parameter → 422 ────────────────────────────────
    section("14. POST /api/v1/geometry (missing width) → 422")
    payload_missing = {
        "shape_type": "island",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 72},
    }
    resp = client.post("/api/v1/geometry", json=payload_missing)
    assert_status(resp, 422, "missing width 422")
    err = resp.json()
    assert err["error"] == "validation_error"
    ok("422 missing width", f"params={[e['parameter'] for e in err['errors']]}")

    # ── 15. Below min_value → 422 ────────────────────────────────────────────
    section("15. POST /api/v1/geometry (length=5, below min=12) → 422")
    payload_range = {
        "shape_type": "island",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 5, "width": 36},
    }
    resp = client.post("/api/v1/geometry", json=payload_range)
    assert_status(resp, 422, "below min 422")
    ok("422 below min", f"msg='{resp.json()['errors'][0]['message'][:60]}'")

    # ── Save sample SVG ───────────────────────────────────────────────────────
    section("Bonus: save island SVG to disk")
    out_dir  = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_island.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    ok("saved SVG", f"→ {out_path}")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All island shape smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
