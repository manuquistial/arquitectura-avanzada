"""Citizen schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class CitizenBase(BaseModel):
    """Base citizen schema."""

    id: int = Field(..., description="Citizen ID (cédula)", gt=0)
    name: str = Field(..., description="Full name", min_length=1, max_length=255)
    address: str = Field(..., description="Address", min_length=1, max_length=500)
    email: EmailStr = Field(..., description="Email")

    @field_validator("id")
    @classmethod
    def validate_citizen_id(cls, v: int) -> int:
        """Validate citizen ID has exactly 10 digits (required by GovCarpeta API)."""
        id_str = str(v)
        if len(id_str) != 10:
            raise ValueError(
                f"Citizen ID must be exactly 10 digits, got {len(id_str)} digits"
            )
        if not id_str.isdigit():
            raise ValueError("Citizen ID must contain only digits")
        return v

    @field_validator("name", "address")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate string fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        return v.strip()


class CitizenCreate(CitizenBase):
    """Create citizen schema."""

    operator_id: str = Field(..., description="Operator ID", min_length=1, max_length=100)
    operator_name: str = Field(..., description="Operator name", min_length=1, max_length=255)

    @field_validator("operator_id", "operator_name")
    @classmethod
    def validate_operator_fields(cls, v: str, info) -> str:
        """Validate operator fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        return v.strip()


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

