"""Database models for signature service."""

from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Integer, String, Text, Boolean
from app.database import Base


class SignatureRecord(Base):
    """Signature and authentication record."""
    
    __tablename__ = "signature_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Document info
    document_id = Column(String, nullable=False, index=True)
    citizen_id = Column(Integer, nullable=False, index=True)
    document_title = Column(String, nullable=False)
    
    # Hash and signature
    sha256_hash = Column(String(64), nullable=False, index=True)
    signature_algorithm = Column(String, nullable=True)
    signature_value = Column(Text, nullable=True)  # Base64 encoded signature
    
    # SAS URL for hub
    sas_url = Column(Text, nullable=True)
    sas_expires_at = Column(DateTime, nullable=True)
    
    # Hub authentication
    hub_authenticated = Column(Boolean, default=False)
    hub_response = Column(Text, nullable=True)  # JSON response from hub
    hub_authenticated_at = Column(DateTime, nullable=True)
    
    # Timestamps
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentMetadata(Base):
    """Document metadata table (shared with ingestion service).
    
    This is a reference to the same table used by ingestion service.
    Signature service updates WORM fields when authenticating documents.
    """
    
    __tablename__ = "document_metadata"
    
    # Primary fields
    id = Column(String(255), primary_key=True)
    citizen_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=True)
    sha256_hash = Column(String(64), nullable=True)
    
    # Storage
    blob_name = Column(String(500), nullable=False)
    storage_provider = Column(String(20), nullable=False, default="azure")
    
    # Status (deprecated)
    status = Column(String(20), nullable=False, default="pending")
    
    # WORM and Retention (CRITICAL REQUIREMENT)
    state = Column(String(20), nullable=False, default="UNSIGNED", index=True)
    worm_locked = Column(Boolean, nullable=False, default=False, index=True)
    signed_at = Column(DateTime, nullable=True)
    retention_until = Column(Date, nullable=True, index=True)
    hub_signature_ref = Column(String(255), nullable=True)
    legal_hold = Column(Boolean, nullable=False, default=False)
    lifecycle_tier = Column(String(20), nullable=False, default="Hot")
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, nullable=False, default=False)

