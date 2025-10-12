"""OIDC endpoints - minimal viable implementation."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel

from app.config import Settings
from app.services.key_manager import KeyManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Singletons
_settings = Settings()
_key_manager = KeyManager(_settings.private_key_path, _settings.public_key_path)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class TokenResponse(BaseModel):
    """OAuth 2.0 token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None


@router.get("/.well-known/openid-configuration")
async def openid_configuration() -> Dict[str, Any]:
    """OpenID Connect discovery endpoint."""
    base_url = _settings.issuer
    
    return {
        "issuer": _settings.issuer,
        "authorization_endpoint": f"{base_url}/auth/authorize",
        "token_endpoint": f"{base_url}/auth/token",
        "userinfo_endpoint": f"{base_url}/auth/userinfo",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "response_types_supported": ["code", "token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "claims_supported": ["sub", "iss", "aud", "exp", "iat", "name", "email", "roles", "tenant"]
    }


@router.get("/.well-known/jwks.json")
async def jwks() -> Dict[str, Any]:
    """JWKS (JSON Web Key Set) endpoint.
    
    Publishes public keys for JWT verification.
    """
    return _key_manager.get_jwks()


@router.post("/auth/token", response_model=TokenResponse)
async def token(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """OAuth 2.0 token endpoint.
    
    For MVP: accepts any credentials and issues JWT.
    In production: validate against database.
    """
    # MVP: Accept any credentials (development only!)
    if _settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Production auth not implemented, use Azure AD B2C"
        )
    
    # Mock user (in production, lookup in database)
    user = {
        "sub": str(form_data.username),  # Subject (user ID)
        "email": form_data.username,
        "name": "Usuario Demo",
        "roles": ["citizen", "user"],
        "tenant": "carpeta-demo"
    }
    
    # Create JWT
    now = datetime.utcnow()
    expires_delta = timedelta(minutes=_settings.jwt_access_token_expire_minutes)
    
    claims = {
        "sub": user["sub"],
        "iss": _settings.issuer,
        "aud": "carpeta-ciudadana",
        "exp": now + expires_delta,
        "iat": now,
        "name": user["name"],
        "email": user["email"],
        "roles": user["roles"],
        "tenant": user["tenant"]
    }
    
    # Sign with private key
    access_token = jwt.encode(
        claims,
        _key_manager.get_private_key_pem(),
        algorithm=_settings.jwt_algorithm,
        headers={"kid": _key_manager.kid}
    )
    
    logger.info(f"✅ JWT issued for {user['sub']}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=int(expires_delta.total_seconds())
    )


@router.get("/auth/userinfo")
async def userinfo(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """OIDC userinfo endpoint.
    
    Returns user claims from validated JWT.
    """
    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            _key_manager.get_public_key_pem(),
            algorithms=[_settings.jwt_algorithm],
            audience="carpeta-ciudadana",
            issuer=_settings.issuer
        )
        
        return {
            "sub": payload.get("sub"),
            "name": payload.get("name"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "tenant": payload.get("tenant")
        }
        
    except jwt.JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

