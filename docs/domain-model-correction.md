# BuildDesk — Domain Model Correction & Architecture Realignment

> **Status:** Architecture Decision Record — v1  
> **Supersedes:** All previous geometry-first roadmap documents  
> **Effective immediately** — no further roadmap expansion until Phase 3 is designed.

---

## The Core Problem

The current BuildDesk implementation solves the wrong problem.

| What we built | What the business needs |
|---|---|
| Generic shape generator | Multifamily countertop fabrication package |
| One shape → one PDF | Full project package → one PDF set |
| Rectangle / Island / Vanity stubs | Kitchen, Vanity, Island, Bar, Laundry, ADA assemblies |
| `project_id` as a flat UUID | Project → Building → Floor → Unit → Unit Type hierarchy |
| `GeometryPiece` (area, perimeter) | Part, Splash, Cutout, EdgeTreatment, Hole, FabricationNote |
| No concept of variants | MIR, ADA, LEFT/RIGHT, REV, custom derived types |
| PDF = one shape drawing | PDF = cover + type sheets + drawing pages + summary pages |

The infrastructure layer (FastAPI, PostgreSQL, JWT, Cloud Run) is correct. The **domain model is wrong** and must be corrected before any further feature work.

---

## A. Domain Model Proposal

### A.1 Project Hierarchy (Flexible / Optional)

```
Project
├── (optional) Building
│   ├── (optional) Floor
│   │   └── Unit / Flat
│   └── Unit / Flat          ← floor may be absent
└── Unit / Flat              ← building may be absent
```

All intermediate levels are optional. A project can be flat (`Project → Units`) or deeply nested (`Project → Building → Floor → Unit`). Controlled by `HierarchyConfig`.

```python
class Project:
    id: UUID
    tenant_id: UUID
    name: str                          # "Riverside Apartments Phase 2"
    client_name: str | None
    material: str | None               # "Calacatta Gold 3cm"
    issue_date: date | None
    hierarchy_config: HierarchyConfig  # controls which levels are active
    status: ProjectStatus              # draft | in_progress | issued | archived

class HierarchyConfig:
    has_buildings: bool = False
    has_floors: bool = False
    has_unit_types: bool = False

class Building:
    id: UUID
    project_id: UUID
    name: str                          # "Building A", "Tower 1"
    code: str | None                   # "A", "T1"
    sort_order: int

class Floor:
    id: UUID
    building_id: UUID
    project_id: UUID
    name: str                          # "Floor 2", "Level 3"
    number: int | None
    sort_order: int

class Unit:
    id: UUID
    project_id: UUID
    building_id: UUID | None           # null when no building level
    floor_id: UUID | None              # null when no floor level
    unit_type_id: UUID | None
    name: str                          # "Apt 201"
    code: str                          # "201"
    variant: UnitVariant | None        # MIR, ADA, etc.

class UnitType:
    id: UUID
    project_id: UUID
    code: str                          # "A", "B", "B1", "ADA"
    name: str                          # "Type A — 2BR/2BA"
    is_mirror: bool = False
    is_ada: bool = False
    base_type_id: UUID | None          # if derived (A-MIR from A)

class UnitVariant(str, Enum):
    STANDARD = "standard"
    MIRROR = "MIR"
    ADA = "ADA"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    REVERSED = "REV"
    CUSTOM = "custom"
```

### A.2 Countertop Assembly Model

Replace "shape" thinking with fabrication-aware "assembly" thinking.

An **Assembly** = complete countertop installation for one location (kitchen, vanity, etc.) in one unit. It has one or more **Parts**, each with cutouts, holes, splashes, edge treatments.

