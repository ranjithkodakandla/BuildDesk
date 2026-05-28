"""
Health Router
=============
Provides liveness and readiness endpoints for GCP Cloud Run health checks
and general platform status monitoring.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the current operational status of the BuildDesk API.",
)
def health_check() -> HealthResponse:
    """Liveness / readiness probe for Cloud Run and load balancers."""
    return HealthResponse(
        status="ok",
        service="buildesk-api",
        version="0.1.0",
    )
