"""Read models for CQRS projections (optimized for queries)."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, Index
from app.database import Base


class ReadDocument(Base):
    """Optimized read model for documents.
    
    Denormalized view combining data from multiple events:
    - document.uploaded
    - document.authenticated
    - citizen.registered
    """
    __tablename__ = "read_documents"
    
    # Primary key
    id = Column(String, primary_key=True)  # document_id
    
    # Document info
    citizen_id = Column(Integer, nullable=False, index=True)
    citizen_name = Column(String, nullable=True)  # Denormalized from citizen event
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    title = Column(String, nullable=True)
    
    # Hash and signature
    sha256_hash = Column(String(64), nullable=True, index=True)
    is_authenticated = Column(Boolean, default=False)
    authenticated_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default="uploaded")
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_read_doc_citizen_status', 'citizen_id', 'status'),
        Index('idx_read_doc_uploaded_at', 'uploaded_at'),
        Index('idx_read_doc_authenticated', 'is_authenticated'),
    )


class ReadTransfer(Base):
    """Optimized read model for transfers.
    
    Denormalized view combining data from:
    - transfer.requested
    - transfer.confirmed
    """
    __tablename__ = "read_transfers"
    
    # Primary key
    id = Column(Integer, primary_key=True)  # transfer_id
    
    # Transfer info
    citizen_id = Column(Integer, nullable=False, index=True)
    citizen_name = Column(String, nullable=True)
    
    # Operators
    source_operator_id = Column(String, nullable=False)
    source_operator_name = Column(String, nullable=True)
    destination_operator_id = Column(String, nullable=False)
    destination_operator_name = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="requested")  # requested, confirmed, failed
    success = Column(Boolean, nullable=True)
    
    # Metadata
    document_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_read_transfer_citizen_status', 'citizen_id', 'status'),
        Index('idx_read_transfer_requested_at', 'requested_at'),
    )

