"""Pydantic schemas for metadata service."""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Document metadata response."""
    
    id: str
    filename: str
    content_type: str
    size: int = Field(alias="size_bytes")
    status: str
    description: str | None = None
    tags: str | None = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentListResponse(BaseModel):
    """Document list response."""
    
    documents: list[DocumentResponse]
    total: int


class SearchResult(BaseModel):
    """Search result."""
    
    id: str
    title: str
    description: str | None = None
    filename: str
    created_at: datetime
    score: float


class SearchResponse(BaseModel):
    """Search response."""
    
    results: list[SearchResult]
    total: int
    took_ms: int

