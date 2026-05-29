# Reference PDF Validation — BULL OUTDOOR Splashes (3 sides Polish)

**Branch:** `feat/reference-pdf-validation` (from `canonical-phase16`)  
**Date:** 2026-05-29  
**Reference:** `artifacts/reference-pdf/BULL_OUTDOOR_Splashes_3sides_Polish.pdf` (6 pages; primary sheet **100-01** Colonial White)  
**BuildDesk output:** `artifacts/reference-validation/builddesk_bull_outdoor_100-01.pdf`  
**Verdict:** **NO-GO** for Virgin Surfaces / Canyon-style fabrication sheet parity

---

## Executive summary

BuildDesk can **name** a Bull Outdoor project, hold **45 units**, store **six rectangular parts** with correct **inch dimensions in text**, and emit a **multi-page PDF package**. It does **not** produce a shop drawing meaningfully similar to the Virgin Surfaces reference: no combined layout sheet, no dual inch/mm dimensions, no symbol legend, no grain arrows, no sink geometry, no R-radius / break-corner notation, and **production cannot persist edges or cutouts** (HTTP 500).

---

## STEP 1 — REFERENCE ANALYSIS

Source inspected: all 6 pages rendered to `artifacts/reference-pdf/page-*.png`. Sheet **100-01** (page 1) is the validation target for Colonial White / BULL OUTDOOR.

### PROJECT STRUCTURE

| Finding | Example from PDF |
|--------|-------------------|
| Community / job name in header | **Boca Grande** (top left) |
| Program name in title block | **BULL OUTDOOR** |
| Item / order id | **ITEM # 16360** |
| Sheet id | **100-01** (pages 100-02 … 100-06 for other materials) |
| Quantity at sheet level | **QTY=45** |
| Drawn by / date | Arun · **08/20/2025** |
| Multi-page set per material variant | Colonial White, Fantasy Brown, Bonita, etc. |

### MATERIAL MODEL

| Finding | Example |
|--------|---------|
| Named stone + thickness | **3CM Colonial White** / **3CM GRANITE** |
| Material repeated in vertical title strip | “3CM Colonial White” on right margin |
| Global note | “ALL 3CM GRANITE” |

### ASSEMBLY MODEL

| Finding | Example |
|--------|---------|
| One layout sheet = one unit-type “kit” of pieces | 6 numbered pieces on one landscape sheet |
| Pieces 1–3 = tops/returns; 4–6 = splash strips | Piece 1 sink top; 2 wing; 3 main top; 4–6 splashes |
| “3 sides polish” on splashes | Top + both sides polished; bottom raw |

### PIECE MODEL

| Piece | Dimensions (in, with [mm]) | Notes |
|-------|---------------------------|--------|
| 1 | 28.5 [724] × 30.0 [762] | Top-mount sink 17.5×17.5; inset 5.5; R1/8 on sink corners; R1/2 on outer corners |
| 2 | 31 [787] × 9 [229] | Grain arrow; R1/2 bottom-left |
| 3 | 40.5 [1029] × 30.0 [762] | “Polished all outside edges”; grain arrow |
| 4 | 28.5 × **4** | Splash; break corners; 3-side polish |
| 5 | 31 × **4** | Splash |
| 6 | 40.5 × **4** | Splash |

### DRAWING MODEL

| Finding | Example |
|--------|---------|
| Plan-view rectangles, true scale layout on one sheet | All 6 pieces positioned spatially |
| Extension dimensions inch + mm | `28.5" [724]` |
| Piece numbers inside geometry | Large **1** … **6** |
| Leader notes | “Polished all out side edges”, “Break Corners”, “Top mount Sink” |
| Seam/join implied by adjacency | L-shaped top assembly + separate splashes above |

### TITLE BLOCK MODEL

| Finding | Example |
|--------|---------|
| Virgin Surfaces logo + Hyderabad / US contact | Right vertical band |
| Project, material, order #, date, revision table | MAIN TOP ORDER# · REVISIONS grid |
| Page label | **100-01** bottom right |

### LEGEND MODEL

**GRANITE/QUARTZ KEY NOTES** (top right):

| Symbol | Meaning |
|--------|---------|
| X | 3MM ROUND |
| F | FLAT EDGE (STOVE POLISH) |
| BS | BACK SPLASH |
| SS | SIDE SPLASH |
| TR | 1/8" RADIUS |
| RAW | RAW EDGE |
| □ on dimension | OVERSIZED PART |

Note: “ALL PARTS MADE TO SIZE UNLESS NOTED WITH A 'RECTANGLE' ON THE DIMENSION”

### SHOP NOTE MODEL

