"""MinTIC Client models matching exact API specs."""

from pydantic import BaseModel, Field


# Request Models
class RegisterCitizenRequest(BaseModel):
    """Register citizen request."""

    id: int = Field(..., description="Citizen ID (cédula)")
    name: str = Field(..., description="Citizen full name")
    address: str = Field(..., description="Citizen address")
    email: str = Field(..., description="Citizen email")
    operatorId: str = Field(..., description="Operator ID")
    operatorName: str = Field(..., description="Operator name")


class UnregisterCitizenRequest(BaseModel):
    """Unregister citizen request."""

    id: int = Field(..., description="Citizen ID (cédula)")
    operatorId: str = Field(..., description="Operator ID")
    operatorName: str = Field(..., description="Operator name")


class AuthenticateDocumentRequest(BaseModel):
    """Authenticate document request."""

    idCitizen: int = Field(..., description="Citizen ID")
    UrlDocument: str = Field(..., description="S3 presigned URL")
    documentTitle: str = Field(..., description="Document title")


class RegisterOperatorRequest(BaseModel):
    """Register operator request."""

    name: str = Field(..., description="Operator name")
    address: str = Field(..., description="Operator address")
    contactMail: str = Field(..., description="Contact email")
    participants: list[str] = Field(..., description="List of participants")


class RegisterTransferEndPointRequest(BaseModel):
    """Register transfer endpoint request."""

    idOperator: str = Field(..., description="Operator ID")
    endPoint: str = Field(..., description="Transfer endpoint URL")
    endPointConfirm: str = Field(..., description="Transfer confirmation endpoint URL")


# Response Models
class OperatorInfo(BaseModel):
    """Operator information."""

    OperatorId: str
    OperatorName: str
    transferAPIURL: str


class MinTICResponse(BaseModel):
    """Generic MinTIC response."""

    status_code: int
    message: str
    success: bool

