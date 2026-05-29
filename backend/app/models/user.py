"""
User Domain Model
=================
Lightweight domain representation of an authenticated user.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    """Domain user — stored only hashed_password, never plaintext."""

    tenant_id: uuid.UUID
    email: str
    hashed_password: str
    role: str = "member"           # member | admin
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=_utcnow)
