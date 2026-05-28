"""
BuildDesk Demo SVG Generator — CLI tool
========================================
Generates demo SVG drawings locally without starting the API server.

Usage:
    python backend/tools/generate_demo_svg.py rectangle
    python backend/tools/generate_demo_svg.py island
    python backend/tools/generate_demo_svg.py all

Output:
    backend/tests/output/<shape>_demo.svg

Options:
    --out-dir  PATH   Override the default output directory.
    --scale    FLOAT  SVG scale factor (pixels per inch). Default: 4.0.
    --open             Open the SVG in the default browser after generating.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
import webbrowser

# Make sure `app` is importable when running from project root
_HERE     = os.path.dirname(os.path.abspath(__file__))
_BACKEND  = os.path.dirname(_HERE)           # .../backend
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.exporters.svg_exporter import SvgExporter            # noqa: E402
from app.geometry.shapes import SHAPE_REGISTRY                 # noqa: E402
from app.services.geometry_builder import GeometryBuilder      # noqa: E402
from app.services.template_resolver import TemplateResolver    # noqa: E402

# ---------------------------------------------------------------------------
# Demo payloads — same as demo router
# ---------------------------------------------------------------------------

_DEMO_PAYLOADS: dict[str, dict] = {
    "rectangle": {
        "length": 96.0,
        "width": 26.0,
        "thickness": 0.75,
        "label": "Standard Countertop",
    },
    "island": {
        "length": 72.0,
        "width": 36.0,
        "thickness": 0.75,
        "corner_radius": 2.0,
        "label": "Kitchen Island",
    },
    "vanity": {
        "length": 48.0,
        "width": 22.0,
        "thickness": 0.75,
        "backsplash_height": 4.0,
        "sink_cutout": True,
        "sink_diameter": 12.0,
        "label": "Bathroom Vanity",
    },
    "straight_kitchen": {
        "length": 180.0,
        "width": 26.0,
        "thickness": 0.75,
        "backsplash_height": 4.0,
        "seam_enabled": True,
        "slab_max_length": 120.0,
        "label": "Main Kitchen Run",
    },
    "l_kitchen": {
        "leg_a_length": 120.0,
        "leg_b_length": 96.0,
        "width": 26.0,
        "thickness": 1.18,
        "seam_enabled": True,
        "corner_join_type": "miter",
        "label": "L-Shape Layout",
    },
}

_DEMO_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEMO_TENANT_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")

# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

def generate(shape_type: str, out_dir: str, scale: float) -> str:
    """
    Generate a demo SVG for *shape_type* and write it to *out_dir*.

    Returns:
        Absolute path of the written SVG file.

    Raises:
        ValueError: if shape_type is not in SHAPE_REGISTRY or _DEMO_PAYLOADS.
    """
    if shape_type not in SHAPE_REGISTRY:
        available = ", ".join(sorted(SHAPE_REGISTRY.keys()))
        raise ValueError(
            f"Unknown shape_type '{shape_type}'. Available: {available}"
        )
    if shape_type not in _DEMO_PAYLOADS:
        raise ValueError(
            f"No demo payload defined for shape_type '{shape_type}'."
        )

    template = SHAPE_REGISTRY[shape_type]
    dims     = _DEMO_PAYLOADS[shape_type]

    resolver = TemplateResolver()
    builder  = GeometryBuilder()
    exporter = SvgExporter(scale=scale)

    resolved = resolver.resolve(template, dims)
    if resolved.has_errors:
        raise RuntimeError(f"Demo payload failed validation: {resolved.errors}")

    result = builder.build(
        template=template,
        resolved=resolved,
        project_id=_DEMO_PROJECT_ID,
        tenant_id=_DEMO_TENANT_ID,
    )

    svg = exporter.export(result)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{shape_type}_demo.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)

    return os.path.abspath(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    default_out = os.path.join(
        os.path.dirname(_BACKEND), "backend", "tests", "output"
    )

    parser = argparse.ArgumentParser(
        prog="generate_demo_svg",
        description="BuildDesk — generate demo SVG drawings locally.",
    )
    parser.add_argument(
        "shape",
        nargs="?",
        default="all",
        choices=list(_DEMO_PAYLOADS.keys()) + ["all"],
        help=(
            "Shape type to generate. "
            f"Choices: {', '.join(_DEMO_PAYLOADS.keys())}, all (default: all)"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=default_out,
        metavar="PATH",
        help=f"Output directory (default: {default_out})",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=4.0,
        metavar="FLOAT",
        help="SVG pixels per inch (default: 4.0)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open generated SVG(s) in default browser after writing.",
    )

    args = parser.parse_args()

    shapes = list(_DEMO_PAYLOADS.keys()) if args.shape == "all" else [args.shape]

    written: list[str] = []
    for shape in shapes:
        try:
            path = generate(shape, args.out_dir, args.scale)
            print(f"  ✓  {shape:20s} → {path}")
            written.append(path)
        except Exception as exc:
            print(f"  ✗  {shape:20s} → ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.open:
        for path in written:
            webbrowser.open(f"file://{path}")

    print(f"\nGenerated {len(written)} SVG(s).")


if __name__ == "__main__":
    main()
