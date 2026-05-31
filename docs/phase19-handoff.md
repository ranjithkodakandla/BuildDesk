# Phase 19 — Handoff Document
## PDF Visual Overhaul + Remaining UX Gaps

> **Purpose:** This document gives a new AI session everything needed to continue
> work on BuildDesk without any context from the previous session.
> Read this before touching any code.

---

## 1. Project context in one paragraph

BuildDesk is a multifamily countertop fabrication package generator used by
fabricators, installers, and designers. Users import a unit schedule (apartment
numbers + stone types), attach shop drawings (assemblies with parts, edges,
cutouts, splashes), then generate a multi-page fabrication PDF that goes to the
shop floor. The PDF is the primary deliverable — it must look like a professional
shop drawing, not a software report.

**Reference PDFs are located at:**
```
/Users/ranjithkodakandla/Downloads/Virgin Surfaces/Virgin Surfaces - Project/PDF/
  BULL OUTDOOR Splashes (3 sides Polish) (1).pdf   ← multi-unit kitchen, ITEM# style
  Deforest Yards Bldg I Drawings.pdf               ← fractional dims, CAD black/white
  Concord North drawings (1).pdf                   ← dual in[mm], Virgin Surfaces logo
  Haven Pdf Drawings (1).pdf                       ← single-unit per page, ADA tops
```

Study these before changing any drawing code. They are the acceptance criteria.

---

## 2. Current test baseline (must stay green)

```bash
cd /Users/ranjithkodakandla/Downloads/Virgin\ Surfaces/project/buildesk/BuildDesk/backend
.venv/bin/python -m pytest tests/ -q
# Expected: 85 passed
```

```bash
cd /Users/ranjithkodakandla/Downloads/Virgin\ Surfaces/project/buildesk/BuildDesk/frontend
npm run build
# Expected: 0 TypeScript errors, 107 modules
```

Run these before and after every change. Do not proceed if either fails.

---

## 3. What is done (do NOT redo these)

### Drawing engine (`fabrication_drawing_engine.py`)
- ✅ Two-zone layout: BS pieces in top zone, main tops in bottom zone
- ✅ Width-matched BS alignment above parent tops
- ✅ L-shape detection + L-CORNER annotation
- ✅ 4 dimension styles: DIM_INCH_MM / DIM_FRAC / DIM_LONG_MM / DIM_DECIMAL
- ✅ `fmt_dim(value, style)` used everywhere including cutout dims
- ✅ Scale cap 12.0 + vertical centering
- ✅ Seam lines only between adjacent main tops

### Package PDF (`package_pdf_exporter.py`)
- ✅ Compact fab table REMOVED from assembly pages
- ✅ Drawing zone expanded ~85 pts (full body, no table below)
- ✅ Unit list at bottom: `UNITS: 101, 201, 301 …`
- ✅ `_infer_dim_style(project)` auto-selects from material string

### Frontend
- ✅ Tab renames, step numbers, job checklist on Overview
- ✅ Unassigned units at top with quick-assign dropdown
- ✅ Bigger unit chips, always-visible tools sidebar
- ✅ "Generate PDF" hero button when all steps complete

---

## 4. What still needs to be done

### Priority 1 — PDF Visual Overhaul (makes the PDF look like a real shop drawing)

This is the most impactful change. Every reference PDF is black-and-white,
clean line drawings. BuildDesk output currently has:
- Blue-grey fill on every stone piece
- Colored edge lines (blue eased, orange miter, green finished)
- Blue dimension lines
- Tick marks on dimensions instead of arrowheads

**File to change:** `backend/app/exporters/fabrication_drawing_engine.py`

#### 4.1 Remove color fill — use white for all stone pieces

**Find these constants (around line 50-70):**
```python
_C_PART_FILL   = HexColor("#f0f4f8")   # change to white
_C_SPLASH_FILL = HexColor("#e8f4fd")   # change to white
_C_DIM         = HexColor("#4a7fb5")   # change to dark
_C_EASED       = HexColor("#4a7fb5")   # change to dark
_C_MITER       = HexColor("#e67e22")   # change to dark
_C_FINISHED    = HexColor("#2ecc71")   # change to dark
_C_SPLASH_STR  = HexColor("#2980b9")   # change to dark
```

