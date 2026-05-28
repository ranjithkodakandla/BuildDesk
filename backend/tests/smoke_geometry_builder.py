"""
Smoke Tests: Geometry Builder
==============================
Executable examples demonstrating the full pipeline:

    TemplateResolver → ResolvedDimensions → GeometryBuilder → GeometryBuildResult

Covers:
    ✓ rectangle — valid payload → GeometryModel computed
    ✓ rectangle — area and perimeter computed correctly
    ✓ rectangle — GeometryPiece populated correctly
    ✓ rectangle — primitives generated (Rectangle, DimensionLines, Annotation)
    ✗ rectangle — missing required parameter → resolver error (pre-build)
    ✗ rectangle — below min_value → resolver error (pre-build)
    ✗ rectangle — building from error result → GeometryBuildError
    ✗ unsupported shape type → UnsupportedShapeError
    ✓ thickness default applied
    ✓ full pipeline: resolver → builder → GeometryModel ready

Run with:
    cd backend
    python -m tests.smoke_geometry_builder
"""

from __future__ import annotations

import sys
import uuid

from app.geometry.shapes import RECTANGLE_TEMPLATE, SHAPE_REGISTRY
from app.models.geometry import GeometryStatus
from app.models.shape_template import ShapeCategory, ShapeTemplate
from app.services.geometry_builder import (
    GeometryBuildError,
    GeometryBuilder,
    UnsupportedShapeError,
)
from app.services.template_resolver import TemplateResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"

PROJECT_ID = uuid.uuid4()
TENANT_ID  = uuid.uuid4()

