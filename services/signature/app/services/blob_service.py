"""Azure Blob Storage service for SAS token generation."""

import logging
from datetime import datetime, timedelta, timezone
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, UserDelegationKey
from app.config import Settings

logger = logging.getLogger(__name__)

class BlobService:
    """Handles Azure Blob Storage operations.
    
    Preferencia por User Delegation SAS (más seguro), con fallback a Account Key SAS.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sas_ttl_minutes = getattr(settings, 'sas_ttl_minutes', 15)
        self.use_managed_identity = True
        
        # Try to use Managed Identity first
        if settings.azure_storage_account_name:
            try:
                account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self.client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                # Test the credential
                self.client.list_containers(max_results=1)
                logger.info("✅ Using Managed Identity for Azure Blob Storage")
            except Exception as e:
                logger.warning(f"⚠️  Managed Identity auth failed, falling back to account key: {e}")
                self.use_managed_identity = False
                
                # Fallback to Account Key
                if settings.azure_storage_account_key:
                    connection_string = (
                        f"DefaultEndpointsProtocol=https;"
                        f"AccountName={settings.azure_storage_account_name};"
                        f"AccountKey={settings.azure_storage_account_key};"
                        f"EndpointSuffix=core.windows.net"
                    )
                    self.client = BlobServiceClient.from_connection_string(connection_string)
                    logger.info("✅ Using Account Key for Azure Blob Storage")
                else:
                    logger.warning("⚠️  Azure Storage not configured")
                    self.client = None
        else:
            logger.warning("⚠️  Azure Storage not configured")
            self.client = None
    
    def _get_user_delegation_key(self) -> UserDelegationKey | None:
        """Get User Delegation Key for generating User Delegation SAS.
        
        Returns None if Managed Identity is not available.
        """
        if not self.use_managed_identity or not self.client:
            return None
        
        try:
            # User delegation key is valid for 7 days maximum
            start_time = datetime.now(timezone.utc)
            expiry_time = start_time + timedelta(days=1)
            
            user_delegation_key = self.client.get_user_delegation_key(
                key_start_time=start_time,
                key_expiry_time=expiry_time
            )
            return user_delegation_key
        except AzureError as e:
            logger.error(f"❌ Failed to get user delegation key: {e}")
            return None
    
    async def generate_sas_url(
        self, 
        blob_name: str, 
        expiry_hours: float | None = None
    ) -> str:
        """Generate SAS token URL for blob (READ only).
        
        Tries User Delegation SAS first (more secure), falls back to Account Key SAS.
        
        IMPORTANT: This SAS is for hub authentication only.
        Hub does NOT download/store binaries, only validates metadata.
        
        Args:
            blob_name: Blob name in container
            expiry_hours: Hours until SAS expires (default from SAS_TTL_MINUTES)
            
        Returns:
            Full SAS URL (READ permission only)
        """
        if not self.client:
            return f"https://mock-storage/{blob_name}?sas=MOCK_TOKEN"
        
        if expiry_hours is None:
            expiry_hours = self.sas_ttl_minutes / 60.0
        
        blob_client = self.client.get_blob_client(
            container=self.settings.azure_storage_container,
            blob=blob_name
        )
        
        try:
            # Try User Delegation SAS first (more secure)
            user_delegation_key = self._get_user_delegation_key()
            
            if user_delegation_key:
                start_time = datetime.now(timezone.utc)
                expiry_time = start_time + timedelta(hours=expiry_hours)
                
                sas_token = blob_client.generate_sas(
                    user_delegation_key=user_delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_time,
                    start=start_time,
                )
                logger.info(f"✅ User Delegation SAS URL generated for {blob_name}")
            else:
                # Fallback to Account Key SAS
                if not self.settings.azure_storage_account_key:
                    raise ValueError("No account key available for fallback SAS generation")
                    
                sas_token = generate_blob_sas(
                    account_name=self.settings.azure_storage_account_name,
                    container_name=self.settings.azure_storage_container,
                    blob_name=blob_name,
                    account_key=self.settings.azure_storage_account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
                )
                logger.info(f"✅ Account Key SAS URL generated for {blob_name}")
            
            url = f"{blob_client.url}?{sas_token}"
            return url
            
        except Exception as e:
            logger.error(f"❌ SAS generation failed: {e}")
            raise
