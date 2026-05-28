"""
Smoke Tests: REST API Layer v1
==============================
Uses FastAPI TestClient to exercise all endpoints end-to-end
without starting a real HTTP server.

Covers:
    ✓ GET  /api/v1/health               → 200 ok
    ✓ GET  /api/v1/shapes               → 200 list of shapes
    ✓ GET  /api/v1/shapes/rectangle     → 200 full template detail
    ✗ GET  /api/v1/shapes/unknown       → 404
    ✓ POST /api/v1/geometry (valid)     → 200 computed geometry
    ✓ POST /api/v1/geometry (valid)     → area + perimeter correct
    ✓ POST /api/v1/geometry (valid)     → pieces + primitives present
    ✗ POST /api/v1/geometry (missing)   → 422 validation error
    ✗ POST /api/v1/geometry (out range) → 422 validation error
    ✗ POST /api/v1/geometry (bad shape) → 404 unknown shape type

Run with:
    cd backend
    python -m tests.smoke_api
"""

from __future__ import annotations

import sys
import uuid

from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Test client
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=True)

PASS = "✓"
FAIL = "✗"

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


def assert_status(resp, expected: int, label: str) -> None:
    if resp.status_code != expected:
        fail(label, f"Expected HTTP {expected}, got {resp.status_code}: {resp.text[:200]}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_all() -> None:
    print("\nBuildDesk · REST API Smoke Tests")
    print(f"Base URL: http://testclient")

    # ── 1. Health check ─────────────────────────────────────────────────────
    section("1. GET /api/v1/health → 200 ok")
    resp = client.get("/api/v1/health")
    assert_status(resp, 200, "health status")
    body = resp.json()
    assert body["status"] == "ok", f"Expected status=ok, got {body}"
    assert body["service"] == "buildesk-api"
    ok("health", f"status={body['status']} | service={body['service']}")

    # ── 2. List shapes ───────────────────────────────────────────────────────
    section("2. GET /api/v1/shapes → 200 list")
    resp = client.get("/api/v1/shapes")
    assert_status(resp, 200, "list shapes")
    body = resp.json()
    assert body["total"] >= 1, "Expected at least 1 shape"
    slugs = [s["shape_type"] for s in body["shapes"]]
    assert "rectangle" in slugs, f"Expected 'rectangle' in shapes, got {slugs}"
    ok("list shapes", f"total={body['total']} | slugs={slugs}")

    # ── 3. Get rectangle template ────────────────────────────────────────────
    section("3. GET /api/v1/shapes/rectangle → 200 full template")
    resp = client.get("/api/v1/shapes/rectangle")
    assert_status(resp, 200, "get rectangle")
    body = resp.json()
    assert body["name"] == "Rectangle"
    param_names = [p["name"] for p in body["parameters"]]
    assert "length" in param_names
    assert "width" in param_names
    ok("template name",       f"name={body['name']}")
    ok("template params",     f"params={param_names}")
    ok("schema_version",      f"schema_version={body['schema_version']}")

    # ── 4. Unknown shape → 404 ──────────────────────────────────────────────
    section("4. GET /api/v1/shapes/hexagon → 404")
    resp = client.get("/api/v1/shapes/hexagon")
    assert_status(resp, 404, "unknown shape 404")
    assert "hexagon" in resp.json()["detail"].lower()
    ok("404 unknown shape", f"detail='{resp.json()['detail'][:60]}'")

    # ── 5. Valid geometry request ────────────────────────────────────────────
    section("5. POST /api/v1/geometry (valid rectangle) → 200")
    payload = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96, "width": 42},
    }
    resp = client.post("/api/v1/geometry", json=payload)
    assert_status(resp, 200, "geometry success")
    body = resp.json()
    assert body["status"] == "computed"
    assert body["shape_type"] == "rectangle"
    ok("status",    f"status={body['status']}")
    ok("shape_type", f"shape_type={body['shape_type']}")
    ok("geometry_id", f"geometry_id={body['geometry_id']}")

    # ── 6. Area + perimeter ──────────────────────────────────────────────────
    section("6. POST /api/v1/geometry → area and perimeter correct")
    assert body["computed_area"]      == 96 * 42,        f"area mismatch: {body['computed_area']}"
    assert body["computed_perimeter"] == 2 * (96 + 42),  f"perimeter mismatch: {body['computed_perimeter']}"
    ok("area",      f"{body['computed_area']} in²")
    ok("perimeter", f"{body['computed_perimeter']} in")

    # ── 7. Pieces + primitives ───────────────────────────────────────────────
    section("7. POST /api/v1/geometry → pieces and primitives present")
    assert len(body["pieces"])          == 1, f"Expected 1 piece, got {len(body['pieces'])}"
    assert len(body["rectangles"])      == 1, f"Expected 1 rect, got {len(body['rectangles'])}"
    assert len(body["dimension_lines"]) == 2, f"Expected 2 dims, got {len(body['dimension_lines'])}"
    piece = body["pieces"][0]
    rect  = body["rectangles"][0]
    ok("piece",      f"label='{piece['label']}' | {piece['length']}\" × {piece['width']}\"")
    ok("rectangle",  f"width={rect['width']} | height={rect['height']} | area={rect['area']}")
    ok("dimensions", f"display_texts={[d['display_text'] for d in body['dimension_lines']]}")
    ok("thickness",  f"thickness={piece['thickness']}\" (default 3/4\")")

    # ── 8. Missing required parameter → 422 ─────────────────────────────────
    section("8. POST /api/v1/geometry (missing 'width') → 422")
    payload_missing = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96},   # width missing
    }
    resp = client.post("/api/v1/geometry", json=payload_missing)
    assert_status(resp, 422, "missing param 422")
    err_body = resp.json()
    assert err_body["error"] == "validation_error"
    param_names = [e["parameter"] for e in err_body["errors"]]
    assert "width" in param_names, f"Expected 'width' in errors, got {param_names}"
    ok("422 missing param", f"error={err_body['error']} | failed params={param_names}")

    # ── 9. Out-of-range parameter → 422 ─────────────────────────────────────
    section("9. POST /api/v1/geometry (length=2, below min=6) → 422")
    payload_range = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 2, "width": 42},   # 2 < min_value 6
    }
    resp = client.post("/api/v1/geometry", json=payload_range)
    assert_status(resp, 422, "out of range 422")
    err_body = resp.json()
    param_names = [e["parameter"] for e in err_body["errors"]]
    assert "length" in param_names
    ok("422 out of range", f"failed params={param_names} | msg='{err_body['errors'][0]['message'][:60]}'")

    # ── 10. Unknown shape type → 404 ─────────────────────────────────────────
    section("10. POST /api/v1/geometry (shape_type='hexagon') → 404")
    payload_bad_shape = {
        "shape_type": "hexagon",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96, "width": 42},
    }
    resp = client.post("/api/v1/geometry", json=payload_bad_shape)
    assert_status(resp, 404, "unknown shape POST 404")
    assert "hexagon" in resp.json()["detail"].lower()
    ok("404 unknown shape POST", f"detail='{resp.json()['detail'][:60]}'")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  All API smoke tests passed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run_all()
