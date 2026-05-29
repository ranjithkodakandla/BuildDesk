#!/usr/bin/env python3
"""
Phase 15.5 — Live staging validation against deployed Cloud Run API.

Usage:
  STAGING_API_URL=https://builddesk-api-....run.app python scripts/run_staging_validation.py
  STAGING_UNIT_COUNT=200 python scripts/run_staging_validation.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = os.getenv(
    "STAGING_API_URL",
    "https://builddesk-api-149130710868.us-central1.run.app",
).rstrip("/")
UNIT_COUNT = int(os.getenv("STAGING_UNIT_COUNT", "200"))
POLL_TIMEOUT_S = int(os.getenv("STAGING_POLL_TIMEOUT_S", "180"))


@dataclass
class StepResult:
    name: str
    ok: bool
    duration_s: float
    detail: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class StagingRun:
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=BASE_URL, timeout=120.0)
        self.results: List[StepResult] = []
        self.tenant_id = str(uuid.uuid4())
        self.token: Optional[str] = None
        self.project_id: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"X-Tenant-ID": self.tenant_id}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _step(self, name: str, fn):
        t0 = time.perf_counter()
        try:
            detail, extra = fn()
            self.results.append(
                StepResult(name, True, time.perf_counter() - t0, detail, extra or {})
            )
        except Exception as exc:
            self.results.append(
                StepResult(name, False, time.perf_counter() - t0, str(exc))
            )
            raise

    def run(self) -> int:
        print(f"Staging validation → {BASE_URL} ({UNIT_COUNT} units)")
        self._step("health", self._health)
        self._step("auth_register_login", self._auth)
        self._step("tenant_profile_branding", self._tenant_profile)
        self._step("project_hierarchy", self._hierarchy)
        self._step("bulk_units", self._bulk_units)
        self._step("assemblies", self._assemblies)
        self._step("search", self._search)
        self._step("package_generate", self._package)
        self._step("exports", self._exports)
        self._step("revision_and_ops", self._revision_ops)
        self._step("tenant_isolation", self._tenant_isolation)
        return 0

    def _health(self):
        r = self.client.get("/api/v1/health")
        r.raise_for_status()
        body = r.json()
        if body.get("database") != "cloudsql-postgres-connected":
            raise RuntimeError(f"unexpected database status: {body.get('database')}")
        return f"db={body.get('database')}", body

    def _auth(self):
        email = f"staging_{uuid.uuid4().hex[:8]}@example.com"
        pwd = "StagingPass123!"
        reg = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pwd, "role": "admin"},
            headers={"X-Tenant-ID": self.tenant_id},
        )
        reg.raise_for_status()
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": pwd},
            headers={"X-Tenant-ID": self.tenant_id},
        )
        login.raise_for_status()
        self.token = login.json()["access_token"]
        me = self.client.get("/api/v1/auth/me", headers=self._headers())
        me.raise_for_status()
        return f"user={email}", {"tenant_id": self.tenant_id}

    def _tenant_profile(self):
        put = self.client.put(
            "/api/v1/tenant/profile",
            json={
                "company_name": "Canyon Staging Co",
                "logo_url": "placeholder://staging",
                "default_footer": "STAGING VERIFY ALL DIMENSIONS",
                "standard_notes": "Staging validation run",
            },
            headers=self._headers(),
        )
        put.raise_for_status()
        get = self.client.get("/api/v1/tenant/profile", headers=self._headers())
        get.raise_for_status()
        body = get.json()
        if body.get("company_name") != "Canyon Staging Co":
            raise RuntimeError("tenant profile not persisted")
        return "branding saved", body

    def _hierarchy(self):
        pr = self.client.post(
            "/api/v1/projects",
            json={
                "name": "Staging Tower Validation",
                "client_name": "Staging GC",
                "material": "Quartz 3cm",
                "hierarchy_config": {
                    "has_buildings": True,
                    "has_floors": True,
                    "has_unit_types": True,
                },
            },
            headers=self._headers(),
        )
        pr.raise_for_status()
        self.project_id = pr.json()["project_id"]
        b = self.client.post(
            f"/api/v1/projects/{self.project_id}/buildings",
            json={"name": "Tower 1", "code": "T1", "sort_order": 1},
            headers=self._headers(),
        )
        b.raise_for_status()
        building_id = b.json()["building_id"]
        floor_id = self.client.post(
            f"/api/v1/projects/{self.project_id}/floors",
            json={"building_id": building_id, "name": "Level 2", "number": 2, "sort_order": 1},
            headers=self._headers(),
        ).json()["floor_id"]
        self._floor_id = floor_id
        self._building_id = building_id
        self._unit_types = {}
        for code, mirror in [("A1", False), ("A1-MIR", True)]:
            ut = self.client.post(
                f"/api/v1/projects/{self.project_id}/unit-types",
                json={"code": code, "name": f"Type {code}", "is_mirror": mirror},
                headers=self._headers(),
            )
            ut.raise_for_status()
            self._unit_types[code] = ut.json()["unit_type_id"]
        return f"project={self.project_id}", {"project_id": self.project_id}

    def _bulk_units(self):
        end = UNIT_COUNT
        bulk = self.client.post(
            f"/api/v1/projects/{self.project_id}/units/bulk",
            json={
                "start_number": 1,
                "end_number": end,
                "prefix": "10",
                "increment": 1,
                "building_id": self._building_id,
                "floor_id": self._floor_id,
                "unit_type_id": self._unit_types["A1"],
                "variant": "standard",
            },
            headers=self._headers(),
        )
        bulk.raise_for_status()
        count = bulk.json().get("created_count", bulk.json())
        return f"units={count}", bulk.json()

    def _assemblies(self):
        types = self.client.get(
            f"/api/v1/projects/{self.project_id}/unit-types",
            headers=self._headers(),
        ).json()["unit_types"]
        a1 = next(t for t in types if t["code"] == "A1")
        asm = self.client.post(
            "/api/v1/assemblies",
            json={
                "project_id": self.project_id,
                "unit_type_id": a1["unit_type_id"],
                "name": "Kitchen A1",
                "assembly_type": "kitchen",
                "parts": [
                    {
                        "part_type": "main_top",
                        "name": "Main Top",
                        "dimensions": {"length": 96, "depth": 25.5, "thickness": 1.25},
                    }
                ],
            },
            headers=self._headers(),
        )
        asm.raise_for_status()
        asm_id = asm.json()["assembly_id"]
        dup = self.client.post(
            f"/api/v1/assemblies/{asm_id}/duplicate",
            json={"variant": "MIR", "name": "Kitchen A1-MIR"},
            headers=self._headers(),
        )
        dup.raise_for_status()
        svg = self.client.get(
            f"/api/v1/assemblies/{asm_id}/preview/svg",
            headers=self._headers(),
        )
        svg.raise_for_status()
        if b"<svg" not in svg.content:
            raise RuntimeError("invalid svg")
        return "assembly+duplicate+svg ok", {"assembly_id": asm_id}

    def _search(self):
        res = self.client.post(
            "/api/v1/search",
            json={"entity_types": ["units", "projects"], "query": "Staging"},
            headers=self._headers(),
        )
        res.raise_for_status()
        return f"hits={res.json().get('total_count')}", res.json()

    def _package(self):
        gen = self.client.post(
            f"/api/v1/projects/{self.project_id}/package/generate",
            json={"version": "Staging-1", "issued_by": "staging-script"},
            headers=self._headers(),
        )
        gen.raise_for_status()
        t0 = time.perf_counter()
        status_body = None
        for _ in range(POLL_TIMEOUT_S):
            st = self.client.get(
                f"/api/v1/projects/{self.project_id}/package/status",
                headers=self._headers(),
            )
            st.raise_for_status()
            status_body = st.json()
            if status_body["status"] == "ready":
                break
            if status_body["status"] == "generation_failed":
                err = status_body.get("generation_error", "unknown")
                raise RuntimeError(f"generation_failed: {err}")
            time.sleep(1)
        else:
            raise TimeoutError("package generation poll timeout")
        poll_s = time.perf_counter() - t0
        pdf = self.client.get(
            f"/api/v1/projects/{self.project_id}/package/pdf",
            headers=self._headers(),
        )
        pdf.raise_for_status()
        size = len(pdf.content)
        if pdf.content[:4] != b"%PDF":
            raise RuntimeError("not a pdf")
        storage = status_body.get("storage_reference", "")
        return f"pdf={size}B poll={poll_s:.1f}s", {
            "poll_seconds": round(poll_s, 2),
            "pdf_bytes": size,
            "storage_reference": storage,
            "generation_attempts": status_body.get("generation_attempts"),
        }

    def _exports(self):
        for export_type, fmt in [("schedule", "csv"), ("fabrication", "xlsx"), ("summary", "csv")]:
            self.client.post(
                f"/api/v1/projects/{self.project_id}/exports",
                json={"export_type": export_type, "format": fmt},
                headers=self._headers(),
            ).raise_for_status()
        return "3 exports queued", {}

    def _revision_ops(self):
        self.client.post(
            f"/api/v1/projects/{self.project_id}/package/generate",
            json={"version": "Rev A", "revision_notes": "staging rev"},
            headers=self._headers(),
        ).raise_for_status()
        pkg_id = None
        for _ in range(POLL_TIMEOUT_S):
            st = self.client.get(
                f"/api/v1/projects/{self.project_id}/package/status",
                headers=self._headers(),
            ).json()
            if st["status"] == "ready":
                pkg_id = st["package_id"]
                break
            time.sleep(1)
        if not pkg_id:
            raise TimeoutError("Rev A timeout")
        self.client.post(
            f"/api/v1/projects/{self.project_id}/packages/{pkg_id}/transition",
            json={"status": "submitted"},
            headers=self._headers(),
        ).raise_for_status()
        self.client.post(
            f"/api/v1/projects/{self.project_id}/packages/{pkg_id}/transition",
            json={"status": "approved", "review_notes": "staging approve"},
            headers=self._headers(),
        ).raise_for_status()
        rfi = self.client.post(
            f"/api/v1/projects/{self.project_id}/rfis",
            json={"title": "Staging RFI", "question": "Confirm sink", "package_id": pkg_id},
            headers=self._headers(),
        )
        rfi.raise_for_status()
        rfi_id = rfi.json()["rfi_id"]
        self.client.post(
            f"/api/v1/rfis/{rfi_id}/answer",
            json={"answer": "Undermount", "status": "answered"},
            headers=self._headers(),
        ).raise_for_status()
        return "rev+approval+rfi ok", {"package_id": pkg_id}

    def _tenant_isolation(self):
        other_tenant = str(uuid.uuid4())
        email = f"other_{uuid.uuid4().hex[:6]}@example.com"
        self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "OtherPass123!", "role": "admin"},
            headers={"X-Tenant-ID": other_tenant},
        ).raise_for_status()
        other_token = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "OtherPass123!"},
            headers={"X-Tenant-ID": other_tenant},
        ).json()["access_token"]
        r = self.client.get(
            f"/api/v1/projects/{self.project_id}",
            headers={"Authorization": f"Bearer {other_token}", "X-Tenant-ID": other_tenant},
        )
        if r.status_code != 404:
            raise RuntimeError(f"expected 404 cross-tenant, got {r.status_code}")
        return "cross-tenant blocked", {}


def main() -> int:
    run = StagingRun()
    failed = False
    try:
        run.run()
    except Exception as exc:
        failed = True
        print(f"FAILED: {exc}", file=sys.stderr)
    total = sum(r.duration_s for r in run.results)
    report = {
        "base_url": BASE_URL,
        "unit_count": UNIT_COUNT,
        "total_duration_s": round(total, 2),
        "passed": sum(1 for r in run.results if r.ok),
        "failed": sum(1 for r in run.results if not r.ok),
        "steps": [
            {
                "name": r.name,
                "ok": r.ok,
                "duration_s": round(r.duration_s, 2),
                "detail": r.detail,
                **r.extra,
            }
            for r in run.results
        ],
    }
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "staging_validation_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