- Polished all outside edges (leader to edges)
- Break corners (splash pieces)
- Grain: horizontal double-arrow on pieces 1–3
- Sink: top mount, dimensioned cutout

### EDGE MODEL

- **X** tick on polished edges (3 mm round)
- **RAW** bottom edge on splash strips (unmarked bottom = raw)
- Stove polish **F** defined but not used on this sheet

### CORNER MODEL

- **R1/2** radius callouts with leaders
- **R1/8** on sink cutout corners
- **Break Corners** text (not radius arc)

### CUTOUT MODEL

- Labeled **Top mount Sink**
- 17.5 × 17.5 with 5.5 offsets from edges

### GRAIN MODEL

- Double-headed arrow (horizontal) on pieces 1–3

### QTY MODEL

- Sheet header **QTY=45** (sets per layout)

---

## STEP 2 — CAPABILITY GAP ANALYSIS (Phase 16)

| Domain area | vs reference | Rating |
|-------------|--------------|--------|
| Project metadata (name, client, material, item) | Fields exist; not title-block layout | **PARTIAL** |
| Quantities (45 units) | Bulk units OK; sheet QTY=45 not on drawing | **PARTIAL** |
| Materials (3CM Colonial White) | `project.material` string only | **PARTIAL** |
| Unit grouping | Unit types + 45 units | **MATCH** |
| Assemblies | One assembly per type; not per sheet layout | **PARTIAL** |
| Parts (6 rectangles) | Dimensions in data; 6 parts in PDF | **PARTIAL** |
| Edge schedules (X, RAW, 3-side polish) | Model exists; **live API 500 on save** | **MISSING** (prod) |
| Splash representation | Named strips; not BS/SS legend symbols | **PARTIAL** |
| Grain arrows | Not rendered | **MISSING** |
| Polished vs raw edges | Generic thick/dashed lines only | **PARTIAL** |
| Corner breaking / R1/2 / R1/8 | Not in drawing engine | **MISSING** |
| Sink cutouts | **API 500**; no cutout in output | **MISSING** |
| Title block fidelity | BuildDesk header/footer, not Virgin strip | **MISSING** |
| Legends | None on output | **MISSING** |
| Drawing layout (single sheet, 6 pieces) | One assembly per PDF page, schematic grid | **MISSING** |
| Dual inch/mm dimensions | Inch only on BuildDesk | **MISSING** |
| PDF structure | 5-page package (cover, index, type, drawing) | **PARTIAL** |
| Downloads | Auth blob download works (after frontend fix) | **MATCH** |
| Branding | Tenant company name in header | **PARTIAL** |
| Revision handling | Version 100-01 stored | **PARTIAL** |

---

## STEP 3 — REALISTIC SAMPLE DATASET

Script: `backend/scripts/seed_bull_outdoor_reference.py`

| Field | Value |
|-------|--------|
| Project | BULL OUTDOOR |
| Client | Boca Grande |
| Material | 3CM Colonial White Granite |
| Address / item | ITEM # 16360 |
| Units | 45 × type BO-100-01 |
| Assembly | 6 parts with reference dimensions in names |
| Package rev | 100-01 |

**Limitation:** Live API returns **500** when POSTing assemblies with `edges` or `cutouts`. Dataset uses bare parts + fabrication notes encoding edge/sink/grain intent.

**Manifest (credentials for visible replay):**  
`artifacts/reference-validation/reference_seed_manifest.json`

---

## STEP 4 — VISIBLE WORKFLOW (operator)

### Automated replay (browser visible — `--headed`)

```bash
cd frontend
# From reference_seed_manifest.json:
export REF_VALIDATION_EMAIL="bull_ref_…@builddesk.accept"
export REF_VALIDATION_PASSWORD="BullOutdoorRef123!"
export REF_VALIDATION_TENANT="55f00f83-…"
export REF_VALIDATION_PROJECT_ID="490d4de4-…"
export FRONTEND_URL="https://builddesk-web-149130710868.us-central1.run.app"

npx playwright test e2e/reference-bull-outdoor-headed.spec.ts --headed --workers=1
```

`playwright.config.ts` sets `headless: false`, `slowMo: 400`, video/trace on.

### Manual checklist

1. Login with manifest tenant/email/password  
2. Open `frontend_workspace_url` from manifest  
3. Assemblies → confirm 6 part names  
4. Edit assembly → SVG preview (rectangles only; no sink)  
5. Packages → Download PDF  
6. Compare to `artifacts/reference-pdf/page-1.png`

**CSP note:** Cursor embedded preview may block scripts; use Chrome/Safari.

---

## STEP 5 — GENERATED OUTPUT

