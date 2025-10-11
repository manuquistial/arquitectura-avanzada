"""Database models for ingestion service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model."""
    pass


class DocumentMetadata(Base):
    """Document metadata table."""

    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    citizen_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Storage location
    blob_name: Mapped[str] = mapped_column(String(500), nullable=False)  # Azure blob name or S3 key
    storage_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="azure")
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="pending"  # pending, uploaded, verified, indexed
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

