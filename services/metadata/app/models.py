"""Database models - shared with ingestion service for Azure PostgreSQL."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model."""
    pass


class DocumentMetadata(Base):
    """Document metadata table - Same as ingestion service for Azure PostgreSQL."""

    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    citizen_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Storage location
    blob_name: Mapped[str] = mapped_column(String(500), nullable=False)  # Azure blob name or S3 key
    storage_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="azure")
    
    # Status (deprecated, use 'state' instead)
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="pending"  # pending, uploaded, verified, indexed
    )
    is_uploaded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False  # True when file has been uploaded to storage
    )
    
    # WORM and Retention (REQUERIMIENTO CRÍTICO)
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="UNSIGNED",  # UNSIGNED (editable, TTL 30d) | SIGNED (inmutable, 5y)
        index=True
    )
    worm_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,  # True = Write Once Read Many (inmutable)
        index=True
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True  # Timestamp when document was signed
    )
    retention_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,  # Auto-calculated: UNSIGNED=created+30d, SIGNED=signed+5y
        index=True
    )
    hub_signature_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True  # Reference from hub authenticateDocument response
    )
    legal_hold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False  # Prevents deletion even after retention expires
    )
    lifecycle_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Hot",  # Hot (0-90d) | Cool (90-365d) | Archive (365d+)
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