**Change to:**
```python
_C_PART_FILL   = HexColor("#ffffff")   # white — matches reference
_C_SPLASH_FILL = HexColor("#f5f5f5")   # very light grey for BS pieces
_C_DIM         = HexColor("#333333")   # dark grey for dimension lines
_C_EASED       = HexColor("#444444")   # dark — use line weight, not color
_C_MITER       = HexColor("#444444")   # dark — miter shown by dash pattern
_C_FINISHED    = HexColor("#444444")   # dark
_C_SPLASH_STR  = HexColor("#444444")   # dark
```

Keep `_C_CUTOUT_STR = HexColor("#c0392b")` red — the red dashed sink outline
IS in the references (Deforest/Concord show it red). Keep `_C_SEAM` red.
Keep `_C_HOLE = HexColor("#8e44ad")` purple.

#### 4.2 Replace tick marks with proper arrowheads on dimension lines

**Find `_dim_line_h()` and `_dim_line_v()` methods** (around line 635-648):

Current code draws tick marks (short perpendicular lines at dimension ends).
Replace with open arrowheads pointing inward, matching CAD convention:

```python
def _dim_line_h(self, c: rl_canvas.Canvas, x: float, y: float, length: float):
    """Horizontal dimension line with inward arrowheads at both ends."""
    c.setLineWidth(0.75)
    c.line(x, y, x + length, y)
    # Left arrowhead (pointing right, into the dimension)
    self._arrowhead(c, x, y, direction='right')
    # Right arrowhead (pointing left, into the dimension)
    self._arrowhead(c, x + length, y, direction='left')

def _dim_line_v(self, c: rl_canvas.Canvas, x: float, y: float, height: float):
    """Vertical dimension line with inward arrowheads at both ends."""
    c.setLineWidth(0.75)
    c.line(x, y, x, y + height)
    # Bottom arrowhead (pointing up)
    self._arrowhead(c, x, y, direction='up')
    # Top arrowhead (pointing down)
    self._arrowhead(c, x, y + height, direction='down')

def _arrowhead(self, c: rl_canvas.Canvas, x: float, y: float, direction: str):
    """Draw a small open arrowhead at (x,y) pointing in the given direction.
    Size: 6pt long, 3pt wide — matches CAD shop drawing convention."""
    L, W = 6.0, 3.0
    if direction == 'right':
        c.line(x, y, x - L, y + W)
        c.line(x, y, x - L, y - W)
    elif direction == 'left':
        c.line(x, y, x + L, y + W)
        c.line(x, y, x + L, y - W)
    elif direction == 'up':
        c.line(x, y, x - W, y - L)
        c.line(x, y, x + W, y - L)
    elif direction == 'down':
        c.line(x, y, x - W, y + L)
        c.line(x, y, x + W, y + L)
```

Add `_arrowhead()` as a new method on `FabricationDrawingEngine`.

#### 4.3 Add real scale calculation and notation

**In `_draw_dimensions()` and in `package_pdf_exporter.py`:**

Currently the PDF shows `Scale: NTS`. Fabricators expect an actual scale like
`1/2" = 1'-0"` or `3/4" = 1'-0"`.

The scale in points-per-inch is already computed. Convert it to a rational scale:

```python
def _format_scale_ratio(pts_per_inch: float) -> str:
    """Convert pts/inch scale to paper ratio string.
    ReportLab uses 72 pts per printed inch.
    So pts_per_inch / 72 = paper_inches_per_model_inch.
    Express as N/M" = 1'-0"
    """
    paper_per_model = pts_per_inch / 72.0   # paper inches per model inch
    # paper_per_model * 12 = paper inches per model foot
    paper_per_foot = paper_per_model * 12.0
    # Round to nearest common scale
    common = [0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    closest = min(common, key=lambda x: abs(x - paper_per_foot))
    # Format as fraction
    frac_map = {0.125: '1/8"', 0.25: '1/4"', 0.375: '3/8"',
                0.5: '1/2"', 0.75: '3/4"', 1.0: '1"',
                1.5: '1 1/2"', 2.0: '2"', 3.0: '3"'}
    return f"{frac_map.get(closest, f'{closest}')} = 1'-0\""
```

