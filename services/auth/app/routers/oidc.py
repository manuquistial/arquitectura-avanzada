"""
OIDC Discovery Endpoints
Implements OpenID Connect Discovery protocol
"""

import logging
from typing import Any

from fastapi import APIRouter

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/openid-configuration")
async def openid_configuration() -> dict[str, Any]:
    """
    OIDC Discovery endpoint
    
    Returns OpenID Connect configuration metadata
    @see https://openid.net/specs/openid-connect-discovery-1_0.html
    """
    issuer = settings.oidc_issuer_url
    
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/api/auth/authorize",
        "token_endpoint": f"{issuer}/api/auth/token",
        "userinfo_endpoint": f"{issuer}/api/auth/userinfo",
        "jwks_uri": f"{issuer}/.well-known/jwks.json",
        "end_session_endpoint": f"{issuer}/api/auth/logout",
        
        # Supported features
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token"
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "offline_access"
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
        ],
        "claims_supported": [
            "sub",
            "iss",
            "aud",
            "exp",
            "iat",
            "email",
            "email_verified",
            "name",
            "given_name",
            "family_name",
            "roles",
            "permissions"
        ],
        "code_challenge_methods_supported": ["S256"],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token",
            "client_credentials"
        ]
    }


@router.get("/jwks.json")
async def jwks() -> dict[str, list]:
    """
    JSON Web Key Set (JWKS) endpoint
    
    Returns public keys for JWT signature verification
    """
    # TODO: Load actual public key from Key Vault or file
    # For now, return empty (clients should use Azure AD B2C JWKS)
    
    logger.warning("⚠️  JWKS endpoint not fully implemented, using placeholder")
    
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "carpeta-ciudadana-key-1",
                "alg": "RS256",
                "n": "placeholder-modulus-value",
                "e": "AQAB"
            }
        ]
    }
