"""Citizen schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class CitizenBase(BaseModel):
    """Base citizen schema."""

    id: str = Field(..., description="Citizen ID (cédula)", min_length=10, max_length=10)
    name: str = Field(..., description="Full name", min_length=1, max_length=255)
    address: str = Field(..., description="Address", min_length=1, max_length=500)
    email: EmailStr = Field(..., description="Email")

    @field_validator("id")
    @classmethod
    def validate_citizen_id(cls, v: str) -> str:
        """Validate citizen ID has exactly 10 digits (required by GovCarpeta API)."""
        if len(v) != 10:
            raise ValueError(
                f"Citizen ID must be exactly 10 digits, got {len(v)} digits"
            )
        if not v.isdigit():
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

    password: str = Field(..., description="User password for authentication", min_length=8, max_length=128)
    # operator_id and operator_name are now optional - will be fetched from system config
    operator_id: str | None = Field(None, description="Operator ID (optional, will be fetched from system config if not provided)")
    operator_name: str | None = Field(None, description="Operator name (optional, will be fetched from system config if not provided)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets requirements."""
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")
        if len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v.strip()


class CitizenResponse(CitizenBase):
    """Citizen response schema."""

    operator_id: str
    operator_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitizenUnregister(BaseModel):
    """Unregister citizen schema."""

    id: str = Field(..., description="Citizen ID or User ID")
    operator_id: str | None = Field(None, description="Operator ID (optional, will be fetched from citizen or system config)")

