"""
Auth Router
===========
JWT-based authentication endpoints.

Endpoints:
    POST /api/v1/auth/register  – create a new tenant-scoped user account
    POST /api/v1/auth/login     – authenticate and receive a JWT access token
    GET  /api/v1/auth/me        – return the authenticated user's profile
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.auth.dependencies import get_current_tenant, get_user_repository, require_active_user
from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.dependencies import get_tenant_repository
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


def _ensure_tenant_exists(tenant_id: uuid.UUID, email: str, tenant_repo: TenantRepository) -> None:
    """Cloud SQL requires a tenants row before users can be inserted (FK)."""
    if tenant_repo.get_by_id(tenant_id) is None:
        tenant_repo.save(
            Tenant(
                tenant_id=tenant_id,
                name=f"Tenant {str(tenant_id)[:8]}",
                slug=f"tenant-{str(tenant_id)[:8]}",
                contact_email=email,
            )
        )

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas  (auth-specific, kept local to this module)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address (unique per tenant)")
    password: str = Field(..., min_length=8, description="Plaintext password (min 8 chars)")
    role: str = Field(default="member", description="User role: 'member' or 'admin'")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    email: str


class UserProfileResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    is_active: bool


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Creates a new user account scoped to the current tenant. "
        "Immediately returns a JWT access token so the caller can proceed without a separate login. "
        "Email must be unique within the tenant."
    ),
)
def register(
    body: RegisterRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    repo: UserRepository = Depends(get_user_repository),
    tenant_repo: TenantRepository = Depends(get_tenant_repository),
) -> TokenResponse:
    _ensure_tenant_exists(tenant_id, body.email, tenant_repo)
    # Enforce uniqueness within tenant
    existing = repo.get_by_email(tenant_id, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{body.email}' already exists in this tenant.",
        )

    role = body.role if body.role in ("member", "admin") else "member"
    user = User(
        tenant_id=tenant_id,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role=role,
    )
    repo.save(user)

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT",
    description=(
        "Authenticates with email + password. "
        "Returns a signed JWT access token valid for the configured expiry window. "
        "Include the token in subsequent requests as 'Authorization: Bearer <token>'."
    ),
)
def login(
    body: LoginRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    repo: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    user = repo.get_by_email(tenant_id, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile derived from the JWT token.",
)
def me(current_user: User = Depends(require_active_user)) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )
