"""SQLAlchemy models for transfer service."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum
import enum

from app.database import Base


class TransferStatus(str, enum.Enum):
    """Transfer status enum."""
    PENDING = "pending"
    CONFIRMED = "confirmed"  # Destination confirmed receipt
    PENDING_UNREGISTER = "pending_unregister"  # Waiting to unregister from hub
    SUCCESS = "success"  # Fully completed (unregistered from hub)
    FAILED = "failed"


class Transfer(Base):
    """Transfer record model.
    
    Tracks all P2P transfer operations between operators.
    """
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    citizen_id = Column(Integer, nullable=False, index=True)  # Citizen ID being transferred
    citizen_name = Column(String, nullable=False)
    citizen_email = Column(String, nullable=False)
    
    # Transfer direction (incoming/outgoing)
    direction = Column(String, nullable=False)  # "incoming" or "outgoing"
    
    # Source and destination operators
    source_operator_id = Column(String, nullable=True)
    source_operator_name = Column(String, nullable=True)
    destination_operator_id = Column(String, nullable=True)
    destination_operator_name = Column(String, nullable=True)
    
    # Transfer metadata
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    confirm_url = Column(String, nullable=True)  # For outgoing transfers
    
    # Status tracking
    status = Column(SQLEnum(TransferStatus), default=TransferStatus.PENDING, nullable=False)
    
    # Documents transferred (JSON-serialized list of doc IDs)
    document_ids = Column(Text, nullable=True)  # Store as JSON string
    
    # Timestamps
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)  # When destination confirmed
    unregistered_at = Column(DateTime, nullable=True)  # When unregistered from hub
    completed_at = Column(DateTime, nullable=True)  # Final completion
    
    # Error info (if failed)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)  # For hub unregister retries

