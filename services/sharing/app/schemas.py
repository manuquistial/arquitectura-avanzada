"""Schemas for sharing service."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class CreateSharePackageRequest(BaseModel):
    """Request to create a share package."""
    
    owner_email: EmailStr = Field(..., description="Owner email")
    document_ids: List[str] = Field(..., description="Document IDs to share", min_length=1)
    expires_at: datetime = Field(..., description="Expiration timestamp")
    audience: Optional[str] = Field(None, description="Specific email or 'public'")
    requires_auth: bool = Field(default=False, description="Require authentication")
    watermark_enabled: bool = Field(default=False, description="Enable watermark")
    watermark_text: Optional[str] = Field(None, description="Custom watermark text")


class CreateSharePackageResponse(BaseModel):
    """Response after creating share package."""
    
    package_id: int
    token: str
    shortlink: str
    expires_at: datetime
    document_count: int


class SharePackageInfo(BaseModel):
    """Share package information."""
    
    package_id: int
    token: str
    owner_email: str
    document_ids: List[str]
    audience: Optional[str]
    expires_at: datetime
    is_active: bool
    access_count: int
    created_at: datetime


class SharePackageDocument(BaseModel):
    """Document in share package with SAS URL."""
    
    document_id: str
    filename: str
    content_type: str
    size: int
    sas_url: str
    watermarked: bool = False


class SharePackageAccess(BaseModel):
    """Response for accessing share package."""
    
    package_id: int
    owner_email: str
    expires_at: datetime
    documents: List[SharePackageDocument]
    watermark_text: Optional[str] = None

