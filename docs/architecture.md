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
    island            → stub (future)
    vanity            → stub (future)
    straight_kitchen  → stub (future)
    l_kitchen         → stub (future)

## Geometry Builder (`services/geometry_builder.py`)

Converts ResolvedDimensions → GeometryModel + geometry primitives.

```
TemplateResolver → ResolvedDimensions
                        ↓
                GeometryBuilder
                        ↓
            GeometryBuildResult
                ├── GeometryModel   (status=computed, pieces=[...])
                ├── List[Rectangle]
                ├── List[DimensionLine]
                └── List[TextAnnotation]
```

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





