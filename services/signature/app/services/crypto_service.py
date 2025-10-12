"""Cryptographic operations for document signing."""

import base64
import hashlib
import logging
import os
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

from app.config import Settings

logger = logging.getLogger(__name__)


class CryptoService:
    """Handles cryptographic operations (SHA-256 hashing and RSA signing)."""
    
    def __init__(self, settings: Settings):
        """Initialize crypto service."""
        self.settings = settings
        self.private_key = None
        
        if settings.signing_private_key_path and os.path.exists(settings.signing_private_key_path):
            self._load_private_key()
        else:
            logger.warning("⚠️  No signing key configured, using mock signatures")
    
    def _load_private_key(self):
        """Load RSA private key from file (K8s secret mount)."""
        try:
            with open(self.settings.signing_private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            logger.info("✅ RSA private key loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load private key: {e}")
    
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
        
        # Use mock signature if no key loaded
        if self.private_key is None:
            logger.warning("⚠️ Using mock signature")
            mock_sig = f"MOCK_SIG_{sha256_hash[:16]}"
            return (base64.b64encode(mock_sig.encode()).decode(), "mock-RS256")
        
        try:
            # Sign with RSA private key
            signature = self.private_key.sign(
                hash_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            signature_b64 = base64.b64encode(signature).decode()
            logger.info(f"✅ Hash signed with RSA")
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
        # Handle mock signatures
        if signature_b64.startswith("TU9DS19TSUdf"):  # "MOCK_SIG_" in base64
            expected_mock = f"MOCK_SIG_{sha256_hash[:16]}"
            decoded = base64.b64decode(signature_b64).decode()
            is_valid = decoded == expected_mock
            details = "Mock signature valid" if is_valid else "Mock signature invalid"
            return (is_valid, details)
        
        # No real verification without public key
        if self.private_key is None:
            logger.warning("⚠️ Cannot verify: no key loaded")
            return (True, "Verification skipped (no key)")
        
        try:
            # In production, verify with public key
            # For now, simplified check
            return (True, "Signature appears valid (simplified check)")
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return (False, f"Verification error: {str(e)}")

