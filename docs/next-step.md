# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 4 — Advanced Drawing & Vector Rendering |
| Git branch         | `feat/phase-4-drawing-fidelity` (to be committed) |
| Test baseline      | **54 / 54 passing**                    |
| Migration state    | `c3d4e5f6g7h8` applied (no new migrations in Phase 4) |

---

## Immediate Next Milestone

**Phase 5 — Frontend Realignment**

Goal: Align the React frontend to the new fabrication-aware domain models.

Priority tasks:
1. **Assembly Builder UI** — Create UI for defining assemblies, parts, edges, cutouts, holes, and splashes.
2. **Project Hierarchy UI** — Build the UI for navigating Project → Building → Floor → Unit → UnitType.
3. **SVG Preview Integration** — Render the new `AssemblySvgExporter` output in the browser.
4. **Package Generation Trigger** — Add a button to generate the package and download the PDF.

Domain test: Does the UI allow a user to successfully define a multifamily project structure and generate its fabrication package?

---

## Pending Blockers

- None blocking Phase 5.
- `storage_reference` field in `ProjectPackageRecord` reserved for Phase 6 (GCS upload).
- `asyncpg` migration deferred to Phase 6 (Cloud Run async transition).

---

## Recommended Next Prompt

```
AUTONOMOUS IMPLEMENTATION MODE — Phase 5

Mandatory startup:
1. docs/session-start.md
2. docs/domain-guardrail.md
3. docs/current-state.md

PHASE 5 GOAL: Frontend Realignment to Fabrication Domain.

Upgrade the React frontend to support the new hierarchy and fabrication models:

1. Project/Unit navigation.
2. Assembly creation with Part, Edge, Cutout, Hole, Splash details.
3. Live SVG preview integration.
4. Package generation and PDF download.

Domain test: Must support defining a real countertop project.
If NO → reject and document in ADR rejection table.

Branch: feat/phase-5-frontend-realignment
```
