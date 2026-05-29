# BuildDesk Architecture

> **ADR-001 Domain Guardrail is active.**
> Before implementing any feature, consult [`docs/domain-guardrail.md`](./domain-guardrail.md).
> BuildDesk is a **multifamily countertop fabrication package system** — not a geometry demo, not a CAD tool.
> Every feature must pass the domain test described in that document.

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

### Phase 1 & 2: Project & Fabrication Hierarchy

BuildDesk maps exactly to real-world countertop project structures:

```
Tenant
└── Project
    └── Building (optional)
        └── Floor (optional)
            ├── UnitType (e.g. Type A)
            └── Unit (e.g. Unit 101, variant=MIRROR)
                └── Assembly (e.g. Kitchen, Vanity)
                    ├── FabricationNote
                    └── Part (e.g. Main Top, Splash)
                        ├── EdgeTreatment (e.g. Front=Eased)
                        ├── Cutout (e.g. Sink=Undermount)
                        ├── Hole (e.g. Faucet=1.375")
                        └── Splash (e.g. Backsplash=4" tall)
```

**Key Assembly Concepts:**
* **Assembly**: A logical grouping of pieces (e.g. an entire L-Kitchen with its island).
* **Part**: A physical piece of stone.
* **Variant Logic**: Unit/Assembly variants (e.g., `MIRROR`, `ADA`) dictate downstream geometric transformations. Assemblies inherit variants from Units if left as standard.
* **Additivity**: Legacy single-shape geometry records (`GeometryModel`) coexist alongside the normalized Assembly structure during the transition phase.

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

## PDF Export Layer (`exporters/pdf_exporter.py`)

A production-style layout exporter leveraging `reportlab` to produce 8.5x11 landscape printable PDFs.

- Uses `GeometryBuildResult` directly to map primitives onto a PDF Canvas.
- Automatically calculates the bounding box of all geometric primitives, applies 10% padding, and sets the scale so the drawing fits perfectly within the margins.
- Injects a standard BuildDesk Title Block and metadata summary block into the layout.

### Export endpoint

| Method | Path | Response |
|---|---|---|
| POST | `/api/v1/export/pdf` | `application/pdf` |

Identical behavior and inputs to the SVG endpoint, but produces a formatted PDF document. Support for `?download=true` is included.

## Demo Workflow (`api/demo.py`, `tools/generate_demo_svg.py`)

Frictionless demo paths — no request body or server required.

### Demo paths

| Path | Method | Description |
|---|---|---|
| Browser URL | `GET /api/v1/demo/{shape}` | Opens SVG directly in browser |
| Browser URL | `GET /api/v1/demo/pdf/{shape}` | Opens printable PDF in browser |
| CLI tool | `python tools/generate_demo_svg.py all` | Writes SVG files to `tests/output/` |
| CLI tool | `python tools/generate_demo_pdf.py all` | Writes PDF files to `tests/output/` |

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







## Persistence Foundation

BuildDesk uses the **Repository Pattern** defined via Python `Protocol`s in `backend/app/repositories/`.

- `GeometryRepository`: Saves and retrieves full `GeometryResponse` payloads (which include the computed `GeometryModel` and all primitives).
- `ProjectRepository` and `TenantRepository`: Manage domain models.

### Implementations

1. **In-Memory** (`app/repositories/in_memory.py`): Stores records in a Python dictionary. Used for fast testing and pure in-memory development.
2. **SQLAlchemy** (`app/repositories/sqlalchemy_repo.py`): Real relational database backend (currently configured for SQLite). Defines `TenantRecord`, `ProjectRecord`, and `GeometryRecord` models (`app/db/models.py`).

### Repository Swap Architecture

Dependency Injection (`backend/app/dependencies.py`) controls the active persistence layer. The FastAPI application depends on `get_geometry_repository()`, which dynamically returns either `InMemoryGeometryRepository` or `SQLGeometryRepository` based on the `USE_SQL_REPOSITORY` environment variable. The API and business logic remain completely unchanged regardless of the storage backend.

## Multi-Tenant Architecture

BuildDesk is designed to support multiple tenants (e.g., different fabrication shops) natively. Tenant isolation is treated as a first-class application concern.

### Tenant Context Resolution

Currently, in Phase 1, tenant context is passed explicitly via the `X-Tenant-ID` HTTP header. This is resolved centrally by a FastAPI dependency (`get_current_tenant` in `backend/app/tenant_context.py`), ensuring that downstream handlers do not need to parse headers manually. 

### Tenant Isolation Rules