Add this as a module-level function in `fabrication_drawing_engine.py`.

Return `scale` from `_compute_layout()` and `_compute_shop_sheet_layout()`, then
pass it to the scale notation line in `package_pdf_exporter.py`:

In `_draw_assembly_page()`, change:
```python
c.drawString(draw_x, draw_bot - 6, f"Scale: NTS  |  {dim_style_label(dim_style)}")
```
To:
```python
scale_str = _format_scale_ratio(layout_scale)  # need to expose scale from draw_assembly
c.drawString(draw_x, draw_bot - 6, f"Scale: {scale_str}  |  {dim_style_label(dim_style)}")
```

To expose the scale, have `draw_assembly()` return a tuple `(height, scale)` or
store it on the engine instance (`self._last_scale`).

#### 4.4 Make the piece number large and un-filled

In `_draw_part_outline()`, the piece number currently has a grey fill swatch
behind it. In the references the number is simply a large, lightly grey number
inside the white piece. No fill swatch needed.

Change:
```python
# current
c.setFillColor(HexColor("#cccccc"))
c.setFont("Helvetica-Bold", min(28 if not is_splash else 14, ph * 0.5))
c.drawCentredString(x + pw / 2, y + ph / 2 - num_font * 0.35, str(piece_num))
```

The piece number should be larger and bolder. Use a lighter colour so it doesn't
dominate the drawing but is clearly readable:
```python
c.setFillColor(HexColor("#bbbbbb"))   # light grey, not white
font_sz = min(36 if not is_splash else 16, ph * 0.6, pw * 0.4)
c.setFont("Helvetica-Bold", font_sz)
c.drawCentredString(x + pw / 2, y + ph / 2 - font_sz * 0.3, str(piece_num))
```

---

### Priority 2 — Inline Piece Editor in Shop Drawings tab

**Context:** There is currently no way to create or edit fabrication data
(dimensions, edge treatments, sink cutouts) through the UI. All data must come
from the API or import. This is the biggest functional gap blocking non-technical
fabricator adoption.

**File to change:** `frontend/src/components/AssembliesPanel.tsx`
**File to check first:** `frontend/src/components/AssemblyEditor.tsx`
  (existing editor — understand what it currently does before adding)