```python
class Assembly:
    id: UUID
    unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    assembly_type: AssemblyType        # KITCHEN, VANITY, ISLAND, BAR, LAUNDRY, ADA
    label: str                         # "Kitchen", "Master Bath Vanity"
    parts: list[Part]
    notes: list[FabricationNote]
    status: AssemblyStatus

class AssemblyType(str, Enum):
    KITCHEN = "kitchen"
    VANITY = "vanity"
    ISLAND = "island"
    BAR_TOP = "bar_top"
    LAUNDRY = "laundry"
    ADA = "ada"
    CUSTOM = "custom"

class Part:
    id: UUID
    assembly_id: UUID
    label: str                         # "A", "B", "LEFT PIECE"
    length: float                      # inches
    width: float                       # inches
    thickness: float                   # inches (default 3cm = 1.1811")
    area: float                        # computed: length × width
    edge_treatments: list[EdgeTreatment]
    cutouts: list[Cutout]
    holes: list[Hole]
    splashes: list[Splash]
    seams: list[Seam]
    notes: list[FabricationNote]
    sort_order: int

class Splash:
    id: UUID
    part_id: UUID
    splash_type: SplashType            # BACK, LEFT_SIDE, RIGHT_SIDE, FULL
    height: float                      # inches
    length: float                      # inches
    edge_treatment: EdgeTreatmentType

class SplashType(str, Enum):
    BACK = "back"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    WINDOW = "window"
    FULL = "full"

class Cutout:
    id: UUID
    part_id: UUID
    cutout_type: CutoutType            # SINK, COOKTOP, RANGE, CUSTOM
    label: str                         # "Undermount Sink", "5-Burner Cooktop"
    length: float
    width: float
    position_x: float                  # from left edge
    position_y: float                  # from front edge
    corner_radius: float | None
    notes: str | None

class CutoutType(str, Enum):
    SINK = "sink"
    COOKTOP = "cooktop"
    RANGE = "range"
    VESSEL = "vessel"
    CUSTOM = "custom"

class Hole:
    id: UUID
    part_id: UUID
    hole_type: HoleType                # FAUCET, SOAP, SPRAYER, AIR_SWITCH
    diameter: float                    # inches
    position_x: float
    position_y: float
    label: str | None

class HoleType(str, Enum):
    FAUCET = "faucet"
    SOAP = "soap"
    SPRAYER = "sprayer"
    AIR_SWITCH = "air_switch"
    CUSTOM = "custom"

class EdgeTreatment:
    id: UUID
    part_id: UUID
    edge: EdgePosition                 # FRONT, BACK, LEFT, RIGHT
    treatment: EdgeTreatmentType       # EASED, OGEE, BEVEL, RAW, MITER

class EdgePosition(str, Enum):
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"

class EdgeTreatmentType(str, Enum):
    EASED = "eased"
    DOUBLE_EASED = "double_eased"
    OGEE = "ogee"
    BEVEL = "bevel"
    MITER = "miter"
    RAW = "raw"
    FINISHED = "finished"

class Seam:
    id: UUID
    assembly_id: UUID
    seam_type: SeamType                # BUTT, MITER, WATERFALL
    position: float                    # inches from left/front
    orientation: str                   # "horizontal" | "vertical"
    connects_part_a: UUID
    connects_part_b: UUID

class FabricationNote:
    id: UUID
    parent_id: UUID                    # assembly_id or part_id
    parent_type: str                   # "assembly" | "part"
    note_type: NoteType
    text: str
    is_critical: bool = False
```

### A.3 ProjectPackage (The Critical Correction)

The downloadable PDF is NOT one shape → one PDF.  
It is a **ProjectPackage** — a complete fabrication drawing set.

```python
class ProjectPackage:
    id: UUID
    project_id: UUID
    tenant_id: UUID
    version: str                       # "1.0", "Rev A", "IFC"
    issued_by: str | None
    issued_date: date | None
    status: PackageStatus              # draft | IFR | IFC | revised
    pages: list[PackagePage]
    generated_at: datetime | None

class PackagePage:
    page_number: int
    page_type: PageType
    title: str
    content_ref: str

class PageType(str, Enum):
    COVER = "cover"
    TYPE_SHEET = "type_sheet"          # "Type A — Qty 8 — Units: 101,102..."
    ASSEMBLY_DRAWING = "assembly_drawing"
    SUMMARY = "summary"
```

---

## B. Architecture Correction Plan

