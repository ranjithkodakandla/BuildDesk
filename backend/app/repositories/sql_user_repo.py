"""
SQLAlchemy User Repository
==========================
Durable implementation of UserRepository backed by PostgreSQL / SQLite via SQLAlchemy.
"""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import UserRecord
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _record_to_user(record: UserRecord) -> User:
    return User(
        id=uuid.UUID(record.id),
        tenant_id=uuid.UUID(record.tenant_id),
        email=record.email,
        hashed_password=record.hashed_password,
        role=record.role,
        is_active=record.is_active,
        created_at=record.created_at,
    )


class SQLUserRepository(UserRepository):
    """Persists users in the SQL database."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, user: User) -> None:
        existing = self.session.query(UserRecord).filter(
            UserRecord.id == str(user.id)
        ).first()
        if existing:
            existing.email = user.email
            existing.hashed_password = user.hashed_password
            existing.role = user.role
            existing.is_active = user.is_active
        else:
            record = UserRecord(
                id=str(user.id),
                tenant_id=str(user.tenant_id),
                email=user.email,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
            )
            self.session.add(record)
        self.session.commit()

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        record = self.session.query(UserRecord).filter(
            UserRecord.id == str(user_id)
        ).first()
        return _record_to_user(record) if record else None

    def get_by_email(self, tenant_id: uuid.UUID, email: str) -> Optional[User]:
        record = self.session.query(UserRecord).filter(
            UserRecord.tenant_id == str(tenant_id),
            UserRecord.email == email.lower(),
        ).first()
        return _record_to_user(record) if record else None

    def get_by_email_global(self, email: str) -> Optional[User]:
        record = (
            self.session.query(UserRecord)
            .filter(UserRecord.email == email.lower())
            .order_by(UserRecord.created_at.asc())
            .first()
        )
        return _record_to_user(record) if record else None

    def list_by_tenant(self, tenant_id: uuid.UUID) -> List[User]:
        records = self.session.query(UserRecord).filter(
            UserRecord.tenant_id == str(tenant_id)
        ).all()
        return [_record_to_user(r) for r in records]