1. **API Perimeter**: Every `/api/v1/geometry` and `/api/v1/export/*` endpoint demands the `X-Tenant-ID` header.
2. **Repository Layer**: The `GeometryRepository` protocol explicitly requires `tenant_id` for reads and listings (e.g., `get_by_id(tenant_id, geometry_id)`). This guarantees that isolation is enforced at the data access level.
3. **Database Security**: Both `InMemoryGeometryRepository` and `SQLGeometryRepository` aggressively filter queries using the provided `tenant_id`. Cross-tenant data leakage is fundamentally prevented at the source.
4. **Demo Scoping**: Demo endpoints (`/api/v1/demo/*`) bypass header checks but are internally bound to a hardcoded `_DEMO_TENANT_ID` to ensure Demo payloads don't bleed into active tenant workspaces.

## Phase 2 Database Roadmap

The current implementation leverages PostgreSQL via the robust `psycopg` (v3) driver in synchronous mode. To reach full production readiness:
1. Adopt PostgreSQL via an async engine (`asyncpg`).
2. Update repository abstractions to be fully async (`asyncSession`).
3. Add robust row-level security and constraints.
4. Implement JWT authentication to securely extract Tenant IDs.

## Deployment Strategy

BuildDesk is designed to be fully containerised, with a stateless API tier and a managed database tier. The primary deployment target is **GCP Cloud Run**.

### Cloud SQL Production Persistence Architecture
For production persistence, BuildDesk utilizes Google Cloud SQL (PostgreSQL). The database is accessed via Cloud Run using the internal Auth Proxy (Unix sockets) ensuring high security without public IP exposure. The `DATABASE_URL` is never committed to code; it is explicitly managed in Google Secret Manager and injected at deployment time.

### Cloud Run Architecture
The FastAPI application operates completely stateless, meeting Cloud Run's requirements. 
- It binds dynamically to the `$PORT` environment variable provided by GCP.
- Liveness and readiness probes rely on the `GET /api/v1/health` endpoint, which verifies the application version and `database` connectivity status explicitly. It dynamically reports backend connections (e.g. `sqlite-connected`, `postgres-connected`, or `cloudsql-postgres-connected`).
- The `lifespan` startup hook ensures a graceful boot and database verification before accepting traffic.
- Post-deployment validation is codified in `docs/deployment-checklist.md` to ensure Tenant isolation and DB connectivity function in the cloud environment.

### GCP Deployment Workflow
Deployment to GCP is automated via `gcloud` and Cloud Build. Detailed setup instructions for Cloud Run and Cloud SQL are maintained in `docs/gcp-setup.md` and `docs/cloud-sql.md`. We support a direct deployment shell script (`backend/scripts/deploy.sh`) which has been extended to securely link Cloud SQL instances and inject Secret Manager credentials.
```bash
make deploy-gcp
```
or for Cloud SQL:
```bash
CLOUDSQL_INSTANCE=project:region:instance make deploy-cloudsql
```

You can validate deployments using the CLI helpers:
```bash
make check-health CLOUD_RUN_URL=https://builddesk-api-...
make cloud-logs
```

### Live Deployment Status
The backend API is fully proven on GCP Cloud Run. During the initial deployment, it was verified that container images must explicitly target the `linux/amd64` architecture. This fix is now codified into the deployment scripts. The service handles database persistence and SVG/PDF generation seamlessly within the serverless environment.

### Artifact Registry Strategy
All Docker images are built and pushed to a Google Cloud Artifact Registry repository (e.g. `us-central1-docker.pkg.dev/...`) tagged uniquely by their Git `COMMIT_SHA`. Cloud Run is then instructed to deploy from this registry URL, ensuring traceability and rollback capability.

### Docker Workflow
A minimal, production-ready `Dockerfile` based on `python:3.11-slim` is provided in the `backend/` directory. It uses a multi-stage build to ensure a small image size and fast startup times.

For local development and testing, a `docker-compose.yml` is provided. It stands up the FastAPI container alongside a PostgreSQL instance (preparing for the Phase 2 database migration).
To start the local stack:
```bash
make docker-up
```
To validate the Cloud Run environment locally:
```bash
make cloud-run-local
```
The platform is strictly configured via environment variables, loaded safely through Pydantic's `BaseSettings` (`app.config`). This ensures a 12-Factor App design.
Key environment variables include:
- `APP_ENV`: Deployment environment (`development` / `production`)
- `USE_SQL_REPOSITORY`: Toggles between `InMemory` and `SQL` persistence.
- `DATABASE_URL`: The SQLAlchemy connection string.

### GCP Readiness
The API exposes a `GET /api/v1/health` endpoint specifically designed to serve as a liveness and readiness probe for Google Cloud Run and load balancers. It validates basic app status, version, and database connectivity on every check.