### B.1 Layer Responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│                     HTTP API Layer                           │
│  /projects  /units  /assemblies  /packages  /auth  /health  │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│                   Domain Services                            │
│  HierarchyService   AssemblyService   PackageGeneratorService│
└───────┬──────────────┬───────────────┬───────────────────────┘
        │              │               │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────────────────────┐
│  Hierarchy   │ │ Assembly   │ │  Drawing Engine             │
│  Repos       │ │ Repos      │ │  (KEEP geometry primitives) │
└──────────────┘ └────────────┘ │  (KEEP SVG exporter core)   │
                                │  (NEW PackagePdfExporter)   │
                                └────────────────────────────┘
```

### B.2 Database Schema Corrections

**Add tables (Phase 1):**
`buildings`, `floors`, `units`, `unit_types`  
Extend `projects`: add `client_name`, `material`, `issue_date`, `hierarchy_config`, `status`

**Add tables (Phase 2):**
`assemblies`, `parts`, `splashes`, `cutouts`, `holes`, `edge_treatments`, `seams`, `fabrication_notes`

**Add tables (Phase 3):**
`project_packages`, `package_pages`

**Retain unchanged:**
`tenants`, `users`, `geometries` (legacy)

**All migrations are ADDITIVE ONLY — no drops, no column renames.**

### B.3 New API Endpoints

```
# Project Hierarchy
POST   /api/v1/projects
GET    /api/v1/projects/{id}
POST   /api/v1/projects/{id}/buildings
POST   /api/v1/projects/{id}/floors
POST   /api/v1/projects/{id}/units
POST   /api/v1/projects/{id}/unit-types

# Assembly
POST   /api/v1/projects/{id}/units/{unit_id}/assemblies
GET    /api/v1/assemblies/{id}
PATCH  /api/v1/assemblies/{id}
POST   /api/v1/assemblies/{id}/parts
POST   /api/v1/assemblies/{id}/parts/{part_id}/cutouts
POST   /api/v1/assemblies/{id}/parts/{part_id}/holes
POST   /api/v1/assemblies/{id}/parts/{part_id}/splashes
POST   /api/v1/assemblies/{id}/parts/{part_id}/edges

