# BuildDesk — Active Next Step
> **This file is the single source of truth for where development continues.**
> It is updated after every committed milestone. Read it at the start of every session.
> Cross-reference with `docs/session-start.md` for the full startup protocol.

---

## Current State

| Field | Value |
|---|---|
| **Last completed phase** | Phase 2 — Assembly & Fabrication Model |
| **Last commit** | `c0c7e5d` — docs(adr): add ADR-001 domain guardrail |
| **Active branch** | `main` |
| **Alembic HEAD** | `b2c3d4e5f6g7` — add_fabrication_domain |
| **Passing tests** | 142 / 142 |
| **GCP Cloud Run** | Live — Phase 2 fabrication API deployed and validated |

---

## Immediate Next Milestone

### Phase 3 — Project Package Generator

**Goal:** Generate a complete, multi-page PDF fabrication package for a project.
This is the primary deliverable BuildDesk exists to produce.

**Branch to create:** `feat/phase-3-package-generator`

**Deliverables (in implementation order):**

```
1. Domain Models
   app/models/package_generator.py
   - ProjectPackage: id, project_id, tenant_id, version, issued_by, issued_date,
                     status (draft|IFR|IFC|revised), pages[], generated_at
   - PackagePage: page_number, page_type (cover|type_sheet|assembly_drawing|summary),
                  title, content_ref

2. ORM Records (ADDITIVE — no drops)
   app/db/models.py
   - ProjectPackageRecord
   - PackagePageRecord

3. Alembic Migration
   alembic/versions/[hash]_add_project_packages.py
   - CREATE TABLE project_packages
   - CREATE TABLE package_pages

4. PackageRepository
   app/repositories/package_repository.py
   - save / get_by_id / list_by_project — tenant-scoped

5. PackagePdfExporter
   app/exporters/package_pdf_exporter.py
   - Page 1:   Cover  (project name, client, material, issue date, version)
   - Pages N:  Type Sheets  ("Type A — Qty 8 — Units: 101, 102...")
   - Pages N:  Assembly Drawing Pages  (per assembly per unit type,
                dimensioned parts, cutouts, holes, seams)
   - Last page: Summary  (total piece count, total sq ft, material quantities)

6. PackageGeneratorService
   app/services/package_generator_service.py
   - Orchestrates: Project → UnitTypes → Units → Assemblies → Parts
   - Handles variant logic (MIR pages are mirror-noted)
   - Calls PackagePdfExporter
   - Persists ProjectPackage record

7. Assembly SVG Preview
   app/exporters/assembly_svg_exporter.py  (wraps existing SvgExporter)
   - Single assembly → SVG drawing with parts, cutouts, holes, seams

8. API Router
   app/api/packages.py
   POST  /api/v1/projects/{id}/package/generate  → triggers generation
   GET   /api/v1/projects/{id}/package/pdf        → returns PDF binary
   GET   /api/v1/assemblies/{id}/preview/svg      → returns assembly SVG

9. API Schemas
   app/api/package_schemas.py

10. Tests
    backend/tests/test_package_generator.py
    - Create project → add unit types → add units → add assemblies → generate package
    - Verify: package created, page count correct, PDF binary returned
    - Verify: tenant isolation (cross-tenant package not accessible)
    - Verify: 401 on unauthenticated package generation
```

**Estimated effort:** 3–4 days

**Domain Validation (pre-confirmed):**
- Domain test: ✅ YES — this IS the fabrication package
- Hierarchy: ✅ Touches all levels: Project → UnitType → Unit → Assembly → Part
- Package: ✅ DIRECTLY produces cover + type sheets + drawing pages + summary
- Reuse: PDF Exporter WRAP, SVG Exporter WRAP, existing repositories EXTEND

---

## Pending Blockers

| Blocker | Impact | Resolution |
|---|---|---|
| None currently | — | — |

---

## Deferred Items (do not start until Phase 3 is complete)

| Item | Deferred To |
|---|---|
| `asyncpg` / async SQLAlchemy migration | Phase 6 |
| Frontend realignment (project wizard, unit tree, assembly builder UI) | Phase 5 |
| Cloud Storage for PDF persistence (GCS upload) | Phase 3+ optional |
| Advanced drawing logic (cutout outlines, hole markers, edge indicators) | Phase 4 |
| Old `SHAPE_REGISTRY` / `demo.py` retirement | Phase 5 |

---

## Recommended Next Prompt

Paste this at the start of the next development session:

```
Session start — BuildDesk Phase 3.

Read docs/session-start.md, docs/domain-guardrail.md, docs/current-state.md,
docs/next-step.md before doing anything.

Implement Phase 3 — Project Package Generator as specified in docs/next-step.md.

Rules:
- All migrations additive only (no DROP, no RENAME)
- Branch: feat/phase-3-package-generator off main
- Every deliverable must pass ADR-001 domain guardrail
- Update docs/current-state.md and docs/next-step.md after commit
```

---

## Update Protocol

**After every committed milestone, update this file:**

1. Change `Last completed phase` to the just-finished phase
2. Change `Last commit` to the new commit SHA and message
3. Change `Active branch` to the new branch (or `main` if merged)
4. Change `Alembic HEAD` to the new migration revision
5. Update `Passing tests` count
6. Update `GCP Cloud Run` status if deployed
7. Replace `Immediate Next Milestone` section with Phase N+1
8. Update `Pending Blockers` if anything changed
9. Update `Recommended Next Prompt` for the next phase

**Commit the updated next-step.md as part of the milestone commit.**
