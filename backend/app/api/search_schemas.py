"""
Search API Schemas (Phase 14)
===========================
"""

from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

class SearchQueryRequest(BaseModel):
    query: str = Field(default="", description="Text to search across entities")
    
    # Entity filters
    entity_types: Optional[List[str]] = Field(default=None, description="['projects', 'units', 'assemblies', 'packages', 'rfis']")
    
    # Operational filters
    project_id: Optional[uuid.UUID] = Field(default=None)
    status: Optional[str] = Field(default=None)
    date_from: Optional[datetime] = Field(default=None)
    date_to: Optional[datetime] = Field(default=None)
    
    # Hierarchy filters
    building_id: Optional[uuid.UUID] = Field(default=None)
    floor_id: Optional[uuid.UUID] = Field(default=None)
    unit_type_id: Optional[uuid.UUID] = Field(default=None)
    assembly_type: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=200)


class SearchResultItem(BaseModel):
    id: uuid.UUID
    entity_type: str
    title: str
    subtitle: Optional[str] = None
    project_id: uuid.UUID
    status: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total_count: int
