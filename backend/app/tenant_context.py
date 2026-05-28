import uuid
from fastapi import Header, HTTPException

def get_current_tenant(x_tenant_id: str = Header(..., description="Tenant ID context for isolation")) -> uuid.UUID:
    """
    FastAPI dependency to extract the active tenant ID from request headers.
    In Phase 1, we trust the header (no JWT yet).
    """
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID format. Must be a valid UUID.")