## Alembic Schema Evolution

Database migrations are strictly managed using [Alembic](https://alembic.sqlalchemy.org/). The `backend/alembic/` directory contains the migration environment, which is wired to introspect the SQLAlchemy declarative models (`app/db/models.py`) to autogenerate migration scripts.

### Alembic Usage Guide

All commands must be executed within the `backend/` directory with the virtual environment activated.

**1. Create a new migration (Autogenerate)**
Whenever a model changes in `models.py`:
```bash
alembic revision --autogenerate -m "description_of_change"
```
*Note: Always review the generated script in `alembic/versions/` before applying it, as autogenerate can miss complex constraint changes.*

**2. Apply migrations**
To upgrade the database to the latest schema:
```bash
alembic upgrade head
```

**3. Revert migrations**
To downgrade the schema by one revision:
```bash
alembic downgrade -1
```---

## Drawing Fidelity Architecture (Phase 4)

### Core Requirement
BuildDesk is a fabrication package generator. The drawings it produces must visually match real-world shop drawings. Text tables of dimensions are insufficient.

### Rendering Pipeline
The system uses a decoupled rendering pipeline optimized for vector output:

1. **Domain Models (`app.models.fabrication`)**: Source of truth for physical dimensions, edges, cutouts, holes, and splashes.
2. **`FabricationDrawingEngine`**: The core layout and vector calculation layer.
   - Computes auto-scaling to fit any given physical layout into a defined drawing zone.
   - Outputs framework-agnostic geometric commands.
3. **`PackagePdfExporter` (ReportLab)**: Integrates the drawing engine into a multi-page PDF document. Features a two-column layout (drawing left, notes right) and title block headers.
4. **`AssemblySvgExporter`**: Integrates the drawing engine to emit raw SVG for rapid web previews, matching the exact visual rules of the PDF.

### Fabrication-Aware Primitives
Unlike a generic CAD system, our primitive renderer understands countertop semantics:
- **Edges**: Differentiated by line style (e.g., polished = thick solid, raw = thin dashed, miter = hatched).
- **Cutouts**: Differentiated by mount type (undermount = dashed, overmount = solid). Sink cutouts receive automatic corner radii.
- **Holes**: Rendered as circles with center crosshairs and diameter/purpose labels.
- **Splashes**: Rendered as shaded bands along the corresponding part edge (Left, Right, Back).
- **Seams**: Emits dashed indicator lines at part joins.

### Layout Engine Rules
- **Coordinate Space**: The drawing engine normalizes the coordinate space. Left-to-right part placement is automatic.
- **Scale Calculation**: `scale = min(w_scale, h_scale)` clamped between 1 pt/in and 6 pt/in.
- **Variants**: Assemblies marked as `MIRROR` have their X-coordinates automatically inverted by the layout engine before drawing.

### Gap Analysis Findings
Phase 4 closed the critical gaps identified in the Phase 3 output:
- Replaced table-based part lists with scaled vector drawings.
- Added visual edge differentiation.
- Added visual cutouts, holes, and splashes.
---

## Frontend Architecture (Phase 5)

### Project Authoring Workflow
The React frontend has been strictly aligned to the multifamily fabrication domain. The generic "dashboard" and "shape drawing playground" concepts have been removed.

The workflow centers around the **Project Workspace**:
1. **Hierarchy & Units (`HierarchyPanel`)**: Users define Unit Types (e.g., "A1", "A1-MIR") and their associated physical units.
2. **Assemblies (`AssembliesPanel` / `AssemblyEditor`)**: Users configure fabrication-aware assemblies (Kitchen, Vanity) and build out their physical `Parts` with exact dimensions, `Edges` (Polished, Miter, Raw), `Cutouts` (Sink, Cooktop), `Holes`, and `Splashes`.
3. **Packages (`PackagesPanel`)**: Users trigger the generation of the multi-page PDF package, track its status, and download it.

### UI Domain Mapping
The frontend domain types strictly mirror the backend Pydantic models:
- `src/types/hierarchy.ts` maps to `app.models.hierarchy`
- `src/types/fabrication.ts` maps to `app.models.fabrication`
- `src/types/packages.ts` maps to `app.models.project_package`

### Live Preview Pipeline
The frontend integrates seamlessly with the backend's `FabricationDrawingEngine` by embedding a live `<img>` tag that sources the `/assemblies/{id}/preview/svg` endpoint. As users modify dimensions or edges in the React forms, saving the assembly instantly regenerates the SVG preview, providing immediate visual feedback that matches the exact visual semantics of the final PDF package.
