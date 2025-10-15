"""Transfer service models."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


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

