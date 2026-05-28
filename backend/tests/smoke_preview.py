"""
Smoke Tests: Preview / Export Convenience Layer
===============================================
Tests the demo endpoints, download mode, and CLI utility.

Covers:
    ✓ GET  /api/v1/demo/rectangle     → 200 SVG inline
    ✓ GET  /api/v1/demo/island        → 200 SVG inline
    ✓ demo/rectangle SVG structure valid
    ✓ demo/island SVG has polygon element
    ✓ demo endpoint headers correct (X-BuildDesk-Demo)
    ✓ POST /api/v1/export/svg (default) → Content-Disposition: inline
    ✓ POST /api/v1/export/svg?download=true → Content-Disposition: attachment
    ✓ CLI generate() rectangle → file written
    ✓ CLI generate() island → file written
    ✓ CLI generate() unknown shape → ValueError raised
    ✗ CLI generate() with invalid demo payload would fail at build time

Run with:
    cd backend
    python -m tests.smoke_preview
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PASS = "✓"
FAIL = "✗"

client     = TestClient(app)
PROJECT_ID = str(uuid.uuid4())
TENANT_ID  = str(uuid.uuid4())

_OUT_DIR = os.path.join(os.path.dirname(__file__), "output")


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
        fail(label, f"Expected '{needle}' not found")
    ok(label, f"'{needle}' present")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · Preview / Export Convenience Layer Smoke Tests")

    # ── 1. GET /demo/rectangle → 200 ─────────────────────────────────────────
    section("1. GET /api/v1/demo/rectangle → 200 SVG")
    resp = client.get("/api/v1/demo/rectangle")
    assert_status(resp, 200, "demo rectangle status")
    ct = resp.headers.get("content-type", "")
    if "svg" not in ct:
        fail("content-type", f"Expected svg, got '{ct}'")
    ok("status",       "200")
    ok("content-type", f"{ct}")
    ok("svg length",   f"{len(resp.text)} chars")

    # ── 2. GET /demo/island → 200 ────────────────────────────────────────────
    section("2. GET /api/v1/demo/island → 200 SVG")
    resp = client.get("/api/v1/demo/island")
    assert_status(resp, 200, "demo island status")
    ok("status",     "200")
    ok("svg length", f"{len(resp.text)} chars")

    # ── 3. Rectangle SVG structure ───────────────────────────────────────────
    section("3. demo/rectangle SVG structure valid")
    resp = client.get("/api/v1/demo/rectangle")
    svg  = resp.text
    assert_in(svg, "<svg ",   "svg root")
    assert_in(svg, "<rect ",  "rect element")
    assert_in(svg, "96.0&quot;",  "length dim text")
    assert_in(svg, "26.0&quot;",  "width dim text")
    assert_in(svg, "Standard Countertop", "piece label")

    # ── 4. Island SVG has polygon ────────────────────────────────────────────
    section("4. demo/island SVG has polygon (closed outline)")
    resp = client.get("/api/v1/demo/island")
    svg  = resp.text
    assert_in(svg, "<polygon", "polygon element")
    assert_in(svg, "Kitchen Island", "island label")

    # ── 5. Demo headers correct ──────────────────────────────────────────────
    section("5. Demo endpoint headers (X-BuildDesk-Demo, Content-Disposition)")
    resp = client.get("/api/v1/demo/rectangle")
    xdemo = resp.headers.get("x-builddesk-demo", "")
    disp  = resp.headers.get("content-disposition", "")
    if xdemo != "true":
        fail("X-BuildDesk-Demo", f"Expected 'true', got '{xdemo}'")
    if "inline" not in disp:
        fail("Content-Disposition", f"Expected inline, got '{disp}'")
    ok("X-BuildDesk-Demo",     f"value='{xdemo}'")
    ok("Content-Disposition",  f"'{disp}'")

    # ── 6. POST /export/svg (default) → inline ───────────────────────────────
    section("6. POST /api/v1/export/svg (default) → Content-Disposition: inline")
    payload = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96, "width": 26},
    }
    resp = client.post("/api/v1/export/svg", json=payload)
    assert_status(resp, 200, "export inline status")
    disp = resp.headers.get("content-disposition", "")
    if "inline" not in disp:
        fail("inline disposition", f"Got '{disp}'")
    ok("inline mode", f"Content-Disposition: {disp}")

    # ── 7. POST /export/svg?download=true → attachment ───────────────────────
    section("7. POST /api/v1/export/svg?download=true → Content-Disposition: attachment")
    resp = client.post("/api/v1/export/svg?download=true", json=payload)
    assert_status(resp, 200, "export download status")
    disp = resp.headers.get("content-disposition", "")
    if "attachment" not in disp:
        fail("attachment disposition", f"Got '{disp}'")
    if "buildesk-rectangle.svg" not in disp:
        fail("filename in disposition", f"Got '{disp}'")
    ok("attachment mode",  f"Content-Disposition: {disp}")

    # ── 8. CLI generate() rectangle ──────────────────────────────────────────
    section("8. CLI generate_demo_svg.generate() rectangle")
    # Import the generator directly (avoids subprocess)
    import importlib.util
    _tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools")
    spec = importlib.util.spec_from_file_location(
        "generate_demo_svg",
        os.path.join(_tools_dir, "generate_demo_svg.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    path = mod.generate("rectangle", _OUT_DIR, scale=4.0)
    if not os.path.isfile(path):
        fail("cli rectangle", f"File not found: {path}")
    size = os.path.getsize(path)
    ok("cli rectangle", f"→ {path} ({size} bytes)")

    # ── 9. CLI generate() island ─────────────────────────────────────────────
    section("9. CLI generate_demo_svg.generate() island")
    path = mod.generate("island", _OUT_DIR, scale=4.0)
    if not os.path.isfile(path):
        fail("cli island", f"File not found: {path}")
    size = os.path.getsize(path)
    ok("cli island", f"→ {path} ({size} bytes)")

    # Spot-check the island SVG has polygon
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "<polygon" not in content:
        fail("island svg polygon", "No <polygon in island_demo.svg")
    ok("island svg polygon", "<polygon present in file")

    # ── 10. CLI generate() unknown shape → ValueError ─────────────────────────
    section("10. CLI generate() unknown shape → ValueError")
    try:
        mod.generate("hexagon", _OUT_DIR, scale=4.0)
        fail("ValueError not raised", "Expected ValueError for unknown shape")
    except ValueError as exc:
        ok("ValueError raised", f"{exc}")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All preview/export smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
