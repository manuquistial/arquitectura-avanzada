"""Database models for sharing service."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SharePackage(Base):
    """Shared document package."""
    
    __tablename__ = "share_packages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Shortlink token
    token = Column(String(32), unique=True, nullable=False, index=True)
    
    # Owner
    owner_email = Column(String, nullable=False, index=True)
    owner_citizen_id = Column(Integer, nullable=True)
    
    # Documents (array of document IDs)
    document_ids = Column(JSON, nullable=False)  # ["doc1", "doc2", ...]
    
    # Access control
    audience = Column(String, nullable=True)  # Specific email or "public"
    requires_auth = Column(Boolean, default=False)
    
    # SAS URLs (regenerated on access, not stored permanently)
    # Stored temporarily in Redis only
    
    # Watermark
    watermark_enabled = Column(Boolean, default=False)
    watermark_text = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Metadata
    created_by = Column(String, nullable=False)  # User sub from JWT
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    # Audit
    package_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (SQLAlchemy reserved)


class ShareAccessLog(Base):
    """Log of share package accesses."""
    
    __tablename__ = "share_access_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Package
    share_package_id = Column(Integer, nullable=False, index=True)
    token = Column(String, nullable=False)
    
    # Access info
    accessed_by_email = Column(String, nullable=True)
    accessed_by_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Result
    access_granted = Column(Boolean, default=False)
    denial_reason = Column(String, nullable=True)
    
    # Timestamp
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

