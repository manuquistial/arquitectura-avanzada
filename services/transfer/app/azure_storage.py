"""Azure Storage integration for transfer service."""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import AzureError
    AZURE_STORAGE_AVAILABLE = True
except ImportError:
    AZURE_STORAGE_AVAILABLE = False
    logging.warning("Azure Storage libraries not available. Running in local mode.")

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AzureStorageService:
    """Azure Storage service with fallback to local storage."""
    
    def __init__(self):
        self.client = None
        self.container_name = settings.azure_storage_container_name
        self.is_available = False
        
        if AZURE_STORAGE_AVAILABLE and settings.azure_storage_account_name:
            try:
                self._initialize_client()
                self.is_available = True
                logger.info("Azure Storage client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Storage: {e}")
                self.is_available = False
        else:
            logger.info("Azure Storage not configured, using local fallback")
    
    def _initialize_client(self):
        """Initialize Azure Storage client."""
        if settings.azure_storage_connection_string:
            self.client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        elif settings.azure_storage_account_name:
            # Use DefaultAzureCredential for managed identity
            credential = DefaultAzureCredential()
            account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
            self.client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            raise ValueError("Azure Storage not configured")
    
    async def upload_document(
        self, 
        document_data: bytes, 
        document_id: str, 
        citizen_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload document to Azure Storage with fallback to local storage."""
        try:
            if not self.is_available:
                return await self._local_upload(document_data, document_id, citizen_id, metadata)
            
            # Generate blob name
            blob_name = f"transfers/{citizen_id}/{document_id}"
            
            # Upload to Azure Storage
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Set metadata
            blob_metadata = {
                "citizen_id": str(citizen_id),
                "document_id": document_id,
                "upload_time": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            blob_client.upload_blob(
                document_data,
                metadata=blob_metadata,
                overwrite=True
            )
            
            # Generate SAS URL for access
            sas_url = self._generate_sas_url(blob_name)
            
            logger.info(f"Document {document_id} uploaded to Azure Storage")
            
            return {
                "success": True,
                "blob_name": blob_name,
                "sas_url": sas_url,
                "size": len(document_data),
                "metadata": blob_metadata
            }
            
        except Exception as e:
            logger.error(f"Azure Storage upload failed: {e}")
            # Fallback to local storage
            return await self._local_upload(document_data, document_id, citizen_id, metadata)
    
    async def _local_upload(
        self, 
        document_data: bytes, 
        document_id: str, 
        citizen_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Local storage fallback."""
        import os
        import tempfile
        
        # Create local storage directory
        storage_dir = os.path.join(tempfile.gettempdir(), "transfer_documents")
        os.makedirs(storage_dir, exist_ok=True)
        
        # Save file locally
        file_path = os.path.join(storage_dir, f"{citizen_id}_{document_id}")
        with open(file_path, "wb") as f:
            f.write(document_data)
        
        logger.info(f"Document {document_id} saved locally at {file_path}")
        
        return {
            "success": True,
            "local_path": file_path,
            "size": len(document_data),
            "metadata": metadata or {}
        }
    
    def _generate_sas_url(self, blob_name: str) -> str:
        """Generate SAS URL for blob access."""
        try:
            if not self.client:
                return ""
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=settings.azure_storage.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(minutes=settings.azure_storage.sas_ttl_minutes)
            )
            
            return f"https://{settings.azure_storage.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            
        except Exception as e:
            logger.error(f"Failed to generate SAS URL: {e}")
            return ""
    
    async def download_document(self, blob_name: str) -> Optional[bytes]:
        """Download document from Azure Storage."""
        try:
            if not self.is_available:
                return await self._local_download(blob_name)
            
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            download_stream = blob_client.download_blob()
            return download_stream.readall()
            
        except Exception as e:
            logger.error(f"Failed to download document {blob_name}: {e}")
            return None
    
    async def _local_download(self, blob_name: str) -> Optional[bytes]:
        """Local download fallback."""
        import os
        import tempfile
        
        # Try to find file in local storage
        storage_dir = os.path.join(tempfile.gettempdir(), "transfer_documents")
        file_path = os.path.join(storage_dir, blob_name.split("/")[-1])
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        
        return None
    
    async def delete_document(self, blob_name: str) -> bool:
        """Delete document from Azure Storage."""
        try:
            if not self.is_available:
                return await self._local_delete(blob_name)
            
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Document {blob_name} deleted from Azure Storage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {blob_name}: {e}")
            return False
    
    async def _local_delete(self, blob_name: str) -> bool:
        """Local delete fallback."""
        import os
        import tempfile
        
        storage_dir = os.path.join(tempfile.gettempdir(), "transfer_documents")
        file_path = os.path.join(storage_dir, blob_name.split("/")[-1])
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Local document {file_path} deleted")
            return True
        
        return False


# Global instance
azure_storage = AzureStorageService()
