"""Database models for Metadata Service.

This service uses the same DocumentMetadata model as Ingestion Service
since they share the same database table.
"""

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model."""
    pass


class DocumentMetadata(Base):
    """Document metadata table.
    
    This is the same table used by Ingestion Service.
    Metadata Service reads and updates this table.
    """

    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    citizen_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Storage location
    blob_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="azure")
    
    # Status (deprecated, use 'state' instead)
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="pending"
    )
    is_uploaded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # WORM and Retention
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="UNSIGNED",
        index=True
    )
    worm_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    retention_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True
    )
    hub_signature_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    legal_hold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    lifecycle_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Hot",
        index=True
    )
    
    # Metadata
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

