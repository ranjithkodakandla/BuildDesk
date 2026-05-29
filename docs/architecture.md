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

### Phase 9: Import Engine
To rapidly populate the `Unit` hierarchy, the `ImportService` orchestrates a two-step CSV/Excel intake:
1. **Validation & Preview:** Translates raw schedules via dynamic `ImportMapping`, validates references (e.g. valid `unit_type`), and identifies duplicates.
2. **Execution:** Materializes the structured rows into domain entities.
Error logs and mappings are isolated per `tenant_id` on the `ImportJobRecord`.

### Phase 10: Export Engine
To enable data round-tripping and operational reporting, the `ExportService` tracks asynchronous artifact generation using `ExportJobRecord`. It supports formats like `.csv` and `.xlsx` built on top of `openpyxl`.
- **Schedule:** Extracts project hierarchy into flat rows mapping units to buildings/floors.
- **Fabrication:** Aggregates parametric sub-parts, sizes, and square footage across all instantiated unit assemblies.
- **Summary:** Rolls up square footage estimation grouped by `UnitType`.
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

---

## Issued Package Architecture (Phase 12)

### PDF Composition Rules
The `PackagePdfExporter` has been elevated from a raw diagnostic tool to a professional document generation engine.
- **Table of Contents (TOC):** A dedicated `_draw_toc` mechanism calculates and reserves pagination across type sheets and assembly drawings to provide a comprehensive index for large 100+ unit projects.
- **Shop-Ready Schedules:** The two-column layout dynamically converts JSON models into structured Edge, Cutout, Hole, and Splash schedules.
- **Drawing Sheet Structure:** Each page acts as an independent "Sheet" featuring a formal Title Block (Project, Type, Assembly, Sheet N of M, Revision ID).
- **Field & Installer Readiness:** Assembly metadata now automatically displays installation tags (e.g. `ASSEMBLE-ON-SITE`) and location metadata directly on the blueprint to reduce field RFI questions.

### Branding & White-Label Foundation
The cover page template is designed to easily support white-label configuration hooks in the future (e.g., logo ingestion, company name substitution, and customizable footer notes). Currently, these blocks display standardized `BUILDDESK` metadata, paving the way for multi-tenant customization.

---

## Operational Coordination Architecture (Phase 13)

### Package Status Rules
The `ProjectPackageStatus` enum has been expanded to support a complete document lifecycle:
- **`DRAFT` / `GENERATING` / `READY`**: Automated states during PDF compilation.
- **`SUBMITTED`**: Package has been sent to the reviewer/client.
- **`UNDER_REVIEW`**: Package is currently being evaluated.
- **`APPROVED`**: Package is formally approved for fabrication. (Records `approved_by` and `approved_at`).
- **`REJECTED`**: Package has corrections required.
- **`SUPERSEDED`**: Package is outdated by a newer revision.
- **`ISSUED`**: Package has been formally pushed to the shop floor.

### Approval Workflow
The `POST /projects/{id}/packages/{pkg_id}/transition` API drives the state machine. Transitions to terminal states (APPROVED/REJECTED) automatically capture metadata (`approved_by`, `review_notes`) without requiring a heavyweight BPM engine. This keeps the UX fast and frictionless.

### RFI Lifecycle
The `RFI` (Request for Information) model (`backend/app/models/rfi.py`) bridges the gap between field questions and backend data:
- **Relational Integrity:** RFIs can be optionally linked to specific packages, assemblies, or parts.
- **State Machine:** Transitions from `OPEN` to `ANSWERED` when a coordinator supplies clarification.
- **Tenant Isolation:** Fully scoped to `tenant_id` to prevent cross-company data leakage.

---

## Revision & Artifact Lifecycle (Phase 11)

### Snapshot Isolation
BuildDesk embraces immutable generation. A generated `ProjectPackage` acts as a historical snapshot.
- Generating a new package does **not** overwrite the previous one.
- Each generation creates a new `ProjectPackageRecord` with a distinct `version` (e.g., "1.0", "Rev A") and an optional `revision_notes` tracking user-entered change reasons.
- The `PackageRepository` orders packages by `created_at DESC` to always provide the "latest" revision for general operations, while preserving access to past artifacts.

### Artifact Lineage
- PDF files generated asynchronously are written with unique filenames incorporating their version and timestamp (e.g., `package_RevA.pdf`).
- Old PDF files are intentionally not deleted. This gives coordinators and builders absolute confidence in past historical data matching previously issued field documents.
- Operational exports (CSV/XLSX schedules) are generated off the *live* data hierarchy. To preserve historical exports, users must either export and save them locally alongside their PDF package, or rely on future phase cloud-bucket artifact archiving.

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

---

## Real Project Pilot Validation (Phase 6)

During the Phase 6 Pilot, the entire architecture (Frontend + Backend + DB) was validated against a 40-unit, multi-floor project ("The Highland Residences").

### Validated Decisions
1. **Domain Isolation:** Separating Unit Types from Units aligns perfectly with fabrication logic.
2. **REST API boundaries:** The FastAPI routers correctly handled the hierarchical and piecewise construction of assemblies.
3. **SVG Fidelity:** Generating the SVG on the backend using the *exact same* scaling math as the PDF ensures total WYSIWYG parity.

### Required Architecture Adjustments
1. **Synchronous Generation Bottleneck:** Generating a 40-unit PDF synchronously over HTTP is viable (takes ~2 seconds), but a 300-unit package will cause HTTP timeouts. The PDF generation pipeline **must** be moved to a background worker queue, with the final artifact uploaded to Cloud Storage (GCS). *(Resolved in Phase 7)*
2. **UI Bulk Tools:** The React frontend requires bulk mutation tools (e.g., "Assign Units 101-108 to A1") rather than single-record forms to handle real-world scale.

