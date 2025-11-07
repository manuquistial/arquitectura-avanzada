"""Pydantic schemas for Metadata Service API."""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentMetadataResponse(BaseModel):
    """Document metadata response schema."""
    
    id: str
    citizen_id: str
    title: str
    filename: str
    content_type: str
    size_bytes: Optional[int] = None
    sha256_hash: Optional[str] = None
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
    description: Optional[str] = None
    tags: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentMetadataListResponse(BaseModel):
    """List of document metadata response."""
    
    documents: List[DocumentMetadataResponse]
    total: int
    citizen_id: str


class MetadataSearchRequest(BaseModel):
    """Metadata search request."""
    
    citizen_id: Optional[str] = None
    query: Optional[str] = None
    state: Optional[str] = None
    content_type: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MetadataSearchResponse(BaseModel):
    """Metadata search response."""
    
    documents: List[DocumentMetadataResponse]
    total: int
    limit: int
    offset: int

