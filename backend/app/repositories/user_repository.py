"""
User Repository Abstraction
===========================
Abstract base for user persistence.
Implementations: InMemoryUserRepository, SQLUserRepository.
"""
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from app.models.user import User


class UserRepository(ABC):
    """Abstract user storage interface."""

    @abstractmethod
    def save(self, user: User) -> None:
        ...

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_email(self, tenant_id: uuid.UUID, email: str) -> Optional[User]:
        ...

    @abstractmethod
    def list_by_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        ...
