"""Signature service schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class SignDocumentRequest(BaseModel):
    """Request to sign a document."""
    
    document_id: str = Field(..., min_length=1, description="Document ID in blob storage")
    citizen_id: str = Field(..., min_length=1, max_length=20, description="Citizen ID")
    signature_type: str = Field(default="PAdES", description="Signature type: PAdES, XAdES, CAdES")
    document_title: str = Field(..., min_length=1, description="Document title for hub")
    
    @validator('signature_type')
    def validate_signature_type(cls, v):
        """Validate signature type."""
        valid_types = ["PAdES", "XAdES", "CAdES"]
        if v not in valid_types:
            raise ValueError(f"Invalid signature type: {v}. Must be one of {valid_types}")
        return v
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document ID."""
        if not v or v.strip() == "":
            raise ValueError("Document ID cannot be empty")
        return v.strip()
    
    @validator('document_title')
    def validate_document_title(cls, v):
        """Validate document title."""
        if not v or v.strip() == "":
            raise ValueError("Document title cannot be empty")
        return v.strip()


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
    
    signed_document_id: str = Field(..., min_length=1, description="Signed document ID")
    
    @validator('signed_document_id')
    def validate_signed_document_id(cls, v):
        """Validate signed document ID."""
        if not v or v.strip() == "":
            raise ValueError("Signed document ID cannot be empty")
        return v.strip()


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
    
    citizen_id: str
    signed_document_id: str
    document_title: str


class AuthenticateDocumentResponse(BaseModel):
    """Response from hub authentication."""
    
    success: bool
    hub_message: Optional[str] = None
    authenticated_at: Optional[datetime] = None