**What is needed:**
1. When a user selects an assembly, show an inline form:
   - Assembly name and type (editable)
   - A list of parts, each with:
     - Length (inches) — number input
     - Depth (inches) — number input
     - Thickness (inches) — number input
     - Edge treatments: for each side (Front/Back/Left/Right), select from
       [Polished, Eased, Miter, Raw, Finished]
     - Sink cutout: checkbox → if checked: model name, width, depth, center_x, center_y
     - Backsplash: checkbox → if checked: height (default 4")
   - Add Part button (adds a new blank part row)
   - Delete Part button per row
   - Save button → calls `PATCH /api/v1/assemblies/{id}` (check API for exact route)
2. After save, trigger SVG preview refresh

**API routes to use:**
```
GET  /api/v1/assemblies/{assembly_id}          → returns Assembly with parts
PUT  /api/v1/assemblies/{assembly_id}/parts    → replaces parts list
POST /api/v1/assemblies/{assembly_id}/parts    → add one part
```
Check `backend/app/api/fabrication.py` for exact route signatures before writing.

---

### Priority 3 — Per-project dimension style setting

**Context:** Currently `_infer_dim_style(project)` auto-selects from material
string which is fragile. Users should be able to set this explicitly per project.

**Backend change:**
In `backend/app/db/models.py`, add a `dim_style` column to `ProjectRecord`:
```python
dim_style = Column(String(20), nullable=False, default="inch_mm")
```
Create an Alembic migration for this.

In `backend/app/api/hierarchy.py` (or wherever `ProjectRecord` is updated),
expose `dim_style` in the Project schema and allow it to be set on create/update.

**Frontend change:**
In `DashboardPage.tsx` new project modal, add a select for dimension style:
```
Dimension Format:
  ○ inch [mm]    — 28.5" [724]   (default)
  ○ Fractional   — 28 1/2"
  ○ Long mm      — 28.5 in [724 mm]
  ○ Decimal      — 28.5"
```

In `package_pdf_exporter.py`, change:
```python
_dim_style = self._infer_dim_style(project)
```
To:
```python
_dim_style = getattr(project, 'dim_style', None) or self._infer_dim_style(project)
```

---

## 5. Reference PDF key facts (needed for any drawing changes)

From studying all 4 reference PDF sets:

| Drawing element | Reference behaviour | Our current behaviour |
|---|---|---|
| Stone piece fill | **White / no fill** | Light blue-grey `#f0f4f8` |
| Edge line colour | **Black only**, weight = edge type | Coloured (blue, orange, green) |
| Dimension lines | **Black**, arrowheads at ends | Blue, tick marks |
| Polished mark | **⊗ or X** at midpoint of polished edge | X mark — correct |
| Piece number | **Large grey number** centred in piece | Grey number — correct |
| BS piece label | **Letter label** (A, B, C) outside piece | "BS" text inside — acceptable |
| Scale notation | **1/2" = 1'-0"** or similar | "NTS" — wrong |
| Key notes box | **Top-right of drawing area** | Top-right of inner zone — correct |
| Unit list | **"UNITS: 101, 201, 301"** at bottom | Implemented ✅ |
| Table of parts | **None** — no parts table | Removed ✅ |
| Vertical title block | **Right margin** with project/material/QTY | Implemented ✅ |

The most commercially damaging difference is the **colour fill + coloured lines**.
A fabricator who receives our PDF vs a Deforest-style PDF will immediately notice
ours looks like software output. Fixing this is the single highest-priority change.

---

## 6. Architecture reference

```
backend/
  app/
    exporters/
      fabrication_drawing_engine.py   ← ALL drawing primitives
        class FabricationDrawingEngine:
          draw_assembly(c, assembly, zone_x, zone_y, zone_w, zone_h, ...)
          _compute_layout(parts, zone_w, zone_h) → {scale, positions, total_height}
          _compute_shop_sheet_layout(parts, zone_w, zone_h) → same
          _draw_part_outline(c, part, x, y, pw, ph, label, piece_num)
          _draw_dimensions(c, part, x, y, pw, ph, scale, dim_style)
          _draw_cutouts(c, part, x, y, pw, ph, scale, dim_style)
          _draw_edge_treatments(c, part, x, y, pw, ph)
          _draw_splash_piece_edges(c, x, y, pw, ph)
          _dim_line_h(c, x, y, length)   ← ADD arrowheads here
          _dim_line_v(c, x, y, height)   ← ADD arrowheads here
        
        format_dimension_inch_mm(inches) → str
        format_dimension_frac(inches) → str
        format_dimension_long_mm(inches) → str
        fmt_dim(inches, style) → str       ← dispatcher
        DIM_INCH_MM / DIM_FRAC / DIM_LONG_MM / DIM_DECIMAL  (constants)

      package_pdf_exporter.py             ← multi-page PDF layout
        class PackagePdfExporter:
          export(project, package, tenant, unit_type_groups, assemblies_by_type, summary)
          _draw_assembly_page(c, project, group, assembly_type, assemblies, version, tenant, dim_style)
          _draw_unit_list_in_drawing(c, group, x, y, w)
          _draw_vertical_title_block(...)
          _infer_dim_style(project) → str

  models/
    fabrication.py    ← Assembly, Part, EdgeTreatment, Cutout, Hole, Splash
    hierarchy.py      ← Project, UnitType, Unit, UnitVariant
    project_package.py ← ProjectPackage, UnitTypeGroup, PackageSummary

frontend/src/
  pages/
    WorkspacePage.tsx     ← 5 tabs with step numbers
    DashboardPage.tsx     ← project/job list
  components/
    OverviewPanel.tsx     ← 3-step job checklist (HOME tab)
    HierarchyPanel.tsx    ← unit management (UNITS & TYPES tab)
    AssembliesPanel.tsx   ← shop drawings viewer (SHOP DRAWINGS tab)
    AssemblyEditor.tsx    ← existing assembly editor (check before adding)
    PackagesPanel.tsx     ← PDF generate/download (PDF PACKAGE tab)
```

---

## 7. How to generate a test PDF to verify drawing changes

```python
# Run from backend/ directory
cd /Users/ranjithkodakandla/Downloads/Virgin\ Surfaces/project/buildesk/BuildDesk/backend
.venv/bin/python - << 'EOF'
import io, uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from app.exporters.fabrication_drawing_engine import FabricationDrawingEngine, DIM_FRAC
from app.models.fabrication import (
    Assembly, AssemblyType, Cutout, CutoutType, Dimensions, EdgeTreatment,
    EdgeType, MountType, Part, PartType, Position, SplashType,
)
from app.models.hierarchy import UnitVariant

_PAGE = landscape(letter)
_W, _H = _PAGE
engine = FabricationDrawingEngine()
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=_PAGE)
aid = pid = tid = uuid.uuid4()

# Create a simple 2-piece kitchen + BS
p1id = uuid.uuid4()
p1 = Part(assembly_id=aid, part_type=PartType.MAIN_TOP, name="Piece 1 — Main Top",
          dimensions=Dimensions(length=28.5, depth=30.0, thickness=1.25),
          edges=[EdgeTreatment(part_id=p1id, position=Position.FRONT, edge_type=EdgeType.POLISHED),
                 EdgeTreatment(part_id=p1id, position=Position.LEFT, edge_type=EdgeType.POLISHED),
                 EdgeTreatment(part_id=p1id, position=Position.RIGHT, edge_type=EdgeType.RAW),
                 EdgeTreatment(part_id=p1id, position=Position.BACK, edge_type=EdgeType.RAW)])
p1.cutouts.append(Cutout(part_id=p1id, cutout_type=CutoutType.SINK,
    mount_type=MountType.UNDERMOUNT,
    dimensions=Dimensions(length=17.5, depth=14.0),
    center_x=14.25, center_y=15.0))

bs = Part(assembly_id=aid, part_type=PartType.LOOSE_PIECE, name="Piece 2 — Backsplash",
          dimensions=Dimensions(length=28.5, depth=4.0, thickness=1.25))

asm = Assembly(project_id=pid, tenant_id=tid, name="Kitchen Type A",
               assembly_type=AssemblyType.KITCHEN, variant=UnitVariant.STANDARD,
               parts=[p1, bs])

engine.draw_assembly(c, asm, 30, 30, _W - 60, _H - 80, dim_style=DIM_FRAC)
c.showPage()
c.save()
with open("/tmp/test_drawing.pdf", "wb") as f:
    f.write(buf.getvalue())
print("Generated: /tmp/test_drawing.pdf")
EOF
```

Then open: `open /tmp/test_drawing.pdf`

Compare against the reference PDFs. The piece fill should be white, lines black,
dimension lines should have arrowheads, scale should show as `1/2" = 1'-0"` etc.

---

## 8. Acceptance criteria for Priority 1 (PDF Visual Overhaul)

Before marking Priority 1 complete, check ALL of these:
- [ ] Stone piece background is **white** (no light blue-grey fill)
- [ ] BS pieces have a **very light grey** background (distinguishes from main tops)
- [ ] All dimension lines are **dark grey or black** (not blue)
- [ ] Edge line colours removed — polished is thick black, raw is thin dashed dark grey,
      eased/miter/finished are medium weight dark lines
- [ ] Dimension endpoints have **arrowheads** (open V shape, 6pt long), not tick marks
- [ ] A real scale like `3/4" = 1'-0"` appears below the drawing zone
- [ ] Cutout outline stays **red dashed** (this IS in the references)
- [ ] Hole circles stay **dark** (acceptable)
- [ ] X polished edge marks still visible
- [ ] Piece numbers large, light grey, centred inside piece
- [ ] All 85 backend tests still pass
- [ ] Generate a test PDF and compare visually to the Deforest PDF

---

## 9. Key constraints — do not violate

1. **Do not drop any existing test** — 85 tests must remain green
2. **Do not change the data model** (models/fabrication.py, models/hierarchy.py)
   without a corresponding Alembic migration
3. **Do not change the API routes or response shapes** — the frontend depends on them
4. **Do not redesign the frontend** — UX improvements only (tab names, layout, sizing)
5. **Do not add colour coding** back to edge treatments — references use line weight only
6. **Do not add a parts table back** below the drawing — no reference has one
