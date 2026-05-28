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
