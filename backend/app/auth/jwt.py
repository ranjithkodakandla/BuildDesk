"""
JWT Token Service
=================
Handles creation and validation of signed JWT access tokens.

Token payload (claims):
    sub   – user UUID (string)
    tid   – tenant UUID (string)
    email – user email
    role  – user role
    exp   – expiry timestamp (standard JWT)
    iat   – issued-at (standard JWT)

Configuration:
    JWT_SECRET_KEY  – env var (required in production)
    JWT_ALGORITHM   – defaults to HS256
    ACCESS_TOKEN_EXPIRE_MINUTES – defaults to 60
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

_ALGORITHM = settings.jwt_algorithm
_SECRET    = settings.jwt_secret_key
_EXPIRES   = settings.access_token_expire_minutes


class TokenError(Exception):
    """Raised when JWT validation fails."""


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Mint a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_EXPIRES))

    payload = {
        "sub":   str(user_id),
        "tid":   str(tenant_id),
        "email": email,
        "role":  role,
        "iat":   now,
        "exp":   expire,
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises TokenError on any validation failure (expired, bad sig, malformed).
    Returns the raw claims dict on success.
    """
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        if payload.get("sub") is None:
            raise TokenError("Token missing 'sub' claim.")
        return payload
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
