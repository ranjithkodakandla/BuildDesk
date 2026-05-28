import uuid
from typing import Optional, Protocol
from app.models.project import Project

class ProjectRepository(Protocol):
    def save(self, project: Project) -> None:
        """Persist a project record."""
        ...

    def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        """Retrieve a project by its UUID."""
        ...