# Package Generation
POST   /api/v1/projects/{id}/package/generate
GET    /api/v1/projects/{id}/package/pdf
GET    /api/v1/assemblies/{id}/preview/svg
```

**Retained (backward compatible, marked deprecated):**
`GET /api/v1/health`, `POST /api/v1/auth/*`, `POST /api/v1/geometry`, `POST /api/v1/export/pdf`

---

## C. Migration Strategy

### Additive-First, Non-Destructive

> **Rule:** Never drop or modify existing table columns. Add new columns as nullable with defaults.

```
Phase 1 migration:
  → ALTER TABLE projects ADD COLUMN client_name, material, issue_date,
                                    hierarchy_config (JSON), status
  → CREATE TABLE buildings (...)
  → CREATE TABLE floors (...)
  → CREATE TABLE units (...)
  → CREATE TABLE unit_types (...)

Phase 2 migration:
  → CREATE TABLE assemblies, parts, splashes, cutouts,
                 holes, edge_treatments, seams, fabrication_notes

Phase 3 migration:
  → CREATE TABLE project_packages, package_pages

Phase 4 (future):
  → Mark geometries table as legacy in schema comments
  → No DROP until all consumers migrated
```

---

## D. Reusable vs Replaceable Subsystem Analysis

### ✅ KEEP — Fully Reusable

| Subsystem | Files | Reason |
|---|---|---|
| Geometry Primitives | `geometry/primitives.py` | `Point`, `Rectangle`, `Line`, `Circle`, `Polyline`, `DimensionLine`, `TextAnnotation` — exactly the right low-level building blocks for drawing engines |
| SVG Exporter core | `exporters/svg_exporter.py` | Primitive→SVG rendering is correct. Wrap for assembly-level previews. |
| PDF primitive renderer | `exporters/pdf_exporter.py` lines 87–205 | The primitive→PDF rendering section is reusable. Title block and page structure must change. |
| JWT Auth stack | `app/auth/` | Fully correct. Unchanged. |
| DB session + base | `app/db/` | Correct. Add tables only. |
| Repository pattern | `app/repositories/` | Correct pattern. Extend with new repos. |
| Tenant isolation | `app/auth/dependencies.py` | JWT-based scoping is correct. |
| FastAPI app factory | `app/main.py` | Correct. Add new routers. |

### ⚠️ WRAP — Extend Without Breaking

| Subsystem | Required Change |
|---|---|
| `GeometryBuilder` | Add `build_assembly(assembly, part)` dispatcher alongside existing shape handlers |
| `PdfExporter` | Keep for single-assembly preview. Add `PackagePdfExporter` for full multi-page package |
| `TemplateResolver` | Keep for backward compatibility. New path bypasses it (Assembly model is self-describing) |
| `ProjectRecord` | Add new columns via additive migration. No existing data broken. |

### ❌ REPLACE — Wrong Abstraction

| Subsystem | Problem | Replacement |
|---|---|---|
| `SHAPE_REGISTRY` / `shapes.py` | 5 hardcoded shapes is wrong primary model | `AssemblyTemplateRegistry` with default part configs per assembly type |
| `POST /api/v1/geometry` | Single shape as primary workflow | `POST /api/v1/.../assemblies` — deprecated but kept for compat |
| `POST /api/v1/export/pdf` | Single-shape PDF | `GET /api/v1/projects/{id}/package/pdf` — full package |
| `api/demo.py` | Misleading pre-canned shapes | Replace with real multifamily assembly examples |

---

## E. Recommended Implementation Order

### Phase 1 — Flexible Project Hierarchy (Target: 2–3 days)
1. Extend `ProjectRecord` ORM (additive columns)
2. Add `BuildingRecord`, `FloorRecord`, `UnitRecord`, `UnitTypeRecord`
3. Alembic migration (additive only — safe to run on live Cloud SQL)
4. `HierarchyService`: create/retrieve project trees
5. API: `POST /projects`, `POST /projects/{id}/buildings`, `POST /projects/{id}/units`
6. Tests: 10+ covering hierarchy creation, variant assignment
7. Docs: update architecture.md

### Phase 2 — Assembly & Fabrication Model (Target: 3–4 days)
1. Add ORM: `Assembly`, `Part`, `Cutout`, `Hole`, `Splash`, `EdgeTreatment`, `Seam`, `FabricationNote`
2. Alembic migration
3. `AssemblyService`: compute part areas, generate primitives via existing `GeometryBuilder`
4. API: `POST /assemblies`, `POST /assemblies/{id}/parts`, `POST /assemblies/{id}/parts/{id}/cutouts`
5. Assembly SVG preview (wrap existing `SvgExporter`)
6. Tests: create unit → kitchen assembly → 2 parts → sink cutout → verify

### Phase 3 — Project Package Generator (Target: 3–4 days)
1. `PackagePdfExporter` — multi-page ReportLab
   - Cover page: project name, client, material, issue date
   - Type sheets: per UnitType — qty, unit list
   - Assembly drawing pages: per assembly type per unit type
   - Summary: piece counts, sq ft, material quantities
2. `PackageGeneratorService`
3. API: `POST /projects/{id}/package/generate`, `GET /projects/{id}/package/pdf`
4. Tests: full project → package → verify page count and structure

### Phase 4 — Advanced Drawing Logic (Target: 4–5 days)
1. Cutout outlines (sink, cooktop) in SVG/PDF
2. Hole markers (faucet, soap)
3. Edge treatment indicators (line weight by treatment type)
4. Seam lines between parts
5. Backsplash/side splash in drawings
6. L-kitchen dimension handling
7. Part label system (A, B, C — fabrication convention)

### Phase 5 — UI Realignment (Target: 3–4 days)
1. Project creation wizard (name, client, material, hierarchy config)
2. Unit management UI (building/floor/unit tree)
3. Assembly builder (part dimensions, cutouts, edges)
4. Package download (replaces current SVG/PDF buttons)
5. Assembly preview (reuses current SVG viewer component)

---

## F. Concrete Workflow Examples

### Example 1: Simple Project (No Building/Floor)

```
Project: "Elm Street Condos"
  Material: Taj Mahal 3cm | Client: Apex Builders
  Hierarchy: Units only (has_buildings=false, has_floors=false)

Units:
  Unit 101 → Type A
  Unit 102 → Type A
  Unit 201 → Type A-MIR (mirror variant)
  Unit 202 → Type B

Type A Kitchen Assembly:
  Part A: 96" × 25.5"  — FRONT: eased, LEFT: raw
  Part B: 42" × 25.5"  — FRONT: eased, RIGHT: eased, LEFT: raw
  Seam: Butt at 96" from left
  Cutout: Undermount sink 32"×18", centered on Part A
  Holes: faucet @ (78", 5"), soap @ (88", 5")
  Splash: BACK — 4" × 138" (full length)
  Splash: LEFT_SIDE — 4" × 25.5"
  Note: "Verify sink template before cut"

Package PDF Pages:
  Page 1: Cover (project name, client, material, date)
  Page 2: Type A — Qty 2 (101, 102) — Kitchen
  Page 3: Type A — Qty 2 (101, 102) — Master Vanity
  Page 4: Type A-MIR — Qty 1 (201) — Kitchen (mirrored)
  Page 5: Type B — Qty 1 (202) — Kitchen
  Page 6: Summary (total pieces, sq ft, by type)
```

### Example 2: Large Multifamily (Full Hierarchy)

```
Project: "Riverside Towers Phase 2"
  Material: Calacatta Gold 3cm | Client: Sterling Development
  Hierarchy: Building → Floor → Unit → UnitType

Building A: Floors 2–8, 8 units/floor
Building B: Floors 2–6, 10 units/floor

Types: A, A-MIR, B, B1, ADA

Package PDF:
  Cover: Both buildings, total count (96 units)
  Type A: Qty 48 — unit list — Kitchen, Master Bath, Guest Bath drawings
  Type A-MIR: Qty 16 — mirrored drawings
  Type ADA: Qty 8 — lower height note — Kitchen + Vanity
  Type B: Qty 16 — Kitchen + Vanity
  Type B1: Qty 8 — variant note — Kitchen only
  Summary: 384 parts, 2,760 sq ft total material
```

### Example 3: Single Assembly Drawing Detail

```
Assembly: Master Bath Vanity — Type A
  Part A: 60" × 22"  (single piece)
    FRONT edge: eased (polished)
    LEFT edge: eased (polished)
    RIGHT edge: eased (polished)
    BACK edge: raw (against wall)
    Cutout: undermount sink 18"×14", centered at (21", 11")
    Hole: faucet 1.375" dia at (45", 8")
  Splash — BACK: 4" × 60"
  Splash — LEFT_SIDE: 4" × 22"
  Note (CRITICAL): "Verify sink template with plumber before cutting"

Drawing Page shows:
  ┌─────────────────────────────── 60" ──────────────────────────────────┐
  │                                                                       │
  │                    [SINK CUTOUT 18"×14"]           ○ faucet          │
  │                                                                       │ 22"
  │═══════════════════════════════════════════════════════════════════════│
  │ ← splash 60" × 4" ─────────────────────────────────────────────────  │
  └───────────────────────────────────────────────────────────────────────┘
```

---

## What Does NOT Change

- FastAPI, PostgreSQL, JWT, Cloud Run, ReportLab, React+Vite
- Geometry primitives (`Point`, `Rectangle`, `Line`, `Circle`, `Polyline`, `DimensionLine`)
- SVG exporter rendering core
- JWT auth stack
- Tenant isolation
- Repository pattern
- Zustand auth store + ProtectedRoute

## Blocked Until This Is Done

- asyncpg migration
- Frontend feature expansion beyond workspace
- Generic geometry demos
- Generic CRUD UI

## Immediate Next Action

> **Phase 1:** Implement flexible project hierarchy  
> Domain models → ORM → Migration → Service → API → Tests