---

## Asynchronous Package Workflow & Storage (Phase 7)

To solve the HTTP timeout bottleneck at scale, the package generation pipeline was decoupled into an asynchronous job loop.

### 1. Job Lifecycle
- `POST /projects/{id}/package/generate`: Validates the request, creates a `ProjectPackage` record in the `generating` state, and immediately returns `202 Accepted` (or a `200 OK` manifest) while pushing the heavy PDF export task to FastAPI's `BackgroundTasks`.
- `GET /projects/{id}/package/status`: Queried periodically by the frontend to watch for transition from `generating` to `ready` or `generation_failed`.

### 2. Artifact Storage Architecture
- A new `CloudStorageService` persists the final `pdf_bytes` outside of the application instance.
- **Local Fallback:** Writes to `artifacts/mock_gcs/` and returns a `local://` URI.
- **Cloud Mode:** Writes directly to a Google Cloud Storage bucket and returns a `gs://` URI.
- The `GET /projects/{id}/package/download` endpoint abstracts this storage URI, returning a signed redirect or serving the local file directly.

### 3. Scaling Assessment & Thresholds
- **Current:** FastAPI `BackgroundTasks` executes in the same Python process loop. This perfectly handles 5-10 concurrent package generations of <1000 units.
- **Threshold for Distributed Workers (Celery/Kafka):** We should ONLY move to distributed workers if memory pressure on the main FastAPI containers exceeds limits during PDF rendering, or if we need to scale PDF generation horizontally independent of the API nodes. For now, `BackgroundTasks` is robust, simple, and strictly adheres to avoiding premature infrastructure complexity.

---

## Bulk Authoring Workflow (Phase 8)

To support realistic multifamily projects (100–300+ units), the application provides bulk creation capabilities instead of standard row-by-row CRUD.

### 1. Hierarchy Productivity Patterns
- **Bulk Unit Engine:** The `POST /projects/{id}/units/bulk` endpoint generates units programmatically. It accepts a range (e.g. `start_number=1`, `end_number=20`), a prefix (e.g. `10`), and an increment, automatically constructing patterns like `101, 102, 103...`.
- **Assembly Duplication:** `POST /assemblies/{id}/duplicate` enables a deep-copy of a complex assembly configuration, fully regenerating UUIDs for all underlying parts, edges, holes, and splashes, and optionally assigning a mirrored variant.
- **Variant Helpers:** The system accommodates base types (`A1`) and derived variants (`A1-MIR`). Duplicating an assembly and assigning the mirror variant allows fabricators to explicitly define mirrored toolpaths without redefining the 20+ cuts and holes manually.

### 2. Import Compatibility Notes
The Bulk Unit Engine operates via REST JSON today, but its implementation within `HierarchyService.bulk_add_units()` is architected to seamlessly plug into future data sources. A future CSV or Excel parser will simply normalize rows into this bulk generation logic, ensuring domain constraints (tenant isolation, building/floor foreign keys, and unique constraints) are centrally enforced regardless of input mechanism.

---

## Operational Scale Layer (Phase 14)

Phase 14 adds operational scalability features that support larger multifamily countertop programs without changing the core fabrication package model.

### Tenant Profile Configuration
Tenant profile fields live on `TenantRecord` and are exposed through `GET/PUT /api/v1/tenant/profile`.
- `company_name` controls PDF cover and footer branding.
- `logo_url` is treated as a lightweight logo placeholder reference for now.
- `default_footer` replaces the hardcoded PDF confidentiality/footer text.
- `standard_notes` replaces hardcoded fabrication notes on package covers.

This remains a tenant profile foundation, not a full white-label subsystem.

### Search Architecture
`SearchRepository` is the cross-entity operational query layer. It returns normalized `SearchResultItem` objects for:
- Projects
- Units
- Assemblies
- Packages
- RFIs

All queries are scoped by `tenant_id` and support filters for status, project, building, floor, unit type, assembly type, and date range. The frontend uses the same endpoint for dashboard search, saved filters, project search, and operational queues.

### Bulk Workflow Architecture
`Unit.status` adds a minimal lifecycle state for large schedule operations:
- `active`
- `archived`

`PUT /api/v1/projects/{project_id}/units/bulk` performs tenant-scoped bulk updates for unit type assignment, variant assignment, hierarchy assignment, and archive/reactivation status changes. This supports realistic schedule cleanups without introducing a broader workflow engine.

### Frontend Operations Surface
The dashboard now has four operational views:
- Projects
- Search
- Queues
- Settings

The project workspace keeps authoring focused on fabrication, with an added project-scoped search tab and bulk controls in `HierarchyPanel`.

### Integration Validation (Phase 14.5)

Phase 14.5 closed the loop between tenant profile configuration and issued-package output without expanding the domain model.

- **Profile → PDF path:** `PUT /api/v1/tenant/profile` persists branding on `TenantRecord`. `POST /projects/{id}/package/generate` builds the manifest synchronously, then `generate_pdf_background` loads the tenant via `SQLTenantRepository` and passes it to `PackagePdfExporter`.
- **Async worker DB access:** Background tasks use `SessionLocal`; integration tests patch `app.tasks.package_generation.SessionLocal` to the test engine so workers share the same database session factory as HTTP handlers.
- **Validation layers:** Pytest integration (`test_phase14_5_integration.py`) covers the branding pipeline; `run_pilot_workflow.py` exercises the full multifamily operational workflow (import-ready hierarchy, packages, revisions, approvals, exports) via authenticated HTTP.
