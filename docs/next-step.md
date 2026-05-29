# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 3 — Project Package Generator  |
| Git branch         | `feat/phase-3-package-generator` (to be committed) |
| Test baseline      | **54 / 54 passing**                    |
| Migration state    | `c3d4e5f6g7h8` applied (project_packages + package_pages) |

---

## Immediate Next Milestone

**Phase 4 — Advanced Drawing & Vector Rendering**

Goal: Upgrade assembly drawing pages from text-based dimension tables to true scaled vector drawings.

Priority tasks:
1. **Part outline to scale** — render each part as a scaled rectangle in the PDF (reuse ReportLab canvas)
2. **Cutout vector overlays** — draw dashed rectangles at correct positions within each part
3. **Hole markers** — draw ○ circles at correct center positions
4. **Splash indicators** — draw edge bands for back/left/right splashes
5. **Dimension callout lines** — leader lines with arrowheads (ReportLab lines + arrowheads)
6. **Edge treatment annotations** — label each part edge with treatment type
7. **Assembly thumbnail view** — put a scaled plan-view thumbnail on the type sheet

Domain test: All rendering must be faithful to real countertop shop drawing conventions.

---

## Pending Blockers

- None blocking Phase 4.
- `storage_reference` field in `ProjectPackageRecord` reserved for Phase 6 (GCS upload).
- `asyncpg` migration deferred to Phase 6 (Cloud Run async transition).
- Frontend realignment deferred until Phase 5 (after drawing engine is stable).

---

## Recommended Next Prompt

```
AUTONOMOUS IMPLEMENTATION MODE — Phase 4

Mandatory startup:
1. docs/session-start.md
2. docs/domain-guardrail.md
3. docs/current-state.md

PHASE 4 GOAL: Advanced Vector Drawing for Assembly Pages.

Upgrade the PackagePdfExporter assembly drawing pages to true scaled vector drawings
using ReportLab canvas primitives:

1. Part outlines rendered to scale (1 inch = N pts, auto-fit to page)
2. Cutout overlays (dashed rectangle at center_x/center_y with dims)
3. Hole markers (circles with Ø label)
4. Splash bands (edge hatching / shaded bands)
5. Dimension callout lines with arrows
6. Edge treatment label per edge position

Domain test: Drawing must match real countertop shop drawing conventions.
If NO → reject and document in ADR rejection table.

Tests: 20+ new tests. Must maintain 54 / 54 existing tests passing.
Branch: feat/phase-4-vector-drawing
Do not break existing endpoints.
```
