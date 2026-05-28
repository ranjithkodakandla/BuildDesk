"""
Smoke Tests: Template Resolver
==============================
Executable examples demonstrating the TemplateResolver against the
L Shape Kitchen template (the primary MVP shape).

Covers:
    ✓ valid payload   → success, clean dimensions
    ✗ missing required → validation error
    ✗ below min_value  → validation error
    ✗ above max_value  → validation error
    ✗ invalid select   → validation error
    ✓ optional absent  → omitted (no error)
    ✓ default applied  → default_value substituted
    ✓ boolean coercion → "yes" → True
    ✓ full pipeline    → ResolvedDimensions → GeometryModel construction

Run with:
    cd backend
    python -m tests.smoke_template_resolver
"""

from __future__ import annotations

import sys

from app.models.geometry import GeometryModel
from app.models.shape_template import (
    DimensionUnit,
    ShapeCategory,
    ShapeParameter,
    ShapeParameterType,
    ShapeTemplate,
)
from app.services.template_resolver import TemplateResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def expect_ok(label: str, result) -> None:
    if result.has_errors:
        print(f"  {FAIL}  [{label}] UNEXPECTED FAILURE: {result.errors}")
        sys.exit(1)
    print(f"  {PASS}  [{label}] OK — dimensions={result.dimensions}")


def expect_error(label: str, result, *expected_params) -> None:
    if not result.has_errors:
        print(f"  {FAIL}  [{label}] Expected validation error, got success: {result.dimensions}")
        sys.exit(1)
    failed_params = {e.parameter for e in result.errors}
    for p in expected_params:
        if p not in failed_params:
            print(f"  {FAIL}  [{label}] Expected error on '{p}' but got: {result.errors}")
            sys.exit(1)
    msgs = "; ".join(f"{e.parameter}: {e.message}" for e in result.errors)
    print(f"  {PASS}  [{label}] Correctly rejected — {msgs}")


# ---------------------------------------------------------------------------
# Fixture: L Shape Kitchen template
# ---------------------------------------------------------------------------

