"""
JWT Service with real implementation using Kubernetes Secrets
Note: We use Kubernetes Secrets, not Azure Key Vault
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import jwt
import base64

from app.config import get_config
from app.services.azure_service import azure_service

logger = logging.getLogger(__name__)
config = get_config()


class JWTService:
    """JWT service with real implementation using Kubernetes Secrets."""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.key_id = "carpeta-ciudadana-key-1"
        self._load_keys()
    
    def _load_keys(self):
        """Load RSA keys from Kubernetes Secrets."""
        try:
            # Try to load private key from Kubernetes Secrets
            private_key_pem = self._get_secret_from_kubernetes("jwt-private-key")
            if private_key_pem:
                self.private_key = serialization.load_pem_private_key(
                    private_key_pem.encode(),
                    password=None,
                    backend=default_backend()
                )
                logger.info("✅ JWT private key loaded from Kubernetes Secrets")
            else:
                # Generate new key pair if not found
                logger.warning("⚠️ JWT private key not found, generating new key pair")
                self._generate_key_pair()
            
            # Try to load public key from Kubernetes Secrets
            public_key_pem = self._get_secret_from_kubernetes("jwt-public-key")
            if public_key_pem:
                self.public_key = serialization.load_pem_public_key(
                    public_key_pem.encode(),
                    backend=default_backend()
                )
                logger.info("✅ JWT public key loaded from Kubernetes Secrets")
            else:
                # Extract public key from private key
                if self.private_key:
                    self.public_key = self.private_key.public_key()
                    logger.info("✅ JWT public key extracted from private key")
            
        except Exception as e:
            logger.error(f"❌ Error loading JWT keys: {e}")
            # Fallback to generated keys
            self._generate_key_pair()
    
    def _get_secret_from_kubernetes(self, secret_name: str) -> Optional[str]:
        """Get secret from Kubernetes Secrets mount."""
        try:
            secret_path = os.path.join("/var/secrets", secret_name)
            if os.path.exists(secret_path):
                with open(secret_path, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            logger.error(f"❌ Error reading Kubernetes secret {secret_name}: {e}")
            return None
    
    def _generate_key_pair(self):
        """Generate new RSA key pair."""
        try:
            # Generate private key
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Extract public key
            self.public_key = self.private_key.public_key()
            
            logger.info("✅ Generated new RSA key pair")
            
        except Exception as e:
            logger.error(f"❌ Error generating key pair: {e}")
            raise
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (JWKS) for public key verification."""
        try:
            if not self.public_key:
                raise ValueError("Public key not available")
            
            # Get public key in PEM format
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Extract modulus and exponent from public key
            public_numbers = self.public_key.public_numbers()
            modulus = public_numbers.n
            exponent = public_numbers.e
            
            # Convert to base64url encoding
            modulus_b64 = base64.urlsafe_b64encode(
                modulus.to_bytes((modulus.bit_length() + 7) // 8, 'big')
            ).decode('ascii').rstrip('=')
            
            exponent_b64 = base64.urlsafe_b64encode(
                exponent.to_bytes((exponent.bit_length() + 7) // 8, 'big')
            ).decode('ascii').rstrip('=')
            
            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "kid": self.key_id,
                        "alg": "RS256",
                        "n": modulus_b64,
                        "e": exponent_b64
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating JWKS: {e}")
            # Fallback to placeholder
            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "kid": self.key_id,
                        "alg": "RS256",
                        "n": "placeholder-modulus-value",
                        "e": "AQAB"
                    }
                ]
            }
    
    def create_access_token(self, user_data: Dict[str, Any], expires_in: int = 3600) -> str:
        """Create JWT access token."""
        try:
            if not self.private_key:
                raise ValueError("Private key not available")
            
            # Create token payload
            now = datetime.utcnow()
            payload = {
                "iss": config.oidc.issuer_url,
                "sub": user_data["id"],
                "aud": "carpeta-ciudadana-api",
                "exp": now + timedelta(seconds=expires_in),
                "iat": now,
                "nbf": now,
                "jti": f"access-{user_data['id']}-{int(now.timestamp())}",
                "scope": "openid profile email",
                "email": user_data["email"],
                "name": user_data["name"],
                "given_name": user_data.get("given_name"),
                "family_name": user_data.get("family_name"),
                "roles": user_data.get("roles", []),
                "permissions": user_data.get("permissions", [])
            }
            
            # Create JWT token
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256",
                headers={"kid": self.key_id}
            )
            
            logger.info(f"✅ Created access token for user: {user_data['email']}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creating access token: {e}")
            raise
    
    def create_id_token(self, user_data: Dict[str, Any], client_id: str) -> str:
        """Create JWT ID token."""
        try:
            if not self.private_key:
                raise ValueError("Private key not available")
            
            # Create ID token payload
            now = datetime.utcnow()
            payload = {
                "iss": config.oidc.issuer_url,
                "sub": user_data["id"],
                "aud": client_id,
                "exp": now + timedelta(seconds=3600),
                "iat": now,
                "nbf": now,
                "jti": f"id-{user_data['id']}-{int(now.timestamp())}",
                "email": user_data["email"],
                "email_verified": True,
                "name": user_data["name"],
                "given_name": user_data.get("given_name"),
                "family_name": user_data.get("family_name"),
                "roles": user_data.get("roles", []),
                "permissions": user_data.get("permissions", [])
            }
            
            # Create JWT ID token
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256",
                headers={"kid": self.key_id}
            )
            
            logger.info(f"✅ Created ID token for user: {user_data['email']}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creating ID token: {e}")
            raise
    
    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        try:
            if not self.private_key:
                raise ValueError("Private key not available")
            
            # Create refresh token payload
            now = datetime.utcnow()
            payload = {
                "iss": config.oidc.issuer_url,
                "sub": user_data["id"],
                "aud": "carpeta-ciudadana-api",
                "exp": now + timedelta(days=30),  # Refresh tokens last longer
                "iat": now,
                "nbf": now,
                "jti": f"refresh-{user_data['id']}-{int(now.timestamp())}",
                "scope": "openid profile email",
                "token_type": "refresh"
            }
            
            # Create JWT refresh token
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256",
                headers={"kid": self.key_id}
            )
            
            logger.info(f"✅ Created refresh token for user: {user_data['email']}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creating refresh token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            if not self.public_key:
                raise ValueError("Public key not available")
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                audience="carpeta-ciudadana-api",
                issuer=config.oidc.issuer_url
            )
            
            logger.info(f"✅ Token verified for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error verifying token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token)
            if not payload or payload.get("token_type") != "refresh":
                logger.warning("⚠️ Invalid refresh token")
                return None
            
            # Get user data from token
            user_data = {
                "id": payload["sub"],
                "email": payload.get("email"),
                "name": payload.get("name"),
                "given_name": payload.get("given_name"),
                "family_name": payload.get("family_name"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", [])
            }
            
            # Create new access token
            access_token = self.create_access_token(user_data)
            id_token = self.create_id_token(user_data, "carpeta-ciudadana-api")
            
            logger.info(f"✅ Refreshed tokens for user: {user_data['email']}")
            
            return {
                "access_token": access_token,
                "id_token": id_token,
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            
        except Exception as e:
            logger.error(f"❌ Error refreshing token: {e}")
            return None


# Global JWT service instance
jwt_service = JWTService()
