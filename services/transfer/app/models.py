"""Transfer service models."""

from pydantic import BaseModel, Field


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

