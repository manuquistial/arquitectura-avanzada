"""Transfer service models."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum
import enum

from app.base import Base


# ============================================================================
# SQLAlchemy Database Models
# ============================================================================

class TransferStatus(str, enum.Enum):
    """Transfer status enum for database."""
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


# ============================================================================
# Pydantic API Models
# ============================================================================

class TransferCitizenRequest(BaseModel):
    """Transfer citizen request from source operator.

    POST /api/transferCitizen
    """

    id: int = Field(..., description="Citizen ID (cédula)")
    citizenName: str = Field(..., description="Citizen full name")
    citizenEmail: str = Field(..., description="Citizen email")
    urlDocuments: dict[str, list[str]] = Field(
        ..., description="Documents with presigned GET URLs"
    )
    confirmAPI: str = Field(..., description="Confirmation endpoint URL")


class TransferCitizenResponse(BaseModel):
    """Transfer citizen response."""

    message: str
    citizen_id: int


class TransferConfirmRequest(BaseModel):
    """Transfer confirmation request.

    POST /api/transferCitizenConfirm
    """

    id: int = Field(..., description="Citizen ID")
    req_status: int = Field(..., description="1=success, 0=failure")


class TransferConfirmResponse(BaseModel):
    """Transfer confirmation response."""

    message: str


class TransferStatus(str, Enum):
    """Transfer status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InitiateTransferRequest(BaseModel):
    """Initiate transfer request from frontend."""
    
    destination_operator_id: str = Field(..., description="Destination operator ID")
    citizen_id: str = Field(..., description="Citizen ID")
    citizen_email: str = Field(..., description="Citizen email")
    citizen_name: str = Field(..., description="Citizen full name")


class InitiateTransferResponse(BaseModel):
    """Initiate transfer response."""
    
    transfer_id: str = Field(..., description="Unique transfer ID")
    status: TransferStatus = Field(..., description="Initial transfer status")
    message: str = Field(..., description="Status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class TransferStatusResponse(BaseModel):
    """Transfer status response."""
    
    transfer_id: str = Field(..., description="Transfer ID")
    status: TransferStatus = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Transfer creation time")
    updated_at: datetime = Field(..., description="Last update time")


# OAuth 2.0 Models for Operator Authentication
class OperatorTokenRequest(BaseModel):
    """OAuth 2.0 token request for operators.
    
    POST /auth/token
    """
    client_id: str = Field(..., description="Operator client ID")
    client_secret: str = Field(..., description="Operator client secret")
    grant_type: str = Field(default="client_credentials", description="OAuth 2.0 grant type")


class OperatorTokenResponse(BaseModel):
    """OAuth 2.0 token response for operators."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class OperatorConfig(BaseModel):
    """Operator configuration for B2B transfers."""
    operator_id: str = Field(..., description="Unique operator identifier")
    operator_name: str = Field(..., description="Operator display name")
    client_id: str = Field(..., description="OAuth 2.0 client ID")
    client_secret: str = Field(..., description="OAuth 2.0 client secret")
    transfer_api_url: str = Field(..., description="Transfer endpoint URL")
    confirm_api_url: str = Field(..., description="Confirmation endpoint URL")
    is_active: bool = Field(default=True, description="Whether operator is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RegisterOperatorRequest(BaseModel):
    """Request to register a new operator."""
    operator_id: str = Field(..., description="Unique operator identifier")
    operator_name: str = Field(..., description="Operator display name")
    client_id: str = Field(..., description="OAuth 2.0 client ID")
    client_secret: str = Field(..., description="OAuth 2.0 client secret")
    transfer_api_url: str = Field(..., description="Transfer endpoint URL")
    confirm_api_url: str = Field(..., description="Confirmation endpoint URL")


class RegisterOperatorResponse(BaseModel):
    """Response for operator registration."""
    message: str = Field(..., description="Registration status message")
    operator_id: str = Field(..., description="Registered operator ID")
    status: str = Field(..., description="Registration status")

