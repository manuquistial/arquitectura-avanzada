"""
User Model for Azure AD B2C Integration
Stores user information from Azure AD B2C
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, String, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """
    User model for Azure AD B2C authenticated users
    
    Fields:
    - id: Azure AD B2C user ID (sub claim)
    - email: User email
    - name: Full name
    - roles: List of roles for ABAC
    - permissions: List of permissions for ABAC
    """
    
    __tablename__ = "users"
    
    # Primary key - Azure AD B2C sub claim
    id: Mapped[str] = mapped_column(String(255), primary_key=True, comment="Azure AD B2C user ID (sub claim)")
    
    # Basic user info
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    given_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    family_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Azure AD B2C specific
    azure_b2c_object_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    idp: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Identity Provider (Azure AD, Google, etc.)"
    )
    
    # ABAC - Roles and Permissions
    roles: Mapped[List[str]] = mapped_column(
        ARRAY(String), nullable=False, default=[], server_default="{}"
    )
    permissions: Mapped[List[str]] = mapped_column(
        ARRAY(String), nullable=False, default=[], server_default="{}"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    # Metadata
    operator_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Operator ID for multi-tenant"
    )
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="es")
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="America/Bogota")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="Soft delete"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, roles={self.roles})>"
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return "admin" in self.roles
    
    def is_operator(self) -> bool:
        """Check if user is operator"""
        return "operator" in self.roles or "admin" in self.roles

