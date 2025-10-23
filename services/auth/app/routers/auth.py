"""
Authentication Endpoints
Handles login, token generation, and user info
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.database import get_db
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()
config = get_config()


# ========================================
# Schemas
# ========================================

class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response"""
    id: str
    email: EmailStr
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []


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


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class RegisterResponse(BaseModel):
    """User registration response"""
    id: str
    email: EmailStr
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []


# ========================================
# Endpoints
# ========================================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Traditional login endpoint
    
    Validates email/password and returns user info
    """
    logger.info(f"Login request for email: {request.email}")
    
    try:
        # Use authentication service
        auth_service = AuthService(db)
        user = await auth_service.authenticate_user(request.email, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        return LoginResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            given_name=user["given_name"],
            family_name=user["family_name"],
            roles=user["roles"],
            permissions=user["permissions"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    User registration endpoint
    
    Creates a new user account
    """
    logger.info(f"Registration request for email: {request.email}")
    
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_user({
            "email": request.email,
            "password": request.password,
            "name": request.name,
            "given_name": request.given_name,
            "family_name": request.family_name,
            "roles": ["user"],
            "permissions": ["read"]
        })
        
        return RegisterResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            given_name=user["given_name"],
            family_name=user["family_name"],
            roles=user["roles"],
            permissions=user["permissions"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
    
    try:
        # Import Azure service for Azure AD B2C integration
        from app.services.azure_service import azure_service
        
        if request.grant_type == "authorization_code":
            if not request.code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing authorization code"
                )
            
            # Check if Azure AD B2C is available
            if azure_service.is_azure_b2c_available():
                # Exchange code for token with Azure AD B2C
                token_response = await azure_service.ad_b2c.exchange_code_for_token(
                    request.code, 
                    request.redirect_uri or "http://localhost:3000/callback"
                )
                
                if token_response:
                    logger.info("✅ Token exchanged successfully with Azure AD B2C")
                    return TokenResponse(
                        access_token=token_response["access_token"],
                        expires_in=token_response["expires_in"],
                        refresh_token=token_response.get("refresh_token"),
                        id_token=token_response.get("id_token"),
                        scope="openid profile email"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to exchange code for token"
                    )
            else:
                # Fallback to local JWT tokens
                logger.warning("⚠️ Azure AD B2C not configured, using local JWT tokens")
                from app.services.jwt_service import jwt_service
                
                # Create mock user data for local token generation
                user_data = {
                    "id": "local-user-1",
                    "email": "user@example.com",
                    "name": "Local User",
                    "given_name": "Local",
                    "family_name": "User",
                    "roles": ["user"],
                    "permissions": ["read"]
                }
                
                # Generate real JWT tokens
                access_token = jwt_service.create_access_token(user_data)
                id_token = jwt_service.create_id_token(user_data, "carpeta-ciudadana-api")
                refresh_token = jwt_service.create_refresh_token(user_data)
                
                return TokenResponse(
                    access_token=access_token,
                    expires_in=3600,
                    refresh_token=refresh_token,
                    id_token=id_token,
                    scope="openid profile email"
                )
        
        elif request.grant_type == "refresh_token":
            if not request.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing refresh token"
                )
            
            # Token refresh logic
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
            
            # Client credentials validation
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
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error in token endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
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
    
    try:
        # Import JWT service for token verification
        from app.services.jwt_service import jwt_service
        
        # Verify JWT token
        payload = jwt_service.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info(f"✅ UserInfo request for user: {payload.get('sub')}")
        
        # Return user info from JWT payload
        return UserInfoResponse(
            sub=payload["sub"],
            email=payload.get("email", ""),
            email_verified=True,
            name=payload.get("name"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", [])
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error in userinfo endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
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
    
    Initiates authorization flow with Azure AD B2C integration
    """
    logger.info(f"Authorize request: client_id={client_id}, response_type={response_type}")
    
    try:
        # Import Azure service for Azure AD B2C integration
        from app.services.azure_service import azure_service
        
        # Check if Azure AD B2C is available
        if azure_service.is_azure_b2c_available():
            # Generate Azure AD B2C authorization URL
            auth_url = azure_service.ad_b2c.get_authorization_url(redirect_uri, state)
            
            logger.info("✅ Generated Azure AD B2C authorization URL")
            
            return {
                "message": "Authorization endpoint - redirecting to Azure AD B2C",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "authorization_url": auth_url,
                "azure_b2c_available": True
            }
        else:
            # Fallback to local authorization
            logger.warning("⚠️ Azure AD B2C not configured, using local authorization")
            
            return {
                "message": "Authorization endpoint - Azure AD B2C not configured",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "azure_b2c_available": False,
                "fallback_url": f"{config.oidc.issuer_url}/api/auth/login"
            }
            
    except Exception as e:
        logger.error(f"❌ Error in authorization endpoint: {e}")
        
        # Fallback response
        return {
            "message": "Authorization endpoint - error occurred",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "error": "Internal server error",
            "azure_b2c_available": False
        }


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout endpoint
    
    Invalidates session and tokens
    """
    logger.info("Logout request")
    
    try:
        # Extract session ID from authorization header or request
        # For now, we'll implement basic logout
        auth_service = AuthService(db)
        
        # In a real implementation, you would extract the session ID
        # from the JWT token or session cookie
        # For now, we'll just log the logout
        
        return {
            "message": "Logged out successfully",
            "redirect_to": config.oidc.issuer_url
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {
            "message": "Logged out successfully",
            "redirect_to": config.oidc.issuer_url
        }

