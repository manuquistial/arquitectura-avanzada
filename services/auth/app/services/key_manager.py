"""RSA key management for JWT signing."""

import base64
import logging
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class KeyManager:
    """Manages RSA keys for JWT signing."""
    
    def __init__(self, private_key_path: str = "", public_key_path: str = ""):
        """Initialize key manager.
        
        Args:
            private_key_path: Path to private key PEM file
            public_key_path: Path to public key PEM file
        """
        self.private_key = None
        self.public_key = None
        self.kid = "carpeta-key-1"  # Key ID
        
        if private_key_path and os.path.exists(private_key_path):
            self._load_keys(private_key_path, public_key_path)
        else:
            self._generate_keys()
    
    def _load_keys(self, private_path: str, public_path: str):
        """Load RSA keys from files."""
        try:
            # Load private key
            with open(private_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            # Load public key
            with open(public_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            
            logger.info("✅ RSA keys loaded from files")
        except Exception as e:
            logger.error(f"Failed to load keys: {e}, generating new ones")
            self._generate_keys()
    
    def _generate_keys(self):
        """Generate new RSA key pair."""
        logger.info("Generating new RSA key pair...")
        
        # Generate private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Derive public key
        self.public_key = self.private_key.public_key()
        
        logger.info("✅ RSA keys generated (in-memory)")
    
    def get_private_key_pem(self) -> str:
        """Get private key as PEM string."""
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode()
    
    def get_public_key_pem(self) -> str:
        """Get public key as PEM string."""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode()
    
    def get_jwks(self) -> dict:
        """Get JWKS (JSON Web Key Set) for public key.
        
        Returns:
            JWKS dict for /.well-known/jwks.json
        """
        # Get public key in DER format
        public_der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Extract modulus and exponent for JWK
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
        public_numbers = self.public_key.public_numbers()
        
        # Convert to base64url
        n = base64.urlsafe_b64encode(
            public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
        ).decode().rstrip('=')
        
        e = base64.urlsafe_b64encode(
            public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')
        ).decode().rstrip('=')
        
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": self.kid,
                    "alg": "RS256",
                    "n": n,
                    "e": e
                }
            ]
        }

