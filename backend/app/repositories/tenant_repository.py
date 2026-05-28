import uuid
from typing import Optional, Protocol
from app.models.tenant import Tenant

class TenantRepository(Protocol):
    def save(self, tenant: Tenant) -> None:
        """Persist a tenant record."""
        ...

    def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Retrieve a tenant by its UUID."""
        ...
