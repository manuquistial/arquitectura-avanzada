"""SAS URL generator for shared documents."""

import logging
from datetime import datetime, timedelta
from typing import List
from azure.storage.blob import generate_blob_sas, BlobSasPermissions

from app.config import Settings

logger = logging.getLogger(__name__)


class SASGenerator:
    """Generates SAS URLs for document sharing."""
    
    def __init__(self, settings: Settings):
        """Initialize SAS generator.
        
        Args:
            settings: Service settings
        """
        self.settings = settings
        self.account_name = settings.azure_storage_account_name
        self.account_key = settings.azure_storage_account_key
        self.container = settings.azure_storage_container
    
    async def generate_sas_urls(
        self,
        blob_names: List[str],
        expiry_hours: int = 24,
        add_watermark: bool = False
    ) -> List[dict]:
        """Generate SAS URLs for multiple blobs.
        
        Args:
            blob_names: List of blob names
            expiry_hours: Hours until SAS expires
            add_watermark: Add watermark parameter to URL
            
        Returns:
            List of dicts with blob_name and sas_url
        """
        if not self.account_name or not self.account_key:
            # Mock mode
            logger.warning("⚠️  Azure Storage not configured, using mock SAS URLs")
            return [
                {
                    "blob_name": blob,
                    "sas_url": f"https://mock-storage/{blob}?sas=MOCK_TOKEN&watermark={add_watermark}"
                }
                for blob in blob_names
            ]
        
        results = []
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        for blob_name in blob_names:
            try:
                # Generate SAS token
                sas_token = generate_blob_sas(
                    account_name=self.account_name,
                    container_name=self.container,
                    blob_name=blob_name,
                    account_key=self.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry
                )
                
                # Build URL
                url = (
                    f"https://{self.account_name}.blob.core.windows.net/"
                    f"{self.container}/{blob_name}?{sas_token}"
                )
                
                # Add watermark parameter if enabled
                if add_watermark:
                    url += "&watermark=true"
                
                results.append({
                    "blob_name": blob_name,
                    "sas_url": url
                })
                
                logger.debug(f"Generated SAS for {blob_name}")
                
            except Exception as e:
                logger.error(f"Failed to generate SAS for {blob_name}: {e}")
                raise
        
        logger.info(f"✅ Generated {len(results)} SAS URLs")
        return results

