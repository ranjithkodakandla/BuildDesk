"""
BuildDesk Backend
=================
Geometry-driven B2B SaaS platform for builders, construction companies,
and surface contractors.

Architecture: Multi-tenant, backend-first, GCP Cloud Run target.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.demo import router as demo_router
from app.api.export import router as export_router
from app.api.geometry import router as geometry_router
from app.api.health import router as health_router
from app.api.shapes import router as shapes_router
from app.config import get_settings

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager

from app.config import get_settings

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.use_sql_repository:
            from app.db.session import engine
            try:
                # Validate DB connectivity at startup
                with engine.connect():
                    pass
            except Exception as e:
                # Log but do not fail to allow migrations to run
                print(f"Warning: Database connection failed during startup: {e}")
        yield

    application = FastAPI(
        title="BuildDesk API",
        description=(
            "Geometry-driven B2B SaaS platform for builders, "
            "construction companies, and surface contractors."
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
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers  (all mounted under /api/v1)
    # ------------------------------------------------------------------

    application.include_router(health_router,   prefix="/api/v1", tags=["health"])
    application.include_router(shapes_router,   prefix="/api/v1", tags=["shapes"])
    application.include_router(geometry_router, prefix="/api/v1", tags=["geometry"])
    application.include_router(export_router,   prefix="/api/v1", tags=["export"])
    application.include_router(demo_router,     prefix="/api/v1", tags=["demo"])

    return application


app = create_app()
