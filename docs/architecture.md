# BuildDesk Architecture

Platform architecture:

Frontend
- React
- Vite

Backend
- FastAPI
- Python

Core concepts:

1. Multi-tenant architecture

Every customer operates as a tenant.

Examples:

- Canyon Surfaces
- Builder A
- Builder B

2. Geometry Model

Geometry is the source of truth.

Drawings are outputs.

3. Shape Templates

Reusable parametric templates.

Example:

L Kitchen Template

Variables:
A
B
Depth
SinkOffset

4. Output Engines

Builder Package
Installer Package
Manufacturer Package

5. Shared Schema

Future compatibility with StoneDesk.

## Infrastructure Strategy

Initial deployment approach:

Platform will be deployed fully on GCP.

Technology stack:

* Frontend: React / Vite
* Backend: FastAPI
* Hosting: GCP Cloud Run
* Database: Cloud SQL (Postgres)
* File Storage: Cloud Storage
* Secrets: Secret Manager

Deployment philosophy:

* Single-cloud strategy (GCP-only)
* Simple operational model
* Demo-ready reliability
* Future SaaS scalability
* Supports multi-tenant architecture

Development approach:

Phase 1:

* Local development
* GitHub source control

Phase 2:

* Deploy backend to Cloud Run
* Add Cloud SQL

Phase 3:

* Add Cloud Storage for generated PDFs, uploads, and shape assets.

Long-term goals:

* Multi-tenant B2B SaaS support
* Customer domain / white-label readiness
* Future interoperability with StoneDesk ecosystem

## Domain Model Layer

Implemented as pure Pydantic models (no DB coupling in Phase 1).

### Model hierarchy

```
Tenant
└── Project
    └── GeometryModel (source of truth)
        ├── ShapeTemplate (parametric input)
        └── Package (output artifact)
```

### Model files

| File | Model | Purpose |
|---|---|---|
| models/tenant.py | Tenant | Top-level org; isolates all data |
| models/project.py | Project | Groups geometry instances per job |
| models/shape_template.py | ShapeTemplate | Reusable parametric shape definitions |
| models/geometry.py | GeometryModel | Concrete dimensions + computed outputs |
| models/package.py | Package | Builder / Installer / Manufacturer PDFs |

### Key design decisions

* All IDs are UUID4 (no auto-increment ints) — portable, non-guessable
* Geometry is the source of truth; packages are derived outputs
* ShapeTemplate.tenant_id = None → global system template
* schema_version on ShapeTemplate and GeometryModel enables future StoneDesk interoperability
* Package versioning: regeneration creates a new record (no mutation)

## Service Layer

Pure Python services — no HTTP, no DB, no side effects.

### Template Resolver (`services/template_resolver.py`)

Validates and normalises a raw dimension payload against a ShapeTemplate.

Input:
    ShapeTemplate + Dict[str, Any] (raw user payload)

Output:
    ResolvedDimensions
        has_errors: bool
        dimensions: Dict[str, Any]   ← ready for GeometryModel.dimensions
        errors: List[ParameterError] ← per-parameter failure messages

Validation rules applied:
    required     → error if missing and no default_value
    default      → substitute default_value when parameter is absent
    type coerce  → cast to declared parameter_type (number/string/boolean/select)
    min / max    → enforce bounds for number-type parameters
    options      → reject invalid values for select-type parameters
    multi-error  → all errors collected in one pass (no fail-fast)

### ShapeParameterType

Added to ShapeParameter in models/shape_template.py.

| Value   | Description                             |
|---|---|
| number  | Float dimension; supports min/max       |
| string  | Free-text annotation                    |
| boolean | Toggle flag (true/false)                |
| select  | One value from allowed_options list     |

## Base Model

`BaseDomainModel` (models/base.py) is the shared base for all domain entities.

Provides:
    created_at     – UTC creation timestamp
    updated_at     – UTC mutation timestamp
    schema_version – interoperability + migration safety
    touch()        – refresh updated_at to current UTC

All five domain models (Tenant, Project, ShapeTemplate, GeometryModel, Package)
inherit from BaseDomainModel.

## Geometry Primitive Layer

Pure Pydantic value objects (`geometry/primitives.py`).
No rendering, no SVG, no PDF — data only.

