# Next Step

> Updated after Phase 19 (Geometry-Aware Drawing Composition + UX Redesign).
> Read `docs/phase19-handoff.md` before starting new work — it contains the exact
> pending changes with file paths, line numbers, and reasoning.

---

## Current State

| Field                 | Value |
|-----------------------|-------|
| Active branch         | local working tree (no git) |
| Last completed phase  | Phase 19 — Geometry-Aware Drawing + UX Redesign |
| Test baseline         | Backend **85 / 85** pytest passing |
| Frontend build        | TypeScript 0 errors, 107 modules |
| Live URL              | `https://builddesk-api-149130710868.us-central1.run.app` |
| GCS bucket            | `builddesk-artifacts-stonedesk-app` |
| Alembic head          | `a8f1c2d3e4b5` |

---

## What was completed in Phase 17–19 (this session)

### Phase 17 — UX Redesign (Frontend)
**Files changed:** `frontend/src/pages/WorkspacePage.tsx`, `OverviewPanel.tsx`,
`HierarchyPanel.tsx`, `DashboardPage.tsx`

- Tab renames: "Unit Schedule" → "Units & Types", "Package" → "PDF Package",
  "Queue" → "Issues & RFIs"
- Step numbers on every tab (1–5) so users always know where they are
- Overview panel replaced abstract health tiles with a **3-step job checklist**
  (Import & Assign → Review Drawings → Generate PDF) with direct action buttons
- "Generate Fabrication PDF" hero button appears when all steps are green
- PDF-ready state shows green "Open / Download PDF" card
- HierarchyPanel redesigned:
  - Unassigned units shown at TOP with amber warning + "Select All" button
  - Inline quick-assign dropdown on each unassigned unit chip
  - Unit chips enlarged (min-h 40px, text-sm) for tablet use
  - Always-visible "Add Stone Type" sidebar (was hidden in "Tools ▼" dropdown)
  - Progress bar showing X of Y units assigned
  - Search box to filter units
  - "Generate Units" form always visible in sidebar
- Dashboard: "New Project" → "New Job", cleaner project cards with status dot

### Phase 18 — PDF Drawing Composition Engine (Backend)
**Files changed:** `backend/app/exporters/fabrication_drawing_engine.py`

- **Two-zone layout**: thin parts (depth ≤ 5.5") drawn as separate stone rectangles
  in TOP zone; main countertop pieces in BOTTOM zone
- **Width-matched alignment**: each BS/SS piece horizontally centred above the main
  top whose width most closely matches it (greedy matching)
- **Layout trigger**: two-zone auto-triggers whenever assembly has BOTH splash parts
  AND main tops — regardless of total part count (was `len(parts) >= 3`)
- **Scale bug fixed**: `min(scale_w, scale_h)` — was using `max()` (wrong)
- **Scale cap raised**: 8.0 → 12.0 pts/inch so single-piece assemblies fill zone
- **Vertical centering**: parts centred within available zone height
- **L-shape detection**: checks `LEFT_RETURN`/`RIGHT_RETURN` PartTypes;
  draws "L-CORNER" annotation at seam junction
- **Seam lines**: only between adjacent main-top parts, not across BS pieces
- `_is_splash_part(part)`: depth ≤ 5.5" → splash
- `_get_splash_label(part)`: BS / L-SS / R-SS / SS from part name
- `_draw_splash_piece_edges()`: polished top/left/right, raw dashed bottom

### Phase 19 — Dimension Formats + PDF Table Removal (Backend)
**Files changed:** `backend/app/exporters/fabrication_drawing_engine.py`,
`backend/app/exporters/package_pdf_exporter.py`

**4 dimension styles now supported:**
- `DIM_INCH_MM`  → `28.5" [724]`   (BULL OUTDOOR / default)
- `DIM_FRAC`     → `28 1/2"`        (Deforest Yards US CAD style)
- `DIM_LONG_MM`  → `28.5 in [724 mm]` (Concord North style)
- `DIM_DECIMAL`  → `28.5"`          (simple)

All styles propagate to width, depth, AND cutout location dimensions.
`fmt_dim(value, style)` dispatcher used everywhere — no format mismatch.

**PDF table removed:**  The `PART / SIZE / EDGE / CUTOUT / SQFT` compact fab table
that appeared below every assembly drawing has been removed. Drawing zone expanded by
~85 pts (the reclaimed table height). Zero parts table in any reference PDF.

**Unit list at bottom of drawing zone:**  `UNITS: 101, 201, 301, 122, 222, 322`
matches Deforest/Haven reference style.

**`_infer_dim_style(project)`:**  Auto-selects style from project material string
("metric"/"mm" keywords → `long_mm`, otherwise `inch_mm`).

---

## Next pending work — PDF Visual Overhaul

**See `docs/phase19-handoff.md` for exact implementation plan.**

Summary:
1. Black-and-white drawing style (remove color fill, use line weight only)
2. Proper arrowhead dimension lines
3. Real scale calculation and notation
4. (Later) Inline piece editor in Shop Drawings tab
5. (Later) Building/floor unit schedule table on drawings

---

## Key file locations

```
backend/app/exporters/fabrication_drawing_engine.py  ← drawing primitives
backend/app/exporters/package_pdf_exporter.py        ← multi-page PDF layout
frontend/src/pages/WorkspacePage.tsx                 ← tab structure
frontend/src/pages/DashboardPage.tsx                 ← project list
frontend/src/components/OverviewPanel.tsx            ← job checklist
frontend/src/components/HierarchyPanel.tsx           ← unit management
frontend/src/components/PackagesPanel.tsx            ← PDF generate/download
frontend/src/components/AssembliesPanel.tsx          ← shop drawings view
```

## How to verify before any new work

```bash
cd backend
.venv/bin/python -m pytest tests/ -q     # must be 85/85

cd ../frontend
npm run build                             # must be 0 TypeScript errors
```
