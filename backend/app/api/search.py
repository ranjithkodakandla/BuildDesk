"""
Search API Router (Phase 14)
==========================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from app.api.search_schemas import SearchQueryRequest, SearchResponse
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.user import User
from app.repositories.search_repository import SearchRepository

router = APIRouter(tags=["search"])


def get_search_repo(db: Session = Depends(get_db)) -> SearchRepository:
    return SearchRepository(db)


@router.post("/search", response_model=SearchResponse)
def global_search(
    body: SearchQueryRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: SearchRepository = Depends(get_search_repo),
):
    """
    Cross-project operational search.
    Supports filtering by entity type, project, and operational states.
    """
    results = repo.search(tenant_id, body)
    return SearchResponse(
        results=results,
        total_count=len(results)
    )