| Primitive       | Purpose                                              |
|---|---|
| Point           | 2-D coordinate (x, y); foundation for all others    |
| Line            | Segment between two Points; has `.length` property  |
| Rectangle       | Axis-aligned box; has `.area`, `.perimeter`, `.edges`, `.corners`, `.center` |
| Circle          | Centre + radius; has `.area`, `.circumference`       |
| Polyline        | Ordered Point sequence; closed flag; has `.segments`, `.total_length` |
| DimensionLine   | Annotated measurement callout between two Points    |
| TextAnnotation  | Free-text label anchored at a Point                 |

All primitives carry: UUID id, optional label, extensible metadata Dict.

## Shape Library

Seed templates (`geometry/shapes.py`) are system-level templates
(tenant_id=None) available to all tenants.

`SHAPE_REGISTRY` maps shape_type slug → ShapeTemplate instance.

MVP shapes:
    rectangle         → implemented
    island            → implemented
    vanity            → implemented
    straight_kitchen  → implemented
    l_kitchen         → implemented

## Geometry Builder (`services/geometry_builder.py`)

Converts ResolvedDimensions → GeometryModel + geometry primitives.

```
TemplateResolver → ResolvedDimensions
                        ↓
                GeometryBuilder
                        ↓
            GeometryBuildResult
                ├── GeometryModel   (status=computed, pieces=[...], metadata={})
                ├── List[Rectangle]  (bounding box)
                ├── List[Polyline]   (shape outlines — closed for island)
                ├── List[DimensionLine]
                ├── List[TextAnnotation]
                ├── List[Line]       (loose lines, optional)
                └── List[Circle]     (sink cutouts, optional)
```

### Island shape — design notes

- Island uses a **closed Polyline** outline (not a bare Rectangle) to signal
  "all four edges are exposed/finished".
- A bounding `Rectangle` primitive is also produced for area/viewbox calculations.
- 4 `DimensionLine`s are emitted — one per side — reflecting all-edge accessibility.
- `corner_radius` is carried in `GeometryModel.metadata` for future rounded-corner
  rendering by the PDF/SVG engine.

### Vanity shape & Construction Rules

- Represents the first shape with wall-mounting construction logic.
- The back edge sits flush against a wall. It is therefore omitted from the geometric outline (an **open Polyline** is used).
- This explicitly signals to output engines that edge-profiling or finishing should NOT be applied to the back edge.
- Emits exactly 3 `DimensionLine`s (left, right, front).
- Includes an optional `Circle` primitive if a `sink_cutout` is requested, triggering geometric validation (sink must fit within slab dimensions).
- `GeometryModel.metadata` records these construction details:
  ```json
  {
      "exposed_edges": ["front", "left", "right"],
      "wall_edge": "back",
      "has_backsplash": true
  }
  ```

### Straight Kitchen shape & Fabrication Rules

- Represents the first shape with multi-piece fabrication logic (seams).
- Like the vanity, the back edge sits flush against a wall (open `Polyline`).
- Includes a greedy algorithm that automatically splits long runs (e.g. 180") into multiple `GeometryPiece` instances based on a `slab_max_length` (e.g. 120" max → 120" + 60" pieces).
- Produces multiple `Rectangle` primitives (one for each physical piece).
- Places a dashed `Line` primitive to visually indicate the seam location.
- Emits specific `DimensionLine`s for each individual piece along the back edge, as well as an overall dimension along the front edge.
- Emits `seam_count` in the `GeometryModel.metadata` and assigns each piece a specific `piece_num`.

### L-Kitchen shape & Corner Join Rules

- Represents the first non-linear shape (L-shape layout).
- Emits an open `Polyline` for the layout perimeter, explicitly omitting the two back wall edges.
- Supports splitting the corner into multiple physical pieces (`GeometryPiece`s) using `corner_join_type` (`miter` or `butt`).
- `butt`: Creates two rectangles; Leg A owns the corner, Leg B butts into it.
- `miter`: Bounding boxes for pieces overlap in the corner to represent a 45-degree cut, and a diagonal seam line is drawn.
- Includes `corner_join_type` and `corner_count` in `GeometryModel.metadata`.

Shape dispatch:
- `_DISPATCH` dict maps shape_type slug → handler method
- Handler selected by inspecting template name / metadata / category
- Adding a new shape = write handler + add to `_DISPATCH`

