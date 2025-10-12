"""Azure Blob Storage service for SAS token generation."""

import logging
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from app.config import Settings

logger = logging.getLogger(__name__)

class BlobService:
    """Handles Azure Blob Storage operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        if settings.azure_storage_account_name and settings.azure_storage_account_key:
            connection_string = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={settings.azure_storage_account_name};"
                f"AccountKey={settings.azure_storage_account_key};"
                f"EndpointSuffix=core.windows.net"
            )
            self.client = BlobServiceClient.from_connection_string(connection_string)
        else:
            logger.warning("⚠️  Azure Storage not configured")
            self.client = None
    
    async def generate_sas_url(
        self, 
        blob_name: str, 
        expiry_hours: float = 0.25
    ) -> str:
        """Generate SAS token URL for blob (READ only).
        
        IMPORTANT: This SAS is for hub authentication only.
        Hub does NOT download/store binaries, only validates metadata.
        
        Args:
            blob_name: Blob name in container
            expiry_hours: Hours until SAS expires (default 0.25 = 15 min)
            
        Returns:
            Full SAS URL (READ permission only)
        """
        if not self.client:
            return f"https://mock-storage/{blob_name}?sas=MOCK_TOKEN"
        
        try:
            sas_token = generate_blob_sas(
                account_name=self.settings.azure_storage_account_name,
                container_name=self.settings.azure_storage_container,
                blob_name=blob_name,
                account_key=self.settings.azure_storage_account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            url = (
                f"https://{self.settings.azure_storage_account_name}.blob.core.windows.net/"
                f"{self.settings.azure_storage_container}/{blob_name}?{sas_token}"
            )
            
            logger.info(f"✅ SAS URL generated for {blob_name}")
            return url
            
        except Exception as e:
            logger.error(f"❌ SAS generation failed: {e}")
            raise
