"""
Smoke Tests: PDF Exporter
=========================
Exercises the PdfExporter and the /export/pdf endpoint.
"""

from __future__ import annotations

import sys
import uuid
import os

from fastapi.testclient import TestClient

from app.exporters.pdf_exporter import PdfExporter
from app.geometry.shapes import SHAPE_REGISTRY, RECTANGLE_TEMPLATE
from app.main import app
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver


PASS = "✓"
FAIL = "✗"

client   = TestClient(app)
resolver = TemplateResolver()
builder  = GeometryBuilder()
exporter = PdfExporter()

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

def run_all() -> None:
    print("\nBuildDesk · PDF Exporter Smoke Tests")

    # ── 1. Direct Exporter Class ─────────────────────────────────────────────
    section("1. Direct Exporter Class (PdfExporter.export)")
    dims = {"length": 96.0, "width": 26.0}
    res = resolver.resolve(RECTANGLE_TEMPLATE, dims)
    r_build = builder.build(RECTANGLE_TEMPLATE, res, uuid.UUID(PROJECT_ID), uuid.UUID(TENANT_ID))
    
    pdf_bytes = exporter.export(r_build, "rectangle")
    if not pdf_bytes or len(pdf_bytes) < 100:
        fail("direct export", "Returned empty or tiny PDF")
    if not pdf_bytes.startswith(b"%PDF"):
        fail("direct export", "Does not start with %PDF")
    ok("direct export", f"Generated {len(pdf_bytes)} bytes of PDF data")

    # ── 2. API Endpoint ──────────────────────────────────────────────────────
    section("2. POST /api/v1/export/pdf")
    payload = {
        "shape_type": "rectangle",
        "project_id": PROJECT_ID,
        "tenant_id":  TENANT_ID,
        "dimensions": {"length": 96.0, "width": 26.0},
    }
    
    resp_inline = client.post("/api/v1/export/pdf", json=payload)
    assert_status(resp_inline, 200, "export API status")
    if resp_inline.headers["content-type"] != "application/pdf":
        fail("content-type", "Expected application/pdf")
    if not resp_inline.content.startswith(b"%PDF"):
        fail("api content", "Response is not a valid PDF")
    if "inline" not in resp_inline.headers["content-disposition"]:
        fail("disposition", "Expected inline disposition")
    ok("api POST", "Generated valid PDF inline")

    # ── 3. API Endpoint (Download) ───────────────────────────────────────────
    section("3. POST /api/v1/export/pdf?download=true")
    resp_dl = client.post("/api/v1/export/pdf?download=true", json=payload)
    assert_status(resp_dl, 200, "download API status")
    disp = resp_dl.headers.get("content-disposition", "")
    if "attachment" not in disp:
        fail("disposition", f"Expected attachment, got '{disp}'")
    ok("api POST download", "Generated valid PDF as attachment")

    # ── 4. Demo Endpoint ─────────────────────────────────────────────────────
    section("4. GET /api/v1/demo/pdf/rectangle")
    resp_demo = client.get("/api/v1/demo/pdf/rectangle")
    assert_status(resp_demo, 200, "demo API status")
    if not resp_demo.content.startswith(b"%PDF"):
        fail("demo content", "Not a valid PDF")
    ok("demo API", "Generated valid PDF")

    print(f"\n{'═' * 60}")
    print(f"  All PDF Exporter smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
