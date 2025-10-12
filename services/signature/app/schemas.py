"""Signature service schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SignDocumentRequest(BaseModel):
    """Request to sign a document."""
    
    document_id: str = Field(..., description="Document ID in blob storage")
    citizen_id: int = Field(..., description="Citizen ID")
    signature_type: str = Field(default="PAdES", description="Signature type: PAdES, XAdES, CAdES")
    document_title: str = Field(..., description="Document title for hub")


class SignDocumentResponse(BaseModel):
    """Response after signing a document."""
    
    document_id: str
    signed_document_id: str
    sha256_hash: str
    signature_type: str
    signed_at: datetime
    signed_blob_url: str


class VerifySignatureRequest(BaseModel):
    """Request to verify a signature."""
    
    signed_document_id: str = Field(..., description="Signed document ID")


class VerifySignatureResponse(BaseModel):
    """Response after verifying a signature."""
    
    is_valid: bool
    sha256_hash: str
    signature_type: str
    signed_at: Optional[datetime] = None
    verified_at: datetime
    details: Optional[str] = None


class AuthenticateDocumentRequest(BaseModel):
    """Internal request to authenticate document with hub."""
    
    citizen_id: int
    signed_document_id: str
    document_title: str


class AuthenticateDocumentResponse(BaseModel):
    """Response from hub authentication."""
    
    success: bool
    hub_message: Optional[str] = None
    authenticated_at: Optional[datetime] = None