def make_l_kitchen_template() -> ShapeTemplate:
    return ShapeTemplate(
        name="L Shape Kitchen",
        category=ShapeCategory.kitchen,
        system_template=True,
        parameters=[
            ShapeParameter(
                name="A",
                label="Leg A length",
                parameter_type=ShapeParameterType.number,
                unit=DimensionUnit.inches,
                min_value=12.0,
                max_value=240.0,
                required=True,
            ),
            ShapeParameter(
                name="B",
                label="Leg B length",
                parameter_type=ShapeParameterType.number,
                unit=DimensionUnit.inches,
                min_value=12.0,
                max_value=240.0,
                required=True,
            ),
            ShapeParameter(
                name="Depth",
                label="Counter depth",
                parameter_type=ShapeParameterType.number,
                unit=DimensionUnit.inches,
                min_value=18.0,
                max_value=36.0,
                default_value=25.5,   # industry standard depth
                required=False,
            ),
            ShapeParameter(
                name="EdgeProfile",
                label="Edge profile style",
                parameter_type=ShapeParameterType.select,
                allowed_options=["eased", "beveled", "bullnose", "ogee"],
                default_value="eased",
                required=False,
            ),
            ShapeParameter(
                name="HasSink",
                label="Includes sink cutout",
                parameter_type=ShapeParameterType.boolean,
                required=False,
                default_value=False,
            ),
            ShapeParameter(
                name="Notes",
                label="Installer notes",
                parameter_type=ShapeParameterType.string,
                required=False,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def run_all() -> None:
    resolver = TemplateResolver()
    template = make_l_kitchen_template()

    print(f"\nBuildDesk · Template Resolver Smoke Tests")
    print(f"Template: {template.name}")

    # ── 1. Valid payload ────────────────────────────────────────────────────
    section("1. Valid full payload → success")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 48.0,
        "Depth": 24.0,
        "EdgeProfile": "bullnose",
        "HasSink": True,
        "Notes": "Handle with care",
    })
    expect_ok("full valid payload", result)

    # ── 2. Missing required parameter ──────────────────────────────────────
    section("2. Missing required parameter → error")
    result = resolver.resolve(template, {
        "B": 48.0,
        "Depth": 24.0,
        # "A" is missing
    })
    expect_error("missing A", result, "A")

    # ── 3. Below min_value ─────────────────────────────────────────────────
    section("3. Number below min_value → error")
    result = resolver.resolve(template, {
        "A": 8.0,   # min is 12
        "B": 48.0,
    })
    expect_error("A below min", result, "A")

    # ── 4. Above max_value ─────────────────────────────────────────────────
    section("4. Number above max_value → error")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 999.0,  # max is 240
    })
    expect_error("B above max", result, "B")

    # ── 5. Invalid select option ───────────────────────────────────────────
    section("5. Invalid select option → error")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 48.0,
        "EdgeProfile": "waterfall",  # not in allowed_options
    })
    expect_error("invalid EdgeProfile", result, "EdgeProfile")

    # ── 6. Optional parameter absent → omitted cleanly ────────────────────
    section("6. Optional parameter absent → omitted (no default)")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 48.0,
        # Notes is optional with no default → should be absent from output
    })
    expect_ok("optional absent", result)
    assert "Notes" not in result.dimensions, "Notes should be absent"
    print(f"         Notes absent from output: confirmed")

    # ── 7. Default value applied ───────────────────────────────────────────
    section("7. Optional absent with default → default applied")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 48.0,
        # Depth absent → should default to 25.5
        # EdgeProfile absent → should default to "eased"
    })
    expect_ok("defaults applied", result)
    assert result.dimensions.get("Depth") == 25.5, f"Expected Depth=25.5, got {result.dimensions.get('Depth')}"
    assert result.dimensions.get("EdgeProfile") == "eased", f"Expected EdgeProfile='eased', got {result.dimensions.get('EdgeProfile')}"
    print(f"         Depth defaulted to {result.dimensions['Depth']}, EdgeProfile defaulted to '{result.dimensions['EdgeProfile']}'")

    # ── 8. Boolean coercion from string ───────────────────────────────────
    section("8. Boolean coercion — string 'yes' → True")
    result = resolver.resolve(template, {
        "A": 96.0,
        "B": 48.0,
        "HasSink": "yes",
    })
    expect_ok("boolean coercion", result)
    assert result.dimensions.get("HasSink") is True, f"Expected HasSink=True, got {result.dimensions.get('HasSink')}"
    print(f"         HasSink coerced: 'yes' → {result.dimensions['HasSink']}")

    # ── 9. Multiple errors collected in one pass ──────────────────────────
    section("9. Multiple errors collected in one pass")
    result = resolver.resolve(template, {
        # A missing (required)
        "B": 500.0,        # above max
        "EdgeProfile": "waterfall",  # invalid option
    })
    expect_error("multi-error", result, "A", "B", "EdgeProfile")

    # ── 10. Full pipeline: resolve → GeometryModel ─────────────────────────
    section("10. Full pipeline: resolve → GeometryModel")
    import uuid
    result = resolver.resolve(template, {
        "A": 120.0,
        "B": 60.0,
        "Depth": 26.0,
        "EdgeProfile": "ogee",
        "HasSink": False,
    })
    expect_ok("pipeline resolve", result)

    project_id = uuid.uuid4()
    tenant_id  = uuid.uuid4()

    geometry = GeometryModel(
        project_id=project_id,
        tenant_id=tenant_id,
        template_id=template.template_id,
        dimensions=result.dimensions,
    )
    print(f"  {PASS}  [GeometryModel created] id={geometry.geometry_id} | dims={geometry.dimensions}")

    # ── Done ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
