"""
BuildDesk Backend
=================
Geometry-driven B2B SaaS platform for builders, construction companies,
and surface contractors.

Architecture: Multi-tenant, backend-first, GCP Cloud Run target.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import get_settings

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    application = FastAPI(
        title="BuildDesk API",
        description=(
            "Geometry-driven B2B SaaS platform for builders, "
            "construction companies, and surface contractors."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
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
    # Routers
    # ------------------------------------------------------------------

    application.include_router(health_router, prefix="/api/v1", tags=["health"])

    return application


app = create_app()
