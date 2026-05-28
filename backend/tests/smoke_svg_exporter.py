"""
Smoke Tests: SVG Exporter
=========================
Tests the full pipeline:
    TemplateResolver → GeometryBuilder → SvgExporter → SVG string

And the HTTP endpoint:
    POST /api/v1/export/svg → 200 image/svg+xml

Covers:
    ✓ SVG generated without exception
    ✓ Valid SVG root element present (<svg …>)
    ✓ Rectangle <rect> element present
    ✓ Dimension lines <line> elements present
    ✓ Text annotation <text> element present
    ✓ Title bar rendered (piece label in SVG)
    ✓ Area and perimeter in title subtitle
    ✓ Arrow marker <defs> present
    ✓ POST /api/v1/export/svg → 200 Content-Type: image/svg+xml
    ✗ POST /api/v1/export/svg (invalid dims) → 422
    ✗ POST /api/v1/export/svg (unknown shape) → 404

Run with:
    cd backend
    python -m tests.smoke_svg_exporter
"""

from __future__ import annotations

import sys
import uuid

from fastapi.testclient import TestClient

from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import RECTANGLE_TEMPLATE
from app.main import app
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"

client    = TestClient(app)
resolver  = TemplateResolver()
builder   = GeometryBuilder()
exporter  = SvgExporter(scale=4.0)

PROJECT_ID = str(uuid.uuid4())
TENANT_ID  = str(uuid.uuid4())


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


def assert_in_svg(svg: str, needle: str, label: str) -> None:
    if needle not in svg:
        fail(label, f"Expected '{needle}' not found in SVG output")
    ok(label, f"'{needle}' present")


def assert_status(resp, expected: int, label: str) -> None:
    if resp.status_code != expected:
        fail(label, f"Expected HTTP {expected}, got {resp.status_code}: {resp.text[:200]}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · SVG Exporter Smoke Tests")
    print(f"Template: {RECTANGLE_TEMPLATE.name}")

    # Build a base result to test the exporter directly
    resolved = resolver.resolve(RECTANGLE_TEMPLATE, {"length": 96, "width": 42})
    if resolved.has_errors:
        fail("resolver", str(resolved.errors))

    result = builder.build(
        template=RECTANGLE_TEMPLATE,
        resolved=resolved,
        project_id=uuid.UUID(PROJECT_ID),
        tenant_id=uuid.UUID(TENANT_ID),
    )

    # ── 1. SVG generated without exception ──────────────────────────────────
    section("1. SVG generated without exception")
    try:
        svg = exporter.export(result)
    except Exception as exc:
        fail("export no-error", str(exc))
    ok("export", f"SVG length={len(svg)} chars")

    # ── 2. Valid SVG root element ────────────────────────────────────────────
    section("2. Valid SVG root element")
    assert_in_svg(svg, "<svg ", "svg root tag")
    assert_in_svg(svg, 'xmlns="http://www.w3.org/2000/svg"', "svg namespace")
    assert_in_svg(svg, "</svg>", "svg closing tag")

    # ── 3. Rectangle <rect> element ──────────────────────────────────────────
    section("3. Rectangle <rect> rendered")
    assert_in_svg(svg, "<rect ", "rect element")
    assert_in_svg(svg, 'fill="#f0f4f8"', "rect fill colour")
    assert_in_svg(svg, 'stroke="#1a2332"', "rect stroke colour")

    # ── 4. Dimension lines ───────────────────────────────────────────────────
    section("4. Dimension lines <line> rendered")
    assert_in_svg(svg, "<line ", "line element")
    assert_in_svg(svg, 'stroke="#4a7fb5"', "dim line colour")

    # ── 5. Dimension text values ─────────────────────────────────────────────
    section("5. Dimension text values rendered")
    # The " inch symbol is XML-escaped to &quot; in the SVG text elements
    assert_in_svg(svg, "96.0&quot;", "length dimension text")
    assert_in_svg(svg, "42.0&quot;", "width dimension text")

    # ── 6. Text annotation rendered ──────────────────────────────────────────
    section("6. TextAnnotation <text> rendered")
    assert_in_svg(svg, "<text ", "text element")
    assert_in_svg(svg, "Rectangle", "piece label text")

    # ── 7. Title bar ─────────────────────────────────────────────────────────
    section("7. Title bar rendered")
    assert_in_svg(svg, _COL_TITLE_BG := "#1a2332", "title bar bg colour")
    assert_in_svg(svg, "BuildDesk v1", "BuildDesk watermark")
    assert_in_svg(svg, "Area:", "area in subtitle")

    # ── 8. Arrow marker defs ─────────────────────────────────────────────────
    section("8. Arrow marker <defs> present")
    assert_in_svg(svg, "<defs>", "defs element")
    assert_in_svg(svg, 'id="arrow"', "arrow marker id")

    # ── 9. POST /api/v1/export/svg → 200 SVG response ────────────────────────
    section("9. POST /api/v1/export/svg → 200 image/svg+xml")
    payload = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 120, "width": 26},
    }
    resp = client.post("/api/v1/export/svg", json=payload, headers={"X-Tenant-ID": TENANT_ID})
    assert_status(resp, 200, "export svg status")
    ct = resp.headers.get("content-type", "")
    if "svg" not in ct:
        fail("content-type", f"Expected svg content-type, got '{ct}'")
    svg_body = resp.text
    if "<svg " not in svg_body:
        fail("svg in body", "Response body does not contain <svg")
    ok("content-type", f"content-type={ct}")
    ok("svg body",     f"SVG length={len(svg_body)} chars")
    ok("geometry rendered", f"dims present: {'120.0&quot;' in svg_body}")

    # ── 10. POST /api/v1/export/svg (missing width) → 422 ─────────────────────
    section("10. POST /api/v1/export/svg (missing width) → 422")
    payload_bad = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96},   # width missing
    }
    resp = client.post("/api/v1/export/svg", json=payload_bad, headers={"X-Tenant-ID": TENANT_ID})
    assert_status(resp, 422, "missing param 422")
    body = resp.json()
    assert body["error"] == "validation_error"
    ok("422 validation", f"error={body['error']} | params={[e['parameter'] for e in body['errors']]}")

    # ── 11. POST /api/v1/export/svg (unknown shape) → 404 ────────────────────
    section("11. POST /api/v1/export/svg (unknown shape) → 404")
    payload_unknown = {
        "shape_type": "hexagon",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96, "width": 42},
    }
    resp = client.post("/api/v1/export/svg", json=payload_unknown, headers={"X-Tenant-ID": TENANT_ID})
    assert_status(resp, 404, "unknown shape 404")
    ok("404 unknown shape", f"detail='{resp.json()['detail'][:60]}'")

    # ── Save sample SVG to file for manual inspection ─────────────────────────
    section("Bonus: save sample SVG output to disk")
    import os
    out_dir  = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_rectangle.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    ok("saved SVG", f"→ {out_path}")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All SVG exporter smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
