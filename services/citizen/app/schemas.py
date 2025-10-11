"""Citizen schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CitizenBase(BaseModel):
    """Base citizen schema."""

    id: int = Field(..., description="Citizen ID (cédula)")
    name: str = Field(..., description="Full name")
    address: str = Field(..., description="Address")
    email: EmailStr = Field(..., description="Email")


class CitizenCreate(CitizenBase):
    """Create citizen schema."""

    operator_id: str = Field(..., description="Operator ID")
    operator_name: str = Field(..., description="Operator name")


class CitizenResponse(CitizenBase):
    """Citizen response schema."""

    operator_id: str
    operator_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class CitizenUnregister(BaseModel):
    """Unregister citizen schema."""

    id: int = Field(..., description="Citizen ID")
    operator_id: str = Field(..., description="Operator ID")

