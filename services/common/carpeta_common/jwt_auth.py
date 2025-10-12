"""
JWT Authentication Middleware for Backend Services
Validates Azure AD B2C JWT tokens
"""

import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class JWTValidator:
    """
    JWT Token Validator for Azure AD B2C
    
    Validates JWT tokens issued by Azure AD B2C
    Caches JWKS for performance
    """
    
    def __init__(
        self,
        tenant_name: str,
        tenant_id: str,
        client_id: str,
        user_flow: str = "B2C_1_signupsignin1"
    ):
        self.tenant_name = tenant_name
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.user_flow = user_flow
        
        # JWKS endpoint
        self.jwks_url = (
            f"https://{tenant_name}.b2clogin.com/{tenant_name}.onmicrosoft.com/"
            f"{user_flow}/discovery/v2.0/keys"
        )
        
        # JWKS client (caches keys)
        self.jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)
        
        logger.info(f"JWT Validator initialized for tenant: {tenant_name}")
    
    def validate_token(self, token: str) -> dict:
        """
        Validate JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token payload
        
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            logger.debug(f"Token validated for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            logger.warning("Invalid audience")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class JWTBearer:
    """
    FastAPI Dependency for JWT Authentication
    
    Usage:
        from carpeta_common.jwt_auth import get_current_user
        
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["sub"]}
    """
    
    def __init__(self, validator: JWTValidator):
        self.validator = validator
    
    async def __call__(
        self,
        authorization: Optional[str] = Header(None)
    ) -> dict:
        """
        Extract and validate JWT from Authorization header
        
        Args:
            authorization: Authorization header value
        
        Returns:
            Decoded token payload
        
        Raises:
            HTTPException: If token is missing or invalid
        """
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        scheme, _, token = authorization.partition(" ")
        
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token
        return self.validator.validate_token(token)


# Helper functions

def create_jwt_validator(
    tenant_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    user_flow: Optional[str] = None
) -> JWTValidator:
    """
    Create JWT validator from environment variables
    
    Args:
        tenant_name: Azure AD B2C tenant name (or from AZURE_AD_B2C_TENANT_NAME env)
        tenant_id: Azure AD B2C tenant ID (or from AZURE_AD_B2C_TENANT_ID env)
        client_id: Azure AD B2C client ID (or from AZURE_AD_B2C_CLIENT_ID env)
        user_flow: User flow name (or from AZURE_AD_B2C_PRIMARY_USER_FLOW env)
    
    Returns:
        JWTValidator instance
    """
    import os
    
    tenant_name = tenant_name or os.getenv("AZURE_AD_B2C_TENANT_NAME")
    tenant_id = tenant_id or os.getenv("AZURE_AD_B2C_TENANT_ID")
    client_id = client_id or os.getenv("AZURE_AD_B2C_CLIENT_ID")
    user_flow = user_flow or os.getenv("AZURE_AD_B2C_PRIMARY_USER_FLOW", "B2C_1_signupsignin1")
    
    if not all([tenant_name, tenant_id, client_id]):
        raise ValueError(
            "Missing Azure AD B2C configuration. "
            "Set AZURE_AD_B2C_TENANT_NAME, AZURE_AD_B2C_TENANT_ID, and AZURE_AD_B2C_CLIENT_ID"
        )
    
    return JWTValidator(
        tenant_name=tenant_name,
        tenant_id=tenant_id,
        client_id=client_id,
        user_flow=user_flow
    )


def create_jwt_bearer() -> JWTBearer:
    """
    Create JWT bearer dependency
    
    Returns:
        JWTBearer instance
    """
    validator = create_jwt_validator()
    return JWTBearer(validator)


# Global instance (initialized on first use)
_jwt_bearer: Optional[JWTBearer] = None


def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    FastAPI dependency to get current user from JWT
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["sub"], "email": user["email"]}
    
    Returns:
        Decoded token payload with user info
    """
    global _jwt_bearer
    
    if _jwt_bearer is None:
        _jwt_bearer = create_jwt_bearer()
    
    # Call the JWT bearer dependency
    import asyncio
    if asyncio.iscoroutinefunction(_jwt_bearer.__call__):
        return asyncio.create_task(_jwt_bearer(authorization))
    else:
        return _jwt_bearer(authorization)


# Role-based access control helpers

def require_role(required_role: str):
    """
    FastAPI dependency to require specific role
    
    Usage:
        @app.get("/admin")
        async def admin_route(
            user: dict = Depends(get_current_user),
            _: None = Depends(require_role("admin"))
        ):
            return {"message": "Admin area"}
    """
    async def check_role(user: dict = Header(get_current_user)):
        roles = user.get("extension_Role", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
    
    return check_role


def require_permission(required_permission: str):
    """
    FastAPI dependency to require specific permission
    
    Usage:
        @app.delete("/documents/{id}")
        async def delete_document(
            id: str,
            user: dict = Depends(get_current_user),
            _: None = Depends(require_permission("documents:delete"))
        ):
            return {"message": "Document deleted"}
    """
    async def check_permission(user: dict = Header(get_current_user)):
        permissions = user.get("extension_Permissions", [])
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
    
    return check_permission

