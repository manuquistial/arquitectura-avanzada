"""Authentication middleware for citizen service."""

import logging
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models_users import User

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware for JWT token validation."""

    @staticmethod
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """Get current user from JWT token."""
        try:
            # Extract token
            token = credentials.credentials
            
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Extract user ID
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            # Get user from database using raw SQL to avoid ORM issues with missing columns
            from sqlalchemy import text
            # Select only columns that definitely exist (based on migration 002_create_users)
            # Avoid email_verified, operator_id, last_login_at, etc. that might not exist
            # Ensure user_id is a string and cast both sides to VARCHAR for safe comparison
            user_id_str = str(user_id)  # Ensure it's always a string
            result = await db.execute(
                text("""
                    SELECT id, email, name, given_name, family_name, citizen_id,
                           roles, permissions, is_active, is_verified,
                           created_at, updated_at
                    FROM users
                    WHERE CAST(id AS TEXT) = CAST(:user_id AS TEXT)
                """),
                {"user_id": user_id_str}
            )
            
            row = result.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Create User-like object from row
            from types import SimpleNamespace
            # Create user object with only columns we selected
            user = SimpleNamespace(
                id=row.id,
                email=row.email,
                name=row.name if hasattr(row, 'name') else None,
                citizen_id=row.citizen_id if hasattr(row, 'citizen_id') else None,
                given_name=row.given_name if hasattr(row, 'given_name') else None,
                family_name=row.family_name if hasattr(row, 'family_name') else None,
                roles=row.roles if hasattr(row, 'roles') and row.roles else [],
                permissions=row.permissions if hasattr(row, 'permissions') and row.permissions else [],
                is_active=row.is_active if hasattr(row, 'is_active') else True,
                is_verified=row.is_verified if hasattr(row, 'is_verified') else False,
                email_verified=False,  # Default value if column doesn't exist
                operator_id=None,  # Default value if column doesn't exist
                created_at=row.created_at if hasattr(row, 'created_at') else None,
                updated_at=row.updated_at if hasattr(row, 'updated_at') else None,
                last_login_at=None  # Default value if column doesn't exist
            )
            
            return user
            
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )

    @staticmethod
    async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[User]:
        """Get current user from JWT token (optional)."""
        if not credentials:
            return None
        
        try:
            return await AuthMiddleware.get_current_user(credentials, db)
        except HTTPException:
            return None

    @staticmethod
    def require_roles(*required_roles: str):
        """Decorator to require specific roles."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Get current user from kwargs
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                # Check if user has required roles
                user_roles = getattr(current_user, 'roles', [])
                if not any(role in user_roles for role in required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {', '.join(required_roles)}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def require_permissions(*required_permissions: str):
        """Decorator to require specific permissions."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Get current user from kwargs
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                # Check if user has required permissions
                user_permissions = getattr(current_user, 'permissions', [])
                if not any(permission in user_permissions for permission in required_permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required permissions: {', '.join(required_permissions)}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
