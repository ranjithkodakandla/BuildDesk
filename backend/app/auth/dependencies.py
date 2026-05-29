"""
Authentication Dependencies
============================
FastAPI dependency functions for JWT-based auth and tenant resolution.

Dependency hierarchy:
    get_current_user()      ← validates JWT, returns User domain object
    get_current_tenant()    ← extracts tenant_id from JWT (or X-Tenant-ID header in dev)
    require_active_user()   ← get_current_user() + is_active guard

Usage in route handlers:
    current_user: User = Depends(get_current_user)
    tenant_id: uuid.UUID = Depends(get_current_tenant)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token, TokenError
from app.config import get_settings
from app.dependencies import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.in_memory_user import InMemoryUserRepository
from app.repositories.sql_user_repo import SQLUserRepository

settings = get_settings()

_bearer_scheme = HTTPBearer(auto_error=False)

# Module-level singleton for in-memory mode
_in_memory_user_repo = InMemoryUserRepository()


# ---------------------------------------------------------------------------
# User Repository Provider
# ---------------------------------------------------------------------------

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Dependency provider: returns SQL or in-memory user repository."""
    if settings.use_sql_repository:
        return SQLUserRepository(db)
    return _in_memory_user_repo


# ---------------------------------------------------------------------------
# JWT Auth Dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Validate Bearer token and return the authenticated User.
    Raises HTTP 401 on any auth failure.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError:
        raise _unauthorized

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise _unauthorized

    user = repo.get_by_id(user_id)
    if user is None:
        raise _unauthorized

    return user


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Guard: additionally checks that the user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return current_user


def get_current_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_tenant_id: Optional[str] = Header(default=None, description="Tenant ID (required for register/login; JWT preferred for data endpoints)"),
    repo: UserRepository = Depends(get_user_repository),
) -> uuid.UUID:
    """
    Extract tenant_id from:
      1. JWT payload  (all environments — preferred for protected data routes)
      2. X-Tenant-ID header (all environments — required for register/login flows)

    Protected data endpoints (geometry, export) additionally enforce require_active_user(),
    which validates the full JWT. The header-only path is intentionally left open so that
    unauthenticated users can register/login with a known tenant scope.
    """
    # --- JWT path ---
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            tid_str = payload.get("tid")
            if tid_str:
                return uuid.UUID(tid_str)
        except (TokenError, ValueError):
            pass

    # --- X-Tenant-ID header (always accepted for tenant scoping) ---
    if x_tenant_id:
        try:
            return uuid.UUID(x_tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID format. Must be a valid UUID.")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tenant context required. Provide 'X-Tenant-ID' header or valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
