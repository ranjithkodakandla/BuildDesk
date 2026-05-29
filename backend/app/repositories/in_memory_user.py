"""
InMemory User Repository
========================
In-memory implementation of UserRepository for development and testing.
"""
import uuid
from typing import Dict, List, Optional

from app.models.user import User
from app.repositories.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    """Thread-local in-memory user store. NOT production-safe."""

    def __init__(self):
        # Keyed by user_id
        self._store: Dict[uuid.UUID, User] = {}

    def save(self, user: User) -> None:
        self._store[user.id] = user

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self._store.get(user_id)

    def get_by_email(self, tenant_id: uuid.UUID, email: str) -> Optional[User]:
        for user in self._store.values():
            if user.tenant_id == tenant_id and user.email.lower() == email.lower():
                return user
        return None

    def list_by_tenant(self, tenant_id: uuid.UUID) -> List[User]:
        return [u for u in self._store.values() if u.tenant_id == tenant_id]
