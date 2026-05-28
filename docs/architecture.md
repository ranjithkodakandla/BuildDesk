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