"""Cryptographic operations for document signing."""

import base64
import hashlib
import logging
import os
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

from app.config import get_config

logger = logging.getLogger(__name__)


class CryptoService:
    """Handles cryptographic operations (SHA-256 hashing and RSA signing)."""
    
    def __init__(self, config):
        """Initialize crypto service."""
        self.config = config
        self.private_key = None
        self.public_key = None
        
        if config.signing_private_key_path and os.path.exists(config.signing_private_key_path):
            self._load_private_key()
        else:
            logger.warning("⚠️  No signing key configured, generating temporary RSA key pair")
            self._generate_temporary_key_pair()
    
    def _load_private_key(self):
        """Load RSA private key from file (K8s secret mount)."""
        try:
            with open(self.config.signing_private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
            logger.info("✅ RSA private key loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load private key: {e}")
            self._generate_temporary_key_pair()
    
    def _generate_temporary_key_pair(self):
        """Generate temporary RSA key pair for development."""
        try:
            # Generate 2048-bit RSA key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            logger.info("✅ Temporary RSA key pair generated (2048-bit)")
        except Exception as e:
            logger.error(f"❌ Failed to generate temporary key pair: {e}")
            raise
    
    async def calculate_sha256(self, data: bytes) -> str:
        """Calculate SHA-256 hash of document."""
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()
    
    async def sign_hash(self, sha256_hash: str) -> Tuple[str, str]:
        """Sign SHA-256 hash using RSA private key.
        
        Args:
            sha256_hash: Hex-encoded SHA-256 hash
            
        Returns:
            (signature_base64, algorithm)
        """
        hash_bytes = bytes.fromhex(sha256_hash)
        
        if self.private_key is None:
            raise ValueError("No private key available for signing")
        
        try:
            # Sign with RSA private key using PKCS1v15 padding
            signature = self.private_key.sign(
                hash_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            signature_b64 = base64.b64encode(signature).decode()
            logger.info(f"✅ Hash signed with RSA-2048")
            return (signature_b64, "RS256")
            
        except Exception as e:
            logger.error(f"❌ Signing failed: {e}")
            raise
    
    async def verify_signature(
        self,
        sha256_hash: str,
        signature_b64: str
    ) -> Tuple[bool, str]:
        """Verify signature against hash.
        
        Args:
            sha256_hash: Hex-encoded SHA-256 hash
            signature_b64: Base64-encoded signature
            
        Returns:
            (is_valid, details)
        """
        if self.public_key is None:
            logger.warning("⚠️ Cannot verify: no public key available")
            return (False, "No public key available for verification")
        
        try:
            # Decode signature
            signature_bytes = base64.b64decode(signature_b64)
            hash_bytes = bytes.fromhex(sha256_hash)
            
            # Verify signature with public key
            self.public_key.verify(
                signature_bytes,
                hash_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            logger.info("✅ Signature verified successfully")
            return (True, "Signature verified with RSA-2048")
            
        except Exception as e:
            logger.error(f"❌ Signature verification failed: {e}")
            return (False, f"Signature verification failed: {str(e)}")

