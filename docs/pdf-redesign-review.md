# PDF Redesign Review -- Phase 17

**Branch:** `feat/phase17-product-ux-and-pdf-fidelity`  
**Date:** 2026-05-29  
**Sample:** Kitchen A assembly (6 parts, sink cutout, mixed edge treatments)

## Artifacts

| File | Description |
|------|-------------|
| [pdf-redesign-before.pdf](../artifacts/pdf-redesign-before.pdf) | Pre-Phase 17 layout (831c06c exporter) |
| [pdf-redesign-after.pdf](../artifacts/pdf-redesign-after.pdf) | Phase 17 drawing-first layout |
| [before-assembly.png](../artifacts/pdf-redesign-screenshots/before-assembly-3.png) | Assembly sheet screenshot - before |
| [after-assembly.png](../artifacts/pdf-redesign-screenshots/after-assembly-3.png) | Assembly sheet screenshot - after |

## Layout comparison

### Before (text-first)

- **61% drawing / 36% notes column** - side schedule consumed horizontal space.
- Verbose edge blocks: `BACK: POLISHED`, `FRONT: POLISHED`, etc.
- Drawing zone felt like a schematic inset; metadata competed with geometry.
- Title block and schedules stacked in the right column.

### After (drawing-first)

- **Horizontal title strip:** Project | Unit | Material | Qty | Rev | Sheet
- **~65-70% full-width drawing canvas** - no side notes column on assembly sheets.
- **Compact fab table:** `PART | SIZE | EDGE | CUTOUT | SQFT` with codes like `B=P F=P L=R R=P`.
- **Single-line shop notes** at bottom instead of multi-block schedules.
- Drawing scale cap raised from 6 to **8 pts/inch** in `FabricationDrawingEngine`.

## Fabrication critique

### Improvements

1. **Visual hierarchy** - operator eye lands on part geometry first; tables are secondary reference.
2. **Edge density** - one row per part replaces four-line edge schedule blocks.
3. **Page real estate** - landscape sheet used for fabrication, not admin reporting.
4. **Title strip** - shop-relevant fields in one scan line.

### Remaining gaps

1. **Inline geometry labels** - sink/faucet/cutout callouts still partially table-dependent; next pass should push more labels into the vector layer.
2. **Grain arrows and corner radius** - engine supports some notation; not yet on every part type in sample.
3. **Multi-part sheet** - complex assemblies with many small splashes still need legibility tuning at 8 pts/inch cap.
4. **Cover/TOC/summary pages** - still report-oriented; assembly sheets are the priority fix.

## Validation

- Backend: `85 passed` (sqlite in-memory, `USE_SQL_REPOSITORY=false`)
- Sample PDF script: `backend/scripts/generate_pdf_redesign_sample.py`
- Unit test: `tests/test_pdf_layout_phase17.py` (compact edge codes)

## Recommendation

Ship Phase 17 assembly layout to production packages. Schedule Phase 18 for geometry-embedded annotations (sink labels, grain arrows on all parts) and cover-sheet slimming.
