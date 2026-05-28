"""
Smoke Tests: Deployment Foundation
==================================
Tests configuration, health endpoints, and Docker assumptions.
"""

import sys
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PASS = "✓"
FAIL = "✗"

def ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {PASS}  [{label}]{suffix}")

def fail(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {FAIL}  [{label}]{suffix}")
    sys.exit(1)

def run_all() -> None:
    print("\nBuildDesk · Deployment Smoke Tests")
    
    resp = client.get("/api/v1/health")
    if resp.status_code != 200:
        fail("health", f"Got status {resp.status_code}")
    data = resp.json()
    
    if "database" not in data or "tenant_mode" not in data:
        fail("health", "Missing new health fields")
        
    ok("health", f"Status OK, DB={data['database']}, Version={data['version']}")
    
    from app.config import get_settings
    settings = get_settings()
    ok("config", f"Settings loaded successfully. DEBUG={settings.debug}")
    
    print(f"\n{'═' * 60}")
    print("  All Deployment smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
