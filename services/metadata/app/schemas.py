"""Pydantic schemas for metadata service."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentMetadataCreate(BaseModel):
    """Document metadata creation schema."""
    
    citizen_id: str
    title: str
    filename: str
    content_type: str
    size_bytes: int
    sha256_hash: Optional[str] = None
    issuer: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None


class DocumentMetadataResponse(BaseModel):
    """Document metadata response schema."""
    
    id: str
    citizen_id: str
    title: str
    filename: str
    content_type: str
    size_bytes: Optional[int] = None  # Can be NULL in database
    sha256_hash: Optional[str] = None  # Can be NULL in database
    blob_name: str
    storage_provider: str
    status: str
    is_uploaded: bool
    state: str
    worm_locked: bool
    signed_at: Optional[datetime] = None
    retention_until: Optional[date] = None
    hub_signature_ref: Optional[str] = None
    legal_hold: bool
    lifecycle_tier: str
    description: Optional[str] = None  # Can be NULL in database
    tags: Optional[str] = None  # Can be NULL in database
    is_deleted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


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


class DocumentSearchResponse(BaseModel):
    """Document search response."""
    
    documents: list[SearchResult]
    total: int
    page: int
    page_size: int
    took_ms: int

