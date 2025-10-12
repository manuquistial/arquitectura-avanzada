"""Database models for signature service."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
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

