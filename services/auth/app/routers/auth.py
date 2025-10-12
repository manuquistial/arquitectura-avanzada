"""
Authentication Endpoints
Handles login, token generation, and user info
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# ========================================
# Schemas
# ========================================

class TokenRequest(BaseModel):
    """OAuth2 token request"""
    grant_type: str  # authorization_code, refresh_token, client_credentials
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = None  # PKCE


class TokenResponse(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


class UserInfoResponse(BaseModel):
    """OIDC UserInfo response"""
    sub: str  # User ID
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []


# ========================================
# Endpoints
# ========================================

@router.post("/token", response_model=TokenResponse)
async def token(request: TokenRequest):
    """
    OAuth2 Token endpoint
    
    Supports:
    - authorization_code: Exchange code for tokens
    - refresh_token: Refresh access token
    - client_credentials: M2M authentication
    """
    logger.info(f"Token request: grant_type={request.grant_type}")
    
    # TODO: Implement actual token generation
    # For now, delegate to Azure AD B2C or return mock
    
    if request.grant_type == "authorization_code":
        if not request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code"
            )
        
        # TODO: Exchange code for tokens (Azure AD B2C)
        # For now, return mock tokens
        return TokenResponse(
            access_token="mock-access-token",
            expires_in=3600,
            refresh_token="mock-refresh-token",
            id_token="mock-id-token",
            scope="openid profile email"
        )
    
    elif request.grant_type == "refresh_token":
        if not request.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing refresh token"
            )
        
        # TODO: Validate and refresh token
        return TokenResponse(
            access_token="mock-refreshed-access-token",
            expires_in=3600,
            scope="openid profile email"
        )
    
    elif request.grant_type == "client_credentials":
        # M2M authentication
        if not request.client_id or not request.client_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing client credentials"
            )
        
        # TODO: Validate client credentials
        return TokenResponse(
            access_token="mock-m2m-token",
            expires_in=3600,
            token_type="Bearer",
            scope="api"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant type: {request.grant_type}"
        )


@router.get("/userinfo", response_model=UserInfoResponse)
async def userinfo(
    authorization: Optional[str] = Header(None)
):
    """
    OIDC UserInfo endpoint
    
    Returns user information from access token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    scheme, _, token = authorization.partition(" ")
    
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # TODO: Validate token and extract user info
    # For now, return mock data
    
    logger.info("UserInfo request (mock data)")
    
    return UserInfoResponse(
        sub="user-id-123",
        email="user@example.com",
        email_verified=True,
        name="Demo User",
        given_name="Demo",
        family_name="User",
        roles=["user"],
        permissions=["read:own_documents"]
    )


@router.post("/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str = "openid profile email",
    state: Optional[str] = None,
    nonce: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None
):
    """
    OAuth2 Authorization endpoint
    
    Initiates authorization flow
    """
    logger.info(f"Authorize request: client_id={client_id}, response_type={response_type}")
    
    # TODO: Implement authorization flow
    # For now, delegate to Azure AD B2C
    
    return {
        "message": "Authorization endpoint - delegate to Azure AD B2C",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "azure_b2c_url": f"https://{settings.azure_b2c_tenant_name}.b2clogin.com"
    }


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None)
):
    """
    Logout endpoint
    
    Invalidates session and tokens
    """
    # TODO: Invalidate session in Redis
    # TODO: Revoke tokens
    
    logger.info("Logout request")
    
    return {
        "message": "Logged out successfully",
        "redirect_to": settings.oidc_issuer_url
    }

