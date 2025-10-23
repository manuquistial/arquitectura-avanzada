"""Shared data models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Event types."""

    CITIZEN_REGISTERED = "citizen.registered"
    CITIZEN_UNREGISTERED = "citizen.unregistered"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_SIGNED = "document.signed"
    DOCUMENT_AUTHENTICATED = "document.authenticated"
    DOCUMENT_SHARED = "document.shared"
    TRANSFER_INITIATED = "transfer.initiated"
    TRANSFER_CONFIRMED = "transfer.confirmed"
    TRANSFER_FAILED = "transfer.failed"


class BaseEvent(BaseModel):
    """Base event model."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aggregate_id: str
    aggregate_type: str
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any]


class CitizenStatus(str, Enum):
    """Citizen status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"


class DocumentStatus(str, Enum):
    """Document status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    SIGNED = "signed"
    AUTHENTICATED = "authenticated"
    SHARED = "shared"
    TRANSFERRED = "transferred"
    ERROR = "error"


class TransferStatus(str, Enum):
    """Transfer status."""

    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SignatureType(str, Enum):
    """Signature type."""

    XADES = "xades"
    CADES = "cades"
    PADES = "pades"


class Citizen(BaseModel):
    """Citizen model."""

    id: int  # Citizen ID (cédula)
    name: str
    address: str
    email: str
    operator_id: str
    operator_name: str
    status: CitizenStatus = CitizenStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    """Document model."""

    id: UUID
    citizen_id: int
    title: str
    description: str | None = None
    s3_key: str
    s3_bucket: str
    file_size: int
    mime_type: str
    sha256: str
    status: DocumentStatus
    signature_type: SignatureType | None = None
    signature_data: dict[str, Any] | None = None
    authenticated_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Transfer(BaseModel):
    """Transfer model."""

    id: UUID
    citizen_id: int
    citizen_name: str
    citizen_email: str
    source_operator_id: str
    source_operator_name: str
    destination_operator_id: str
    destination_operator_name: str
    destination_endpoint: str
    destination_confirm_endpoint: str
    status: TransferStatus
    document_count: int
    idempotency_key: UUID
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_message: str | None = None