resolver = TemplateResolver()
builder  = GeometryBuilder()


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print(f"\nBuildDesk · Geometry Builder Smoke Tests")
    print(f"Template: {RECTANGLE_TEMPLATE.name}")

    # ── 1. Valid rectangle → success ────────────────────────────────────────
    section("1. Valid rectangle payload → GeometryModel computed")
    resolved = resolver.resolve(RECTANGLE_TEMPLATE, {"length": 96, "width": 42})
    if resolved.has_errors:
        fail("resolve", str(resolved.errors))
    result = builder.build(RECTANGLE_TEMPLATE, resolved, PROJECT_ID, TENANT_ID)
    g = result.geometry
    if g.status != GeometryStatus.computed:
        fail("status", f"Expected computed, got {g.status}")
    ok("status", f"status={g.status.value}")
    ok("template_id", f"template_id matches: {g.template_id == RECTANGLE_TEMPLATE.template_id}")

    # ── 2. Area and perimeter ───────────────────────────────────────────────
    section("2. Area and perimeter computed correctly")
    expected_area = 96 * 42
    expected_perim = 2 * (96 + 42)
    if g.computed_area != expected_area:
        fail("area", f"Expected {expected_area}, got {g.computed_area}")
    if g.computed_perimeter != expected_perim:
        fail("perimeter", f"Expected {expected_perim}, got {g.computed_perimeter}")
    ok("area",      f"{g.computed_area} in²")
    ok("perimeter", f"{g.computed_perimeter} in")

    # ── 3. GeometryPiece ────────────────────────────────────────────────────
    section("3. GeometryPiece populated correctly")
    if len(g.pieces) != 1:
        fail("piece count", f"Expected 1 piece, got {len(g.pieces)}")
    piece = g.pieces[0]
    assert piece.length == 96.0
    assert piece.width  == 42.0
    assert piece.area   == expected_area
    ok("piece",    f"label='{piece.label}' | {piece.length}\" × {piece.width}\" | area={piece.area} in²")
    ok("thickness", f"thickness={piece.thickness}\" (default applied)")

    # ── 4. Primitives generated ─────────────────────────────────────────────
    section("4. Geometry primitives produced")
    if len(result.rectangles) != 1:
        fail("rectangles", f"Expected 1 Rectangle, got {len(result.rectangles)}")
    rect = result.rectangles[0]
    assert rect.width  == 96.0
    assert rect.height == 42.0
    ok("Rectangle",  f"origin=({rect.origin.x},{rect.origin.y}) | {rect.width}×{rect.height} | area={rect.area}")
    ok("edges",      f"4 edges: {[e.label for e in rect.edges]}")
    ok("center",     f"center=({rect.center.x}, {rect.center.y})")

    if len(result.dimension_lines) != 2:
        fail("DimensionLines", f"Expected 2, got {len(result.dimension_lines)}")
    ok("DimensionLines", f"{[d.display_text for d in result.dimension_lines]}")

    if len(result.annotations) != 1:
        fail("TextAnnotation", f"Expected 1, got {len(result.annotations)}")
    ok("TextAnnotation", f"text='{result.annotations[0].text}'")

    # ── 5. Missing required parameter → resolver error ───────────────────────
    section("5. Missing required parameter → resolver error (pre-build)")
    resolved_err = resolver.resolve(RECTANGLE_TEMPLATE, {"width": 42})
    if not resolved_err.has_errors:
        fail("missing length", "Expected resolver error")
    ok("missing length", f"correctly rejected: {resolved_err.errors[0].message}")

    # ── 6. Below min_value → resolver error ─────────────────────────────────
    section("6. Below min_value → resolver error (pre-build)")
    resolved_err = resolver.resolve(RECTANGLE_TEMPLATE, {"length": 2, "width": 42})
    if not resolved_err.has_errors:
        fail("length below min", "Expected resolver error")
    ok("length below min", f"correctly rejected: {resolved_err.errors[0].message}")

    # ── 7. Building from error result → GeometryBuildError ──────────────────
    section("7. Building from error result → GeometryBuildError raised")
    try:
        builder.build(RECTANGLE_TEMPLATE, resolved_err, PROJECT_ID, TENANT_ID)
        fail("GeometryBuildError", "Expected exception not raised")
    except GeometryBuildError as exc:
        ok("GeometryBuildError", f"raised correctly: {type(exc).__name__}")

    # ── 8. Unsupported shape type → UnsupportedShapeError ──────────────────
    section("8. Unknown shape type → UnsupportedShapeError")
    unknown_template = ShapeTemplate(
        name="HexagonalSink",
        category=ShapeCategory.custom,
        system_template=False,
        parameters=[],
    )
    fake_resolved = resolver.resolve(unknown_template, {})
    try:
        builder.build(unknown_template, fake_resolved, PROJECT_ID, TENANT_ID)
        fail("UnsupportedShapeError", "Expected exception not raised")
    except UnsupportedShapeError as exc:
        ok("UnsupportedShapeError", f"raised correctly: {type(exc).__name__}")

    # ── 9. Thickness default applied ────────────────────────────────────────
    section("9. Thickness default applied when absent")
    resolved_default = resolver.resolve(RECTANGLE_TEMPLATE, {"length": 60, "width": 24})
    result_default = builder.build(RECTANGLE_TEMPLATE, resolved_default, PROJECT_ID, TENANT_ID)
    piece_default = result_default.geometry.pieces[0]
    if piece_default.thickness != 0.75:
        fail("thickness default", f"Expected 0.75, got {piece_default.thickness}")
    ok("thickness default", f"thickness={piece_default.thickness}\" (default 3/4\" applied)")

    # ── 10. SHAPE_REGISTRY lookup ────────────────────────────────────────────
    section("10. SHAPE_REGISTRY lookup → rectangle template")
    tmpl = SHAPE_REGISTRY.get("rectangle")
    if tmpl is None:
        fail("registry", "rectangle not in SHAPE_REGISTRY")
    resolved_reg = resolver.resolve(tmpl, {"length": 48, "width": 24})
    result_reg   = builder.build(tmpl, resolved_reg, PROJECT_ID, TENANT_ID)
    ok("SHAPE_REGISTRY", f"looked up and built: area={result_reg.geometry.computed_area} in²")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All geometry builder smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
