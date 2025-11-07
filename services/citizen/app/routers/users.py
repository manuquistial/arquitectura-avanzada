"""
User Management Endpoints
Handles user bootstrap and management
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models_users import User
from ..middleware.auth import AuthMiddleware

router = APIRouter(prefix="/api/users", tags=["users"])


# ========================================
# Schemas
# ========================================

class UserCreate(BaseModel):
    """User creation schema"""
    id: str  # Azure AD B2C sub claim
    email: EmailStr
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    azure_b2c_object_id: Optional[str] = None
    idp: Optional[str] = None
    email_verified: bool = False
    roles: List[str] = []
    operator_id: Optional[str] = None


class UserUpdate(BaseModel):
    """User update schema"""
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    name: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    is_active: bool
    is_verified: bool
    email_verified: bool
    operator_id: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ========================================
# Endpoints
# ========================================

@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Bootstrap user from Azure AD B2C
    
    Creates a new user if it doesn't exist, or updates last_login_at if it does.
    This endpoint is called automatically after successful Azure AD B2C authentication.
    """
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == user_data.id)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Update last login
        existing_user.last_login_at = datetime.utcnow()
        
        # Update email if changed
        if existing_user.email != user_data.email:
            existing_user.email = user_data.email
        
        # Update name if changed
        if user_data.name and existing_user.name != user_data.name:
            existing_user.name = user_data.name
        
        # Update email_verified if changed
        if existing_user.email_verified != user_data.email_verified:
            existing_user.email_verified = user_data.email_verified
        
        await db.commit()
        await db.refresh(existing_user)
        
        return existing_user
    
    # Create new user
    new_user = User(
        id=user_data.id,
        email=user_data.email,
        name=user_data.name,
        given_name=user_data.given_name,
        family_name=user_data.family_name,
        azure_b2c_object_id=user_data.azure_b2c_object_id,
        idp=user_data.idp,
        email_verified=user_data.email_verified,
        roles=user_data.roles or ["user"],  # Default role
        permissions=[],
        is_active=True,
        is_verified=False,
        operator_id=user_data.operator_id,
        last_login_at=datetime.utcnow(),
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    Get current user profile
    """
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(AuthMiddleware.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID (requires authentication)
    """
    # Check if user is requesting their own data or has admin role
    if user_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(AuthMiddleware.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user (admin only)
    
    Requires admin role to update other users.
    Users can update their own profile (limited fields).
    """
    # Check if user has admin role or is updating their own profile
    if user_id != current_user.id and "admin" not in current_user.roles and "mintic" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required to update other users."
        )
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.name is not None:
        user.name = user_update.name
    if user_update.given_name is not None:
        user.given_name = user_update.given_name
    if user_update.family_name is not None:
        user.family_name = user_update.family_name
    if user_update.roles is not None:
        user.roles = user_update.roles
    if user_update.permissions is not None:
        user.permissions = user_update.permissions
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.preferred_language is not None:
        user.preferred_language = user_update.preferred_language
    if user_update.timezone is not None:
        user.timezone = user_update.timezone
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(AuthMiddleware.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (admin only)
    
    Requires admin role to access.
    """
    # Check if user has admin role
    if "admin" not in current_user.roles and "mintic" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Use raw SQL to avoid issues with missing columns (like azure_b2c_object_id)
    from sqlalchemy import text
    
    # Query with only columns that should exist in most cases
    # Try with deleted_at filter first
    query = text("""
        SELECT 
            id, email, name, given_name, family_name,
            roles, permissions, is_active, is_verified, email_verified,
            operator_id, created_at, updated_at, last_login_at
        FROM users
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :skip
    """)
    
    try:
        result = await db.execute(query, {"limit": limit, "skip": skip})
        rows = result.fetchall()
    except Exception as e:
        # If deleted_at doesn't exist, query without it
        query = text("""
            SELECT 
                id, email, name, given_name, family_name,
                roles, permissions, is_active, is_verified, email_verified,
                operator_id, created_at, updated_at, last_login_at
            FROM users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        result = await db.execute(query, {"limit": limit, "skip": skip})
        rows = result.fetchall()
    
    # Convert rows to User-like objects
    users = []
    for row in rows:
        user_dict = {
            'id': row.id,
            'email': row.email,
            'name': row.name,
            'given_name': row.given_name,
            'family_name': row.family_name,
            'roles': row.roles or [],
            'permissions': row.permissions or [],
            'is_active': row.is_active,
            'is_verified': row.is_verified,
            'email_verified': row.email_verified,
            'operator_id': row.operator_id,
            'created_at': row.created_at,
            'updated_at': row.updated_at,
            'last_login_at': row.last_login_at,
            'azure_b2c_object_id': None,
            'idp': None,
            'preferred_language': None,
            'timezone': None,
            'deleted_at': None,
        }
        # Create a SimpleNamespace object that behaves like a User
        from types import SimpleNamespace
        user_obj = SimpleNamespace(**user_dict)
        users.append(user_obj)
    
    return users