Exceptions:
    GeometryBuildError    – generic build failure (e.g. error result passed in)
    UnsupportedShapeError – no handler registered for shape_type

## REST API Layer v1

All routes under `/api/v1`. No authentication in Phase 1.

### Endpoint table

| Method | Path | Purpose | Success | Errors |
|---|---|---|---|---|
| GET | `/api/v1/health` | Liveness probe | 200 | — |
| GET | `/api/v1/shapes` | List shape templates | 200 | — |
| GET | `/api/v1/shapes/{shape_type}` | Template + parameter schema | 200 | 404 |
| POST | `/api/v1/geometry` | Full geometry pipeline | 200 | 404, 422, 400 |

### API Schema separation

HTTP contracts (`api/schemas.py`) are kept strictly separate from
internal domain models (`models/`). Routers translate between the two layers.

    GeometryRequest      → TemplateResolver → GeometryBuilder → GeometryResponse
    ShapeTemplateResponse ← ShapeTemplate (domain model)
    ValidationErrorResponse → 422 domain validation errors (not FastAPI's built-in 422)

### HTTP status codes

| Code | Meaning in BuildDesk |
|---|---|
| 200 | Success |
| 400 | Shape type exists in registry but handler not yet implemented |
| 404 | Shape type not found in SHAPE_REGISTRY |
| 422 | Domain validation error — missing required param, out-of-range, invalid option |

## SVG Export Layer (`exporters/svg_exporter.py`)

Converts a GeometryBuildResult into a self-contained SVG string.

```
GeometryBuildResult
        ↓
    SvgExporter
        ↓
    SVG string   ← POST /api/v1/export/svg response body
```

### Coordinate mapping

Geometry system: origin bottom-left, y-up.
SVG system: origin top-left, y-down.
Mapping: `svg_y = svg_height - margin - geometry_y × scale`

### Primitive → SVG element mapping

| Primitive       | SVG element           | Style |
|---|---|---|
| Rectangle       | `<rect>`              | fill #f0f4f8, stroke #1a2332 |
| Line            | `<line>`              | stroke #1a2332 |
| Circle          | `<circle>`            | no fill, dashed stroke |
| Polyline        | `<polyline>` / `<polygon>` | depends on closed flag |
| DimensionLine   | `<line>` × 3 + `<text>` | stroke #4a7fb5, arrowhead markers |
| TextAnnotation  | `<text>`              | fill #2d5f8a |

### Export endpoint

| Method | Path | Response |
|---|---|---|
| POST | `/api/v1/export/svg` | `image/svg+xml` |

Same request body as `POST /geometry`.
Errors: 404 (unknown shape), 422 (validation), 400 (unimplemented).

Query param `?download=true` switches `Content-Disposition` from `inline` to `attachment`.

## Demo Workflow (`api/demo.py`, `tools/generate_demo_svg.py`)

Frictionless demo paths — no request body or server required.

### Three demo paths

| Path | Method | Description |
|---|---|---|
| Browser URL | `GET /api/v1/demo/rectangle` | Opens SVG directly in browser |
| Browser URL | `GET /api/v1/demo/island` | Opens SVG directly in browser |
| CLI tool | `python tools/generate_demo_svg.py all` | Writes SVG files to `tests/output/` |

### Demo payloads (hardcoded)

| Shape | length | width | extras |
|---|---|---|---|
| rectangle | 96" | 26" | thickness=0.75", label="Standard Countertop" |
| island | 72" | 36" | thickness=0.75", corner_radius=2.0", label="Kitchen Island" |

### Demo endpoint response headers

    Content-Type:        image/svg+xml
    Content-Disposition: inline; filename="demo-<shape>.svg"
    Cache-Control:       no-store
    X-BuildDesk-Demo:    true

### CLI tool usage

    python tools/generate_demo_svg.py rectangle          # single shape
    python tools/generate_demo_svg.py island             # single shape
    python tools/generate_demo_svg.py all                # all shapes (default)
    python tools/generate_demo_svg.py all --open         # open in browser
    python tools/generate_demo_svg.py all --scale 6.0   # larger SVG
    python tools/generate_demo_svg.py all --out-dir /tmp # custom output dir