| Artifact | Path |
|----------|------|
| Reference PDF copy | `artifacts/reference-pdf/BULL_OUTDOOR_Splashes_3sides_Polish.pdf` |
| Reference renders | `artifacts/reference-pdf/page-1.png` … `page-6.png` |
| BuildDesk PDF | `artifacts/reference-validation/builddesk_bull_outdoor_100-01.pdf` |
| BuildDesk renders | `artifacts/reference-validation/builddesk-page-*.png` |
| GCS | `gs://builddesk-artifacts-stonedesk-app/projects/…/packages/….pdf` |
| Generation time | ~3.4 s |
| PDF size | 10,224 bytes (5 pages) |

---

## STEP 6 — SIDE-BY-SIDE VALIDATION

### Reference sheet 100-01 vs BuildDesk package (assembly page)

| Category | Reference | BuildDesk | Result |
|----------|-----------|-----------|--------|
| Single-sheet 6-piece layout | All pieces on one landscape sheet | One assembly page; schematic PART A–F grid | **FAIL** |
| Piece numbering | 1–6 inside drawings | PART A–F labels | **PARTIAL** |
| Dimensions | Inch + mm brackets | Inch on drawing; mm missing | **FAIL** |
| Sink cutout | Drawn 17.5×17.5 | Text in notes only | **FAIL** |
| Edge symbols (X, RAW) | Legend + ticks on edges | Thick/thin lines; no X/RAW | **FAIL** |
| Corner R1/2, R1/8, break | Leaders + text | Notes only | **FAIL** |
| Grain arrows | On pieces 1–3 | Absent | **FAIL** |
| Legend block | GRANITE/QUARTZ KEY NOTES | Small line-style legend only | **FAIL** |
| Title block | Virgin vertical strip | BuildDesk blue header + footer | **FAIL** |
| QTY=45 on sheet | Prominent header | Cover/type pages only | **PARTIAL** |
| Material callout | 3CM Colonial White | In project + footer string | **PARTIAL** |
| Splash 3-side polish | Visual raw bottom edge | Described in notes | **PARTIAL** |
| Branding | Virgin Surfaces logo | Tenant name text | **PARTIAL** |
| Part area / sq ft | Implicit on reference | Cover shows **0 parts / 0 sq ft** (bug) | **FAIL** |

### Production defects found

1. **HTTP 500** on `POST /api/v1/assemblies` when `edges` or `cutouts` arrays are non-empty (blocks real fabrication authoring).  
2. **Cover summary** reports 0 parts / 0.0 sq ft despite 6 parts in assembly.  
3. **Frontend** `listAssemblies` must unwrap `{ assemblies, total }` (fixed on branch; deploy required for workspace crash).

---

## STEP 7 — PRIORITIZED BACKLOG (do not implement in this session)

### Critical

1. Fix production persistence for **edges, cutouts, holes, splashes** (500 on live API).  
2. Package summary metrics: **part count, sq ft** on cover.  
3. **Shop sheet layout**: multi-piece single page matching field layout (positions, not grid).  
4. **Sink/cutout drawing** with offsets and radius notation.  
5. **Legend + symbol language** (X, RAW, BS, SS, TR, F).  

### Important

6. Dual **inch + mm** dimensions.  
7. **Grain direction** arrows.  
8. **Corner** notation: R1/2, R1/8, break corners.  
9. **Virgin-style title block** (logo strip, revision table, sheet 100-xx).  
10. Sheet-level **QTY=** callout on drawing.  
11. Edge visualization matching legend (not generic thick line only).  

### Nice-to-have

12. Oversized-part rectangle on dimensions.  
13. Community vs program name fields (Boca Grande / BULL OUTDOOR).  
14. PDF page size / scale matching A4 landscape shop standard.  
15. Bulk authoring UI for 6-piece kits.  

---

## Pilot recommendation

| Verdict | **NO-GO** |
|---------|-----------|
| Rationale | Cannot model or print fabrication truth (edges, cutouts, legend, layout, notation) at reference fidelity; production data entry for edges/cutouts is broken. |

**Conditional path:** Fix Critical items 1–3, re-run this validation against sheet 100-01, then reassess.

---

## Artifacts index

```
artifacts/reference-pdf/
  BULL_OUTDOOR_Splashes_3sides_Polish.pdf
  page-1.png … page-6.png
artifacts/reference-validation/
  reference_seed_manifest.json
  builddesk_bull_outdoor_100-01.pdf
  builddesk-page-1.png … builddesk-page-5.png
backend/scripts/seed_bull_outdoor_reference.py
frontend/e2e/reference-bull-outdoor-headed.spec.ts
```
