"""
BuildDesk Backend
=================
Multifamily countertop fabrication package platform for builders,
construction companies, and surface contractors.

Architecture: Multi-tenant, backend-first, GCP Cloud Run target.
Domain: Project → Building (opt) → Floor (opt) → Unit → Assembly → Part → Package
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import HTTPBearer

from app.api.auth import router as auth_router
from app.api.demo import router as demo_router
from app.api.export import router as export_router
from app.api.fabrication import router as fabrication_router
from app.api.geometry import router as geometry_router
from app.api.health import router as health_router
from app.api.hierarchy import router as hierarchy_router
from app.api.packages import router as packages_router
from app.api.shapes import router as shapes_router
from app.api.imports import router as imports_router
from app.api.exports import router as exports_router
from app.api.rfis import router as rfis_router
from app.api.search import router as search_router
from app.api.tenants import router as tenants_router
from app.api.templates import router as templates_router
from app.api.matrix import router as matrix_router
from app.config import get_settings
from app.startup_checks import has_blocking_errors, log_startup_checks, run_startup_checks

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        checks = run_startup_checks(settings)
        log_startup_checks(checks)
        if has_blocking_errors(checks) and settings.is_production:
            raise RuntimeError("Blocking production configuration errors — see startup logs.")

        if settings.use_sql_repository:
            from app.db.session import engine
            backend_type = "postgres" if "postgresql" in settings.database_url else "sqlite"
            print(f"Starting BuildDesk with SQL Repository ({backend_type} backend)")
            try:
                # Validate DB connectivity at startup
                with engine.connect():
                    print(f"✓ Database connectivity to {backend_type} established.")
            except Exception as e:
                # Log but do not fail to allow migrations to run
                print(f"Warning: Database connection failed during startup: {e}")
        else:
            print("Starting BuildDesk with In-Memory Repository")
        yield

    application = FastAPI(
        title="BuildDesk API",
        description=(
            "Geometry-driven B2B SaaS platform for builders, "
            "construction companies, and surface contractors. "
            "Use the Authorize button to supply a Bearer JWT token."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers  (all mounted under /api/v1)
    # ------------------------------------------------------------------

    application.include_router(health_router,    prefix="/api/v1", tags=["health"])
    application.include_router(auth_router,      prefix="/api/v1", tags=["auth"])
    # Phase 1: Project Hierarchy
    application.include_router(hierarchy_router, prefix="/api/v1", tags=["hierarchy"])
    # Phase 2: Fabrication Domain (Assemblies)
    application.include_router(fabrication_router, prefix="/api/v1", tags=["fabrication"])
    # Phase 3: Package Generator
    application.include_router(packages_router,  prefix="/api/v1", tags=["packages"])
    # Phase 9: Import Domain
    application.include_router(imports_router,   prefix="/api/v1", tags=["imports"])
    # Phase 10: Export Domain
    application.include_router(exports_router,   prefix="/api/v1", tags=["exports"])
    # Phase 13: Operational Coordination (RFIs)
    application.include_router(rfis_router,      prefix="/api/v1", tags=["rfis"])
    # Phase 14: Search
    application.include_router(search_router,    prefix="/api/v1", tags=["search"])
    application.include_router(tenants_router,   prefix="/api/v1", tags=["tenant"])
    # Phase 4: Template-Driven Fabrication API
    application.include_router(templates_router, prefix="/api/v1", tags=["templates"])
    application.include_router(matrix_router,   prefix="/api/v1", tags=["matrix"])
    # Legacy geometry endpoints (deprecated, kept for backward compatibility)
    application.include_router(shapes_router,    prefix="/api/v1", tags=["shapes (legacy)"])
    application.include_router(geometry_router,  prefix="/api/v1", tags=["geometry (legacy)"])
    application.include_router(export_router,    prefix="/api/v1", tags=["export (legacy)"])
    application.include_router(demo_router,      prefix="/api/v1", tags=["demo (legacy)"])

    return application


app = create_app()
