"""Authentication service with database integration."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserSession, UserToken, AuditLog
from app.database import deserialize_json_field, serialize_json_field

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service with database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password."""
        try:
            # Get user by email
            result = await self.db.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await self._log_auth_event(None, "login_attempt", {"email": email}, False, "User not found")
                return None
            
            # Verify password (in production, use proper password hashing)
            if not self._verify_password(password, user.password_hash):
                await self._log_auth_event(user.id, "login_attempt", {"email": email}, False, "Invalid password")
                return None
            
            # Update last login
            await self.db.execute(
                update(User)
                .where(User.id == user.id)
                .values(last_login=datetime.utcnow())
            )
            await self.db.commit()
            
            # Log successful login
            await self._log_auth_event(user.id, "login_success", {"email": email}, True)
            
            return {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "given_name": user.given_name,
                "family_name": user.family_name,
                "roles": deserialize_json_field(user.roles),
                "permissions": deserialize_json_field(user.permissions),
                "is_verified": user.is_verified
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self._log_auth_event(None, "login_error", {"email": email}, False, str(e))
            return None

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        try:
            # Check if user already exists
            result = await self.db.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValueError("User with this email already exists")
            
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=self._hash_password(user_data["password"]),
                name=user_data["name"],
                given_name=user_data.get("given_name"),
                family_name=user_data.get("family_name"),
                roles=serialize_json_field(user_data.get("roles", ["user"])),
                permissions=serialize_json_field(user_data.get("permissions", ["read"])),
                is_active=True,
                is_verified=False
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            # Log user creation
            await self._log_auth_event(user.id, "user_created", {"email": user.email}, True)
            
            return {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "given_name": user.given_name,
                "family_name": user.family_name,
                "roles": deserialize_json_field(user.roles),
                "permissions": deserialize_json_field(user.permissions)
            }
            
        except Exception as e:
            logger.error(f"User creation error: {e}")
            await self.db.rollback()
            raise

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            return {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "given_name": user.given_name,
                "family_name": user.family_name,
                "roles": deserialize_json_field(user.roles),
                "permissions": deserialize_json_field(user.permissions),
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user information."""
        try:
            # Get existing user
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Update fields
            update_values = {}
            if "name" in update_data:
                update_values["name"] = update_data["name"]
            if "given_name" in update_data:
                update_values["given_name"] = update_data["given_name"]
            if "family_name" in update_data:
                update_values["family_name"] = update_data["family_name"]
            if "roles" in update_data:
                update_values["roles"] = serialize_json_field(update_data["roles"])
            if "permissions" in update_data:
                update_values["permissions"] = serialize_json_field(update_data["permissions"])
            
            if update_values:
                update_values["updated_at"] = datetime.utcnow()
                await self.db.execute(
                    update(User).where(User.id == user_id).values(**update_values)
                )
                await self.db.commit()
                
                # Log update
                await self._log_auth_event(user_id, "user_updated", update_data, True)
            
            # Return updated user
            return await self.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f"Update user error: {e}")
            await self.db.rollback()
            raise

    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> str:
        """Create a new user session."""
        try:
            import uuid
            session_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            session = UserSession(
                user_id=user_id,
                session_id=session_id,
                expires_at=expires_at,
                ip_address=session_data.get("ip_address"),
                user_agent=session_data.get("user_agent")
            )
            
            self.db.add(session)
            await self.db.commit()
            
            # Log session creation
            await self._log_auth_event(user_id, "session_created", {"session_id": session_id}, True)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            await self.db.rollback()
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        try:
            result = await self.db.execute(
                select(UserSession, User)
                .join(User, UserSession.user_id == User.id)
                .where(
                    UserSession.session_id == session_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow(),
                    User.is_active == True
                )
            )
            row = result.first()
            
            if not row:
                return None
            
            session, user = row
            
            # Update last activity
            await self.db.execute(
                update(UserSession)
                .where(UserSession.id == session.id)
                .values(last_activity=datetime.utcnow())
            )
            await self.db.commit()
            
            return {
                "session_id": session.session_id,
                "user_id": str(session.user_id),
                "expires_at": session.expires_at.isoformat(),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "given_name": user.given_name,
                    "family_name": user.family_name,
                    "roles": deserialize_json_field(user.roles),
                    "permissions": deserialize_json_field(user.permissions)
                }
            }
            
        except Exception as e:
            logger.error(f"Get session error: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete user session."""
        try:
            result = await self.db.execute(
                select(UserSession).where(UserSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            # Soft delete session
            await self.db.execute(
                update(UserSession)
                .where(UserSession.id == session.id)
                .values(is_active=False)
            )
            await self.db.commit()
            
            # Log session deletion
            await self._log_auth_event(session.user_id, "session_deleted", {"session_id": session_id}, True)
            
            return True
            
        except Exception as e:
            logger.error(f"Delete session error: {e}")
            await self.db.rollback()
            return False

    async def refresh_session(self, session_id: str) -> bool:
        """Refresh session TTL."""
        try:
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.session_id == session_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return False
            
            # Extend session by 24 hours
            new_expires_at = datetime.utcnow() + timedelta(hours=24)
            await self.db.execute(
                update(UserSession)
                .where(UserSession.id == session.id)
                .values(
                    expires_at=new_expires_at,
                    last_activity=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Refresh session error: {e}")
            await self.db.rollback()
            return False

    def _hash_password(self, password: str) -> str:
        """Hash password (in production, use proper hashing like bcrypt)."""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return self._hash_password(password) == password_hash

    async def _log_auth_event(
        self, 
        user_id: Optional[int], 
        event_type: str, 
        event_data: Dict[str, Any], 
        success: bool, 
        error_message: Optional[str] = None
    ):
        """Log authentication event."""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                event_type=event_type,
                event_data=json.dumps(event_data),
                success=success,
                error_message=error_message
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")
            # Don't raise exception for logging failures
