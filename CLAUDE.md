# BuildDesk — Claude Code Context

## What this project is

Multifamily countertop fabrication package generator for Virgin Surfaces.
Users: fabricators, installers, designers (non-technical construction field workers).
Primary output: a multi-page PDF "shop drawing package" sent to the cutting shop.

## Always do first

```bash
# Verify backend tests (must be 85/85 before and after any change)
cd backend && .venv/bin/python -m pytest tests/ -q

# Verify frontend build (must be 0 TypeScript errors)
cd frontend && npm run build
```

## Key docs to read before starting work

1. `docs/next-step.md`       — current state, what's done, what's next
2. `docs/phase19-handoff.md` — exact implementation plan for next changes,
                               with file paths, code snippets, and acceptance criteria

## Reference PDFs (acceptance criteria for any PDF change)

```
/Users/ranjithkodakandla/Downloads/Virgin Surfaces/Virgin Surfaces - Project/PDF/
```
Open and study these before touching `fabrication_drawing_engine.py`.

## Most important files

```
backend/app/exporters/fabrication_drawing_engine.py  ← ALL drawing primitives
backend/app/exporters/package_pdf_exporter.py        ← multi-page PDF layout
frontend/src/components/OverviewPanel.tsx            ← job checklist (HOME tab)
frontend/src/components/HierarchyPanel.tsx           ← unit management
frontend/src/pages/WorkspacePage.tsx                 ← tab structure
```

## Current state (Phase 19 complete)

- Backend: 85/85 pytest passing
- Frontend: 107 modules, 0 TypeScript errors
- Two-zone drawing layout (backsplashes above main tops) working
- 4 dimension styles: DIM_INCH_MM / DIM_FRAC / DIM_LONG_MM / DIM_DECIMAL
- Fab parts table REMOVED from PDF (drawing fills full page)
- Unit list at bottom of drawing zone
- UX: job checklist, step numbers, unassigned units at top, quick-assign

## Next priority: PDF Visual Overhaul

See `docs/phase19-handoff.md` Section 4 for exact code changes.
Summary:
1. Remove colour fill from stone pieces (→ white background)
2. Remove colour from edge lines (→ line weight only, all dark)
3. Replace tick marks with arrowheads on dimension lines
4. Add real scale notation (e.g., `1/2" = 1'-0"`)

## Constraints

- Never drop a test — 85 must remain 85
- Never change data model without Alembic migration
- Never change API routes/shapes without updating frontend types
- Never add a parts table back below the drawing
- Never add colour coding to edge treatments (references use line weight only)

## How to generate a test PDF quickly

```bash
cd backend
.venv/bin/python tools/generate_demo_pdf.py
# or write a quick script — see docs/phase19-handoff.md Section 7
```
