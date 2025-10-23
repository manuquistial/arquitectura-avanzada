"""Hash verification service for document integrity."""

import hashlib
import logging
from typing import Optional, Dict, Any

from app.azure_storage import AzureBlobDocumentClient

logger = logging.getLogger(__name__)


class HashVerificationService:
    """Service for verifying document hash integrity."""
    
    def __init__(self, storage_client: AzureBlobDocumentClient):
        """Initialize hash verification service."""
        self.storage_client = storage_client
    
    def calculate_sha256(self, data: bytes) -> str:
        """Calculate SHA-256 hash of data."""
        return hashlib.sha256(data).hexdigest()
    
    async def verify_document_hash(
        self,
        blob_name: str,
        expected_hash: str
    ) -> Dict[str, Any]:
        """Verify document hash against stored blob."""
        try:
            # Get blob metadata and content
            blob_properties = self.storage_client.get_blob_properties(blob_name)
            
            if not blob_properties:
                return {
                    "verified": False,
                    "error": "Blob not found",
                    "actual_hash": None,
                    "expected_hash": expected_hash
                }
            
            # Get blob content for hash calculation
            blob_content = await self.storage_client.download_blob_content(blob_name)
            
            if not blob_content:
                return {
                    "verified": False,
                    "error": "Failed to download blob content",
                    "actual_hash": None,
                    "expected_hash": expected_hash
                }
            
            # Calculate actual hash
            actual_hash = self.calculate_sha256(blob_content)
            
            # Compare hashes
            verified = actual_hash.lower() == expected_hash.lower()
            
            result = {
                "verified": verified,
                "actual_hash": actual_hash,
                "expected_hash": expected_hash,
                "blob_size": len(blob_content),
                "blob_properties": {
                    "content_type": blob_properties.get("content_type"),
                    "last_modified": blob_properties.get("last_modified"),
                    "etag": blob_properties.get("etag")
                }
            }
            
            if verified:
                logger.info(f"Hash verification successful for blob {blob_name}")
            else:
                logger.warning(f"Hash verification failed for blob {blob_name}: expected {expected_hash}, got {actual_hash}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying hash for blob {blob_name}: {e}")
            return {
                "verified": False,
                "error": str(e),
                "actual_hash": None,
                "expected_hash": expected_hash
            }
    
    async def verify_document_integrity(
        self,
        document_id: str,
        blob_name: str,
        expected_hash: str,
        expected_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Comprehensive document integrity verification."""
        try:
            # Verify hash
            hash_result = await self.verify_document_hash(blob_name, expected_hash)
            
            if not hash_result["verified"]:
                return hash_result
            
            # Verify size if provided
            if expected_size is not None:
                actual_size = hash_result["blob_size"]
                if actual_size != expected_size:
                    return {
                        "verified": False,
                        "error": f"Size mismatch: expected {expected_size}, got {actual_size}",
                        "actual_size": actual_size,
                        "expected_size": expected_size,
                        "hash_verified": True
                    }
            
            return {
                "verified": True,
                "hash_verified": True,
                "size_verified": expected_size is None or hash_result["blob_size"] == expected_size,
                "actual_hash": hash_result["actual_hash"],
                "expected_hash": expected_hash,
                "blob_size": hash_result["blob_size"],
                "blob_properties": hash_result["blob_properties"]
            }
            
        except Exception as e:
            logger.error(f"Error verifying document integrity for {document_id}: {e}")
            return {
                "verified": False,
                "error": str(e),
                "hash_verified": False,
                "size_verified": False
            }
