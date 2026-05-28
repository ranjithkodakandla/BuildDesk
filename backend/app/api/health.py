"""
Health Router
=============
Provides liveness and readiness endpoints for GCP Cloud Run health checks
and general platform status monitoring.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()
settings = get_settings()

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    tenant_mode: bool

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the current operational status of the BuildDesk API.",
)
def health_check() -> HealthResponse:
    """Liveness / readiness probe for Cloud Run and load balancers."""
    
    db_status = "in-memory"
    if settings.use_sql_repository:
        db_status = "sql"
        try:
            from app.db.session import engine
            with engine.connect():
                db_status = "sql-connected"
        except Exception:
            db_status = "sql-disconnected"

    return HealthResponse(
        status="ok",
        service="buildesk-api",
        version=settings.app_version,
        database=db_status,
        tenant_mode=True,
    )
