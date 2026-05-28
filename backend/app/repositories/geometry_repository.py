import uuid
from typing import Optional, List, Protocol

from app.api.schemas import GeometryResponse

class GeometryRepository(Protocol):
    def save(self, geometry: GeometryResponse) -> None:
        """Persist a newly generated geometry record."""
        ...

    def get_by_id(self, geometry_id: uuid.UUID) -> Optional[GeometryResponse]:
        """Retrieve a geometry record by its UUID."""
        ...

    def list_by_project(self, project_id: uuid.UUID) -> List[GeometryResponse]:
        """List all geometry records for a given project."""
        ...
